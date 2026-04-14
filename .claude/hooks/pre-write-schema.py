#!/usr/bin/env python3
"""Validate TeamX vault note schemas before Write tool calls land on disk."""

from __future__ import annotations

import json
import re
import sys
from pathlib import PurePosixPath


TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_path(path: str) -> str:
    return re.sub(r"/+", "/", path.replace("\\", "/"))


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [strip_quotes(item.strip()) for item in inner.split(",") if item.strip()]


def parse_frontmatter(text: str) -> tuple[dict[str, object], list[str], dict[str, str | None]]:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["missing YAML frontmatter"], {}

    data: dict[str, object] = {}
    errors: list[str] = []
    quote_styles: dict[str, str | None] = {}
    current_key: str | None = None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break

        if not stripped or stripped.startswith("#"):
            current_key = None
            continue

        if current_key and stripped.startswith("- "):
            value = strip_quotes(stripped[2:].strip())
            current = data.setdefault(current_key, [])
            if isinstance(current, list):
                current.append(value)
            continue

        current_key = None
        if ":" not in line:
            continue

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()

        if not value:
            data[key] = []
            current_key = key
            continue

        if value.startswith("[") and value.endswith("]"):
            data[key] = parse_inline_list(value)
            continue

        quoted = len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}
        quote_styles[key] = value[0] if quoted else None
        if not quoted and ": " in value:
            errors.append(
                f"frontmatter field '{key}' must be quoted because its value contains ': '"
            )
        data[key] = strip_quotes(value)

    return data, errors, quote_styles


def as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def require_string(frontmatter: dict[str, object], field: str, errors: list[str]) -> str:
    value = frontmatter.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing frontmatter field: {field}")
        return ""
    return value.strip()


def classify_lane(path: str) -> tuple[str, PurePosixPath] | None:
    pure = PurePosixPath(path)
    parts = pure.parts
    try:
        team_idx = len(parts) - 1 - parts[::-1].index("TeamX")
    except ValueError:
        return None

    tail = PurePosixPath(*parts[team_idx:])
    tail_parts = tail.parts
    if len(tail_parts) >= 4 and tail_parts[1] == "Runs" and tail_parts[-1] == "brief.md":
        return "runs-brief", tail
    if len(tail_parts) >= 3 and tail_parts[1] == "Daily" and tail.suffix == ".md":
        return "daily", tail
    if len(tail_parts) >= 4 and tail_parts[1] == "Knowledge" and tail.suffix == ".md":
        return "knowledge", tail
    return None


def validate_runs_brief(
    path: PurePosixPath,
    frontmatter: dict[str, object],
    quote_styles: dict[str, str | None],
) -> list[str]:
    errors: list[str] = []
    slug = require_string(frontmatter, "slug", errors)
    created = require_string(frontmatter, "created", errors)

    for field in ("title", "question"):
        value = require_string(frontmatter, field, errors)
        if value and quote_styles.get(field) != '"':
            errors.append(f"frontmatter field '{field}' must use double quotes")

    tags = as_list(frontmatter.get("tags"))
    if "teamx" not in tags:
        errors.append("tags must contain teamx")

    sources = as_list(frontmatter.get("sources"))
    if not sources:
        errors.append("sources must be a non-empty list")

    path_slug = path.parts[2]
    if slug and slug != path_slug:
        errors.append(f"frontmatter slug '{slug}' does not match folder '{path_slug}'")
    if created and not TS_RE.match(created):
        errors.append("created must be YYYY-MM-DD or UTC timestamp ending in Z")

    return errors


def validate_daily(path: PurePosixPath, frontmatter: dict[str, object]) -> list[str]:
    errors: list[str] = []
    date_value = require_string(frontmatter, "date", errors)
    tags = as_list(frontmatter.get("tags"))
    runs = frontmatter.get("runs")

    filename_date = path.stem
    if date_value and date_value != filename_date:
        errors.append(f"date '{date_value}' does not match filename '{filename_date}'")
    if date_value and not DATE_RE.match(date_value):
        errors.append("date must use YYYY-MM-DD")
    if "teamx" not in tags or "daily" not in tags:
        errors.append("tags must contain both teamx and daily")
    if runs is None:
        errors.append("runs frontmatter list is required (use [] when empty)")
    elif not isinstance(runs, list):
        errors.append("runs must be a YAML list")

    return errors


def validate_knowledge(path: PurePosixPath, frontmatter: dict[str, object]) -> list[str]:
    errors: list[str] = []
    note_type = require_string(frontmatter, "type", errors)
    source_run = require_string(frontmatter, "source_run", errors)
    confidence = require_string(frontmatter, "confidence", errors)
    created = require_string(frontmatter, "created", errors)

    require_string(frontmatter, "title", errors)
    require_string(frontmatter, "source_claim_id", errors)

    tags = as_list(frontmatter.get("tags"))
    if "teamx" not in tags:
        errors.append("tags must contain teamx")

    non_teamx_tags = [tag for tag in tags if tag != "teamx"]
    if not non_teamx_tags:
        errors.append("knowledge atom needs at least one non-teamx tag")
    else:
        topic_folder = path.parts[2]
        if non_teamx_tags[0] != topic_folder:
            errors.append(
                f"first non-teamx tag '{non_teamx_tags[0]}' does not match topic folder '{topic_folder}'"
            )

    if note_type and note_type != "knowledge-atom":
        errors.append("type must equal knowledge-atom")
    if confidence and confidence not in {"high", "medium", "low"}:
        errors.append("confidence must be one of: high, medium, low")
    if created and not DATE_RE.match(created):
        errors.append("created must use YYYY-MM-DD")
    if source_run and not (source_run.startswith("[[Runs/") and source_run.endswith("]]")):
        errors.append("source_run must be a wikilink into Runs/")

    return errors


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0

    path = payload.get("file_path")
    content = payload.get("content")
    if not isinstance(path, str) or not isinstance(content, str) or not content.strip():
        return 0

    classified = classify_lane(normalize_path(path))
    if not classified:
        return 0

    lane, tail = classified
    frontmatter, parse_errors, quote_styles = parse_frontmatter(content)
    if not frontmatter:
        for error in parse_errors:
            print(f"pre-write-schema: {error}", file=sys.stderr)
        return 2

    if lane == "runs-brief":
        errors = validate_runs_brief(tail, frontmatter, quote_styles)
    elif lane == "daily":
        errors = validate_daily(tail, frontmatter)
    else:
        errors = validate_knowledge(tail, frontmatter)
    errors = [*parse_errors, *errors]

    if errors:
        print(f"pre-write-schema: refusing write to {path}", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
