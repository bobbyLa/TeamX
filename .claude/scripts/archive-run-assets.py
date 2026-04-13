#!/usr/bin/env python3
"""Copy run-local assets into the archived run and rewrite brief links."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path, PurePosixPath


WIKI_LINK_RE = re.compile(
    r"(?P<embed>!?)\[\[(?P<target>[^\]|#]+)(?P<suffix>(?:#[^\]|]+)?(?:\|[^\]]+)?)\]\]"
)
MARKDOWN_LINK_RE = re.compile(
    r"(?P<embed>!?)\[(?P<label>[^\]]*)\]\((?P<target><[^>]+>|[^)]+)\)"
)
SOURCE_LINE_RE = re.compile(
    r"(?m)^(?P<indent>\s*-\s+)\[(?P<label>[^\]]+)\]\s+(?P<target>\S+)(?P<suffix>\s*)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive local run assets into the vault copy.")
    parser.add_argument("--source-root", required=True, help="Path to runs/<slug>/")
    parser.add_argument("--target-root", required=True, help="Path to archived TeamX/Runs/<slug>/")
    return parser.parse_args()


def is_local_target(raw_target: str) -> bool:
    lowered = raw_target.lower()
    return not (
        "://" in lowered
        or lowered.startswith("mailto:")
        or lowered.startswith("data:")
        or lowered.startswith("#")
        or lowered.startswith("obsidian:")
    )


def unwrap_markdown_target(raw_target: str) -> tuple[str, str]:
    target = raw_target.strip()
    suffix = ""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    else:
        title_match = re.match(r'^(?P<path>.+?)(?P<suffix>\s+"[^"]*"|\s+\'[^\']*\')$', target)
        if title_match:
            target = title_match.group("path")
            suffix = title_match.group("suffix")
    return target, suffix


def resolve_within_source(raw_target: str, source_root: Path) -> tuple[Path, Path] | None:
    raw = raw_target.strip()
    if not raw or not is_local_target(raw):
        return None

    pure = PurePosixPath(raw.replace("\\", "/"))
    if pure.is_absolute():
        candidate = Path(str(pure))
    else:
        parts = pure.parts
        if len(parts) >= 3 and parts[0] == "runs" and parts[1] == source_root.name:
            candidate = source_root.joinpath(*parts[2:])
        else:
            candidate = source_root.joinpath(*parts)

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        return None

    if not resolved.is_file():
        return None

    if os.path.commonpath([str(resolved), str(source_root.resolve())]) != str(source_root.resolve()):
        return None

    relative = resolved.relative_to(source_root.resolve())
    return resolved, relative


def ensure_destination(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def copy_asset(
    resolved: Path,
    relative_source: Path,
    target_root: Path,
    copied: dict[str, str],
) -> str:
    key = str(resolved)
    if key in copied:
        return copied[key]

    destination = ensure_destination(target_root / relative_source)
    shutil.copy2(resolved, destination)
    copied[key] = str(relative_source).replace("\\", "/")
    return copied[key]


def rewrite_content(content: str, source_root: Path, target_root: Path) -> tuple[str, list[dict[str, str]]]:
    migrated: list[dict[str, str]] = []
    copied: dict[str, str] = {}
    brief_path = target_root / "brief.md"

    def note_migration(resolved: Path, relative_source: Path, relative_target: str) -> None:
        if any(item["source"] == str(resolved) for item in migrated):
            return
        migrated.append(
            {
                "source": str(resolved),
                "archived_as": str(target_root / relative_target),
                "brief_link": os.path.relpath(target_root / relative_target, brief_path.parent).replace("\\", "/"),
            }
        )

    def rewrite_target(raw_target: str) -> tuple[str, Path, str] | None:
        resolved_pair = resolve_within_source(raw_target, source_root)
        if not resolved_pair:
            return None
        resolved, relative_source = resolved_pair
        relative_target = copy_asset(resolved, relative_source, target_root, copied)
        note_migration(resolved, relative_source, relative_target)
        relative_link = os.path.relpath(target_root / relative_target, brief_path.parent).replace("\\", "/")
        return relative_link, resolved, relative_target

    def wiki_replacer(match: re.Match[str]) -> str:
        rewritten = rewrite_target(match.group("target"))
        if not rewritten:
            return match.group(0)
        relative_link, _, _ = rewritten
        return f"{match.group('embed')}[[{relative_link}{match.group('suffix')}]]"

    def markdown_replacer(match: re.Match[str]) -> str:
        parsed_target, suffix = unwrap_markdown_target(match.group("target"))
        rewritten = rewrite_target(parsed_target)
        if not rewritten:
            return match.group(0)
        relative_link, _, _ = rewritten
        if " " in relative_link:
            relative_link = f"<{relative_link}>"
        return f"{match.group('embed')}[{match.group('label')}]({relative_link}{suffix})"

    def source_line_replacer(match: re.Match[str]) -> str:
        rewritten = rewrite_target(match.group("target"))
        if not rewritten:
            return match.group(0)
        relative_link, _, _ = rewritten
        if " " in relative_link:
            relative_link = f"<{relative_link}>"
        return f"{match.group('indent')}[{match.group('label')}]({relative_link}){match.group('suffix')}"

    updated = WIKI_LINK_RE.sub(wiki_replacer, content)
    updated = MARKDOWN_LINK_RE.sub(markdown_replacer, updated)
    updated = SOURCE_LINE_RE.sub(source_line_replacer, updated)
    return updated, migrated


def main() -> int:
    args = parse_args()
    source_root = Path(args.source_root).resolve()
    target_root = Path(args.target_root).resolve()
    brief_path = target_root / "brief.md"

    content = brief_path.read_text(encoding="utf-8")
    updated, migrated = rewrite_content(content, source_root, target_root)
    if updated != content:
        brief_path.write_text(updated, encoding="utf-8")

    print(json.dumps({"migrated_count": len(migrated), "migrated": migrated}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
