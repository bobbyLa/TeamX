import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request


SOURCE_NAME = "gemini-vision"
API_TIMEOUT_SECONDS = 120
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_OUTPUT_TOKENS = 2048

DETAIL_KEYWORDS = (
    "ocr",
    "small text",
    "fine print",
    "receipt",
    "invoice",
    "contract",
    "document",
    "diagram",
    "chart",
    "table",
    "handwriting",
    "scan",
    "serial number",
    "dense text",
    "blueprint",
    "schematic",
    "tiny text",
    "小字",
    "细节",
    "发票",
    "票据",
    "合同",
    "文档",
    "图表",
    "表格",
    "手写",
    "扫描",
    "序列号",
    "密集文字",
    "看清",
    "识别文字",
)

FAST_KEYWORDS = (
    "quick",
    "quickly",
    "fast",
    "rough",
    "roughly",
    "briefly",
    "simple",
    "classify",
    "label",
    "what is this",
    "what's in",
    "identify",
    "animal",
    "快速",
    "大概",
    "粗略",
    "简单",
    "分类",
    "标签",
    "是什么",
    "看看",
    "大致",
    "动物",
)

MEDIA_RESOLUTION_LEVELS = {
    "auto": None,
    "low": "MEDIA_RESOLUTION_LOW",
    "medium": "MEDIA_RESOLUTION_MEDIUM",
    "high": "MEDIA_RESOLUTION_HIGH",
    "ultra-high": "MEDIA_RESOLUTION_ULTRA_HIGH",
}

SCENE_ROUTES = {
    "detail": {
        "models": [
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-3.1-flash-lite-preview",
        ],
        "default_media_resolution": "high",
        "description": "High-detail OCR, document, and chart extraction.",
    },
    "general": {
        "models": [
            "gemini-2.5-flash",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
        ],
        "default_media_resolution": "auto",
        "description": "Balanced route for standard image QA and tagging.",
    },
    "fast": {
        "models": [
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash-lite",
        ],
        "default_media_resolution": "low",
        "description": "Low-latency route for simple recognition and rough summaries.",
    },
    "basic": {
        "models": [
            "gemini-2.5-flash-lite",
        ],
        "default_media_resolution": "low",
        "description": "Lowest-cost route for basic image recognition.",
    },
}


class GeminiVisionError(Exception):
    def __init__(self, stage, message, details=None):
        super().__init__(message)
        self.stage = stage
        self.message = message
        self.details = details or {}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Analyze an image with Gemini vision models using scene-based routing.",
    )
    route_group = parser.add_mutually_exclusive_group()
    route_group.add_argument(
        "--scene",
        choices=("auto", "detail", "general", "fast", "basic"),
        default=None,
        help="Select a routing scene. Defaults to auto unless --model is set.",
    )
    route_group.add_argument(
        "--model",
        help="Use an explicit Gemini model id and skip scene routing.",
    )
    parser.add_argument(
        "--media-resolution",
        choices=("auto", "low", "medium", "high", "ultra-high"),
        default=None,
        help="Override the default media resolution for the selected route.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved route and config without calling the API.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback models and only try the first model in the route.",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        help="Write structured JSON output to this path.",
    )
    parser.add_argument("image_path", help="Path to the image file.")
    parser.add_argument("question", help="Question or instruction for the image.")
    parser.add_argument(
        "output_json_path",
        nargs="?",
        help="Legacy positional JSON output path kept for compatibility.",
    )

    args = parser.parse_args(argv)
    if args.output_path and args.output_json_path:
        parser.error("Use either the positional output_json_path or --output, not both.")

    args.output_path = args.output_path or args.output_json_path
    args.requested_scene = None if args.model else (args.scene or "auto")
    return args


def get_mime_type(path):
    mime, _ = mimetypes.guess_type(path)
    if mime:
        return mime
    ext = os.path.splitext(path)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
    }.get(ext, "image/png")


def image_to_base64(path):
    with open(path, "rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")


def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def load_api_key():
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key

    env_path = os.path.join(repo_root(), ".env")
    if not os.path.exists(env_path):
        return ""

    with open(env_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or not line.startswith("GEMINI_API_KEY="):
                continue
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def detect_scene(question):
    normalized = question.casefold()
    detail_hits = [keyword for keyword in DETAIL_KEYWORDS if keyword in normalized]
    if detail_hits:
        preview = ", ".join(detail_hits[:3])
        return "detail", "Auto-detected detail scene from keywords: " + preview

    fast_hits = [keyword for keyword in FAST_KEYWORDS if keyword in normalized]
    if fast_hits:
        preview = ", ".join(fast_hits[:3])
        return "fast", "Auto-detected fast scene from keywords: " + preview

    return "general", "Auto-detected general scene because no detail or fast keywords matched."


def build_route(scene, no_fallback):
    route = dict(SCENE_ROUTES[scene])
    route["models"] = list(route["models"])
    if no_fallback and route["models"]:
        route["models"] = route["models"][:1]
    return route


def build_generation_config(scene, media_resolution_override):
    default_media_resolution = "auto"
    if scene in SCENE_ROUTES:
        default_media_resolution = SCENE_ROUTES[scene]["default_media_resolution"]

    resolved_media_resolution = (
        media_resolution_override
        if media_resolution_override is not None
        else default_media_resolution
    )

    return {
        "temperature": DEFAULT_TEMPERATURE,
        "max_output_tokens": DEFAULT_MAX_OUTPUT_TOKENS,
        "media_resolution": resolved_media_resolution,
        "api_media_resolution": MEDIA_RESOLUTION_LEVELS[resolved_media_resolution],
    }


def build_payload(image_path, question, config):
    image_part = {
        "inline_data": {
            "mime_type": get_mime_type(image_path),
            "data": image_to_base64(image_path),
        }
    }
    if config["api_media_resolution"]:
        image_part["media_resolution"] = {"level": config["api_media_resolution"]}

    return {
        "contents": [
            {
                "parts": [
                    {"text": question},
                    image_part,
                ]
            }
        ],
        "generationConfig": {
            "temperature": config["temperature"],
            "maxOutputTokens": config["max_output_tokens"],
        },
    }


def parse_json_text(raw_text):
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return None


def extract_api_error_message(error_payload):
    if isinstance(error_payload, dict):
        if "error" in error_payload and isinstance(error_payload["error"], dict):
            message = error_payload["error"].get("message")
            if message:
                return message
        message = error_payload.get("message")
        if message:
            return message
    return str(error_payload)


def call_generate_content(model, payload, api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent".format(
        model=model
    )
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        parsed_body = parse_json_text(raw_body)
        raise GeminiVisionError(
            "api-call",
            "Gemini API returned HTTP {status} for {model}: {message}".format(
                status=exc.code,
                model=model,
                message=extract_api_error_message(parsed_body or raw_body),
            ),
            {
                "model": model,
                "status_code": exc.code,
                "response": parsed_body or raw_body,
            },
        )
    except urllib.error.URLError as exc:
        raise GeminiVisionError(
            "network",
            "Network error while calling Gemini API for {model}: {reason}".format(
                model=model,
                reason=exc.reason,
            ),
            {"model": model, "reason": str(exc.reason)},
        )
    except OSError as exc:
        raise GeminiVisionError(
            "network",
            "Local network error while calling Gemini API for {model}: {reason}".format(
                model=model,
                reason=exc,
            ),
            {"model": model, "reason": str(exc)},
        )

    response_json = parse_json_text(body)
    if response_json is None:
        raise GeminiVisionError(
            "response-parse",
            "Gemini API returned non-JSON output for {model}.".format(model=model),
            {"model": model, "response": body},
        )

    if "error" in response_json:
        raise GeminiVisionError(
            "api-call",
            "Gemini API returned an error for {model}: {message}".format(
                model=model,
                message=extract_api_error_message(response_json),
            ),
            {"model": model, "response": response_json},
        )

    return response_json


def extract_answer(response_json):
    parts = []
    for candidate in response_json.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            text = part.get("text")
            if text and text.strip():
                parts.append(text.strip())

    if not parts:
        raise GeminiVisionError(
            "response-parse",
            "Gemini API response did not contain any text parts.",
            {"response": response_json},
        )

    return "\n\n".join(parts)


def is_media_resolution_supported(model, api_media_resolution):
    if api_media_resolution != "MEDIA_RESOLUTION_ULTRA_HIGH":
        return True
    return model.startswith("gemini-3")


def run_with_fallback(route, image_path, question, generation_config, api_key):
    attempts = []
    last_error = None

    for model in route["models"]:
        attempt = {
            "model": model,
            "media_resolution": generation_config["media_resolution"],
            "status": "pending",
        }

        if not is_media_resolution_supported(model, generation_config["api_media_resolution"]):
            attempt.update(
                {
                    "status": "skipped",
                    "stage": "validation",
                    "message": (
                        generation_config["media_resolution"]
                        + " is not supported by "
                        + model
                    ),
                }
            )
            attempts.append(attempt)
            continue

        try:
            payload = build_payload(image_path, question, generation_config)
            response_json = call_generate_content(model, payload, api_key)
            answer = extract_answer(response_json)
            attempt["status"] = "success"
            attempts.append(attempt)
            return answer, attempts, None, model
        except GeminiVisionError as exc:
            attempt.update(
                {
                    "status": "failed",
                    "stage": exc.stage,
                    "message": exc.message,
                }
            )
            if "status_code" in exc.details:
                attempt["status_code"] = exc.details["status_code"]
            attempts.append(attempt)
            last_error = exc

    if last_error is None:
        last_error = GeminiVisionError(
            "routing",
            "No compatible Gemini models were available for the requested route.",
            {"attempts": attempts},
        )
    return None, attempts, last_error, None


def build_output_path(path):
    if not path:
        return None
    output_path = os.path.abspath(path)
    parent = os.path.dirname(output_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    return output_path


def emit_result(result, output_path, dry_run):
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        if result["error"] is None:
            print("OK: " + output_path)
        else:
            print("Error: " + result["error"]["message"])
        return

    if dry_run or result["error"] is not None or result["answer"] is None:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(result["answer"])


def resolve_request(args):
    if args.model:
        resolved_scene = "model-override"
        route = {
            "models": [args.model],
            "description": "Explicit model override with fallback disabled.",
        }
        selection_reason = "Explicit --model {model}; scene routing disabled.".format(
            model=args.model
        )
        generation_config = build_generation_config(None, args.media_resolution)
        return args.requested_scene, resolved_scene, selection_reason, route, generation_config

    if args.requested_scene == "auto":
        resolved_scene, selection_reason = detect_scene(args.question)
    else:
        resolved_scene = args.requested_scene
        selection_reason = "Explicit --scene {scene}; {description}".format(
            scene=resolved_scene,
            description=SCENE_ROUTES[resolved_scene]["description"],
        )

    route = build_route(resolved_scene, args.no_fallback)
    generation_config = build_generation_config(resolved_scene, args.media_resolution)
    if args.media_resolution is not None:
        selection_reason += " Media resolution overridden to {value}.".format(
            value=generation_config["media_resolution"]
        )
    if args.no_fallback:
        selection_reason += " Fallback disabled."
    return args.requested_scene, resolved_scene, selection_reason, route, generation_config


def build_result(
    model,
    requested_scene,
    resolved_scene,
    selection_reason,
    image_path,
    question,
    request_config,
    attempts,
    answer,
    error,
):
    return {
        "source": SOURCE_NAME,
        "model": model,
        "requested_scene": requested_scene,
        "resolved_scene": resolved_scene,
        "selection_reason": selection_reason,
        "image_path": image_path,
        "question": question,
        "request_config": request_config,
        "attempts": attempts,
        "answer": answer,
        "error": error,
    }


def main(argv=None):
    args = parse_args(argv)
    image_path = os.path.abspath(args.image_path)
    output_path = build_output_path(args.output_path)
    requested_scene, resolved_scene, selection_reason, route, generation_config = resolve_request(args)
    request_config = {
        "route_models": route["models"],
        "media_resolution": generation_config["media_resolution"],
        "temperature": generation_config["temperature"],
        "max_output_tokens": generation_config["max_output_tokens"],
        "fallback_enabled": (not args.model) and (not args.no_fallback) and len(route["models"]) > 1,
        "dry_run": args.dry_run,
    }

    if not os.path.exists(image_path):
        result = build_result(
            route["models"][0] if route["models"] else args.model,
            requested_scene,
            resolved_scene,
            selection_reason,
            image_path,
            args.question,
            request_config,
            [],
            None,
            {
                "stage": "input-validation",
                "message": "Image not found: " + image_path,
            },
        )
        emit_result(result, output_path, args.dry_run)
        return 1

    if args.dry_run:
        attempts = []
        for model in route["models"]:
            attempt = {
                "model": model,
                "media_resolution": generation_config["media_resolution"],
            }
            if is_media_resolution_supported(model, generation_config["api_media_resolution"]):
                attempt["status"] = "planned"
            else:
                attempt["status"] = "skipped"
                attempt["stage"] = "validation"
                attempt["message"] = (
                    generation_config["media_resolution"] + " is not supported by " + model
                )
            attempts.append(attempt)

        result = build_result(
            route["models"][0] if route["models"] else args.model,
            requested_scene,
            resolved_scene,
            selection_reason,
            image_path,
            args.question,
            request_config,
            attempts,
            None,
            None,
        )
        emit_result(result, output_path, args.dry_run)
        return 0

    api_key = load_api_key()
    if not api_key:
        result = build_result(
            route["models"][0] if route["models"] else args.model,
            requested_scene,
            resolved_scene,
            selection_reason,
            image_path,
            args.question,
            request_config,
            [],
            None,
            {
                "stage": "configuration",
                "message": "GEMINI_API_KEY not set in environment or .env",
            },
        )
        emit_result(result, output_path, args.dry_run)
        return 1

    answer, attempts, error, model = run_with_fallback(
        route,
        image_path,
        args.question,
        generation_config,
        api_key,
    )

    result = build_result(
        model or (route["models"][0] if route["models"] else args.model),
        requested_scene,
        resolved_scene,
        selection_reason,
        image_path,
        args.question,
        request_config,
        attempts,
        answer,
        None
        if error is None
        else {
            "stage": error.stage,
            "message": error.message,
        },
    )
    emit_result(result, output_path, args.dry_run)
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
