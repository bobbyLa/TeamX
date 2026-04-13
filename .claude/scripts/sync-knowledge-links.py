#!/usr/bin/env python3
"""Append related knowledge links for a target atom and backlink peer atoms."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_SECTION_HEADING = "## \u76f8\u5173"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Knowledge/ related links for one note.")
    parser.add_argument("--path", required=True, help="Absolute path to a Knowledge atom note.")
    return parser.parse_args()


def parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    data: dict[str, object] = {}
    current_key: str | None = None
    body_start = 0

    for idx, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if stripped == "---":
            body_start = idx + 1
            break
        if not stripped or stripped.startswith("#"):
            current_key = None
            continue
        if current_key and stripped.startswith("- "):
            current = data.setdefault(current_key, [])
            if isinstance(current, list):
                current.append(stripped[2:].strip().strip('"').strip("'"))
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
            inner = value[1:-1].strip()
            data[key] = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
            continue
        data[key] = value.strip().strip('"').strip("'")

    body = "\n".join(lines[body_start:])
    if text.endswith("\n"):
        body += "\n"
    return data, body


def load_note(path: Path) -> dict[str, object] | None:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    if frontmatter.get("type") != "knowledge-atom":
        return None

    tags = frontmatter.get("tags")
    if not isinstance(tags, list):
        return None

    title = frontmatter.get("title")
    if not isinstance(title, str) or not title.strip():
        title = path.stem

    return {
        "path": path,
        "text": text,
        "frontmatter": frontmatter,
        "body": body,
        "tags": [tag for tag in tags if isinstance(tag, str)],
        "title": title.strip(),
    }


def is_related_section(section_lines: list[str]) -> bool:
    saw_list_item = False
    for line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            saw_list_item = True
            continue
        return False
    return saw_list_item


def find_related_section(body_lines: list[str]) -> tuple[int | None, int | None]:
    start = None
    end = None

    for idx, line in enumerate(body_lines):
        if line.strip() == DEFAULT_SECTION_HEADING:
            start = idx
            end = len(body_lines)
            for jdx in range(idx + 1, len(body_lines)):
                if body_lines[jdx].startswith("## "):
                    end = jdx
                    break
            return start, end

    heading_indices = [idx for idx, line in enumerate(body_lines) if line.startswith("## ")]
    for idx in reversed(heading_indices):
        end = len(body_lines)
        for jdx in range(idx + 1, len(body_lines)):
            if body_lines[jdx].startswith("## "):
                end = jdx
                break
        if is_related_section(body_lines[idx + 1 : end]):
            return idx, end

    return None, None


def ensure_section(body: str, lines_to_add: list[str]) -> tuple[str, bool]:
    if not lines_to_add:
        return body, False

    body_lines = body.splitlines()
    if not body_lines:
        body_lines = []

    start, end = find_related_section(body_lines)
    changed = False

    if start is None or end is None:
        if body_lines and body_lines[-1].strip():
            body_lines.append("")
        body_lines.append(DEFAULT_SECTION_HEADING)
        body_lines.extend(lines_to_add)
        changed = True
    else:
        section_lines = body_lines[start + 1 : end]
        existing = {line.strip() for line in section_lines if line.strip()}
        if "- (none)" in existing and lines_to_add:
            section_lines = [line for line in section_lines if line.strip() != "- (none)"]
            existing.discard("- (none)")
            changed = True
        for line in lines_to_add:
            if line.strip() not in existing:
                section_lines.append(line)
                existing.add(line.strip())
                changed = True
        body_lines = body_lines[: start + 1] + section_lines + body_lines[end:]

    updated = "\n".join(body_lines)
    if updated and not updated.endswith("\n"):
        updated += "\n"
    return updated, changed


def rewrite_note(path: Path, text: str, updated_body: str) -> None:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        path.write_text(updated_body, encoding="utf-8")
        return

    end_idx = None
    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        path.write_text(updated_body, encoding="utf-8")
        return

    frontmatter_block = "\n".join(lines[: end_idx + 1])
    new_text = frontmatter_block + "\n" + updated_body
    path.write_text(new_text, encoding="utf-8")


def wikilink(team_root: Path, note_path: Path, title: str) -> str:
    relative = note_path.relative_to(team_root).with_suffix("")
    return f"- [[{relative.as_posix()}|{title}]]"


def main() -> int:
    target_path = Path(parse_args().path).resolve()
    parts = target_path.parts
    if "TeamX" not in parts or "Knowledge" not in parts:
        raise SystemExit("target note is not inside TeamX/Knowledge")

    knowledge_idx = parts.index("Knowledge")
    team_idx = knowledge_idx - 1
    if team_idx < 0 or parts[team_idx] != "TeamX":
        raise SystemExit("could not resolve TeamX root from target path")

    team_root = Path(*parts[: team_idx + 1])
    knowledge_root = Path(*parts[: knowledge_idx + 1])

    target_note = load_note(target_path)
    if target_note is None:
        raise SystemExit("target note is not a knowledge atom")

    target_tags = {tag for tag in target_note["tags"] if tag != "teamx"}
    candidates: list[tuple[int, dict[str, object]]] = []
    for candidate_path in knowledge_root.rglob("*.md"):
        if candidate_path.resolve() == target_path:
            continue
        candidate_note = load_note(candidate_path)
        if candidate_note is None:
            continue
        overlap = target_tags & {tag for tag in candidate_note["tags"] if tag != "teamx"}
        if overlap:
            candidates.append((len(overlap), candidate_note))

    candidates.sort(key=lambda item: (-item[0], str(item[1]["path"])))
    top_matches = [note for _, note in candidates[:5]]

    target_lines = [wikilink(team_root, note["path"], str(note["title"])) for note in top_matches]
    updated_body, target_changed = ensure_section(str(target_note["body"]), target_lines)
    if target_changed:
        rewrite_note(target_path, str(target_note["text"]), updated_body)

    backlink_updates = 0
    backlink_line = wikilink(team_root, target_path, str(target_note["title"]))
    for note in top_matches:
        candidate_body, changed = ensure_section(str(note["body"]), [backlink_line])
        if changed:
            rewrite_note(Path(note["path"]), str(note["text"]), candidate_body)
            backlink_updates += 1

    print(
        f"target_updated={int(target_changed)} related_count={len(top_matches)} backlinks_updated={backlink_updates}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
