#!/usr/bin/env python3
"""Create a Tistory posting package from a translated Markdown article."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from build_tistory_cover_svg import build_svg


ACCENTS = ["#2563EB", "#0F766E", "#9333EA", "#DC2626", "#0891B2", "#4F46E5", "#059669"]


def split_front_matter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    return parse_simple_yaml(text[4:end]), text[end + 4 :].lstrip()


def parse_simple_yaml(raw: str) -> dict[str, object]:
    data: dict[str, object] = {}
    for line in raw.splitlines():
        if not line or line.startswith(" ") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = parse_yaml_value(value.strip())
    return data


def parse_yaml_value(value: str) -> object:
    if value in {"", "null", "None"}:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
    return value.strip("\"'")


def first_heading(body: str) -> str:
    match = re.search(r"^#\s+(.+)$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def remove_duplicate_h1(body: str, title: str) -> str:
    pattern = rf"^#\s+{re.escape(title)}\s*\n+"
    return re.sub(pattern, "", body, count=1, flags=re.MULTILINE).strip()


def strip_thumbnail_prompt_section(body: str) -> str:
    """Drop a stray "## 썸네일 프롬프트" (thumbnail/cover prompt) section from the
    published body. The prompt is a cover-generation input only, never reader-facing
    content. Matches a heading whose text contains 썸네일 or thumbnail, removing it
    through the next same-or-higher-level heading (or end of document)."""
    pattern = re.compile(
        r"^(#{1,6})[ \t]*[^\n]*(?:썸네일|thumbnail|cover prompt)[^\n]*\n"
        r"(?:.*?)(?=^#{1,6}[ \t]|\Z)",
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return re.sub(pattern, "", body).strip()


def as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def has_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def choose_accent(title: str, categories: list[str], explicit: str) -> str:
    if explicit:
        return explicit
    key = "|".join([title, *categories]).encode("utf-8")
    index = int(hashlib.sha256(key).hexdigest()[:8], 16) % len(ACCENTS)
    return ACCENTS[index]


def compact_text(text: str, limit: int = 900) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def article_signals(body: str, summary: str) -> str:
    headings = re.findall(r"^#{2,3}\s+(.+)$", body, flags=re.MULTILINE)[:8]
    bullets = re.findall(r"^\s*[-*]\s+(.+)$", body, flags=re.MULTILINE)[:5]
    return compact_text(" | ".join(item for item in [summary, *headings, *bullets] if item))


def build_cover_prompt(title: str, summary: str, body: str, tags: list[str], categories: list[str]) -> str:
    topic = ", ".join([*categories[:1], *tags[:5]])
    signals = article_signals(body, summary)
    return "\n".join(
        [
            "Generate a new, unique 1200x630 bitmap cover image for this Tistory post.",
            "Do not reuse a previous cover, template, layout, background, or motif.",
            "Make the image topic-specific, premium editorial, polished, and suitable for an AI/tech blog.",
            "Use a high-quality image model style: cinematic lighting, depth, material detail, strong composition, and a clear focal object.",
            "This must look like a custom illustration for this exact article, not a generic AI cover.",
            "Visibly represent at least three concrete concepts from the article signals.",
            "Prefer sophisticated 3D editorial illustration, isometric product-style scene, or realistic abstract tech still life.",
            "Avoid flat infographic screenshots, generic AI brains, random network nodes, decorative blobs, stock photos, and abstract gradients unless they directly express the article.",
            "Avoid readable title text; the Tistory title field will carry the headline.",
            "A small abstract Codex maker mark is acceptable, but do not use logos or trademarks.",
            f"Title: {title}",
            f"Summary: {summary}",
            f"Topic cues: {topic}",
            f"Article signals: {signals}",
            "Composition: one clear central metaphor, foreground/midground/background depth, distinct color palette, useful topic details, no template look.",
            "Quality bar: publish-ready hero image; regenerate if it could fit another unrelated AI post.",
            "Output target: PNG or JPG, uploadable as the first image in the Tistory editor.",
        ]
    )


def package_article(source: Path, output_dir: Path, args: argparse.Namespace) -> dict[str, object]:
    raw = source.read_text(encoding="utf-8")
    meta, body = split_front_matter(raw)
    title = args.title or str(meta.get("title") or first_heading(body) or source.stem)
    body = remove_duplicate_h1(body, title)
    body = strip_thumbnail_prompt_section(body)
    summary = args.summary or str(meta.get("description") or meta.get("summary") or "")
    tags = as_list(args.tags or meta.get("tags") or [])
    categories = as_list(args.category or meta.get("categories") or [])
    output_dir.mkdir(parents=True, exist_ok=True)
    body_path = output_dir / "body.ko.md"
    cover_path = output_dir / "cover.svg"
    cover_png_path = output_dir / "cover.png"
    cover_prompt_path = output_dir / "cover_prompt.md"
    package_path = output_dir / "package.json"
    accent = choose_accent(title, categories, args.accent)
    body_path.write_text(body + "\n", encoding="utf-8")
    cover_path.write_text(build_svg(title, summary, args.badge, categories[0] if categories else "AI SEO", accent), encoding="utf-8")
    cover_prompt_path.write_text(build_cover_prompt(title, summary, body, tags, categories) + "\n", encoding="utf-8")
    cover_png = convert_png(cover_path, cover_png_path) if not args.no_png else None
    package = {
        "title": title,
        "summary": summary,
        "tags": tags,
        "categories": categories,
        "body_markdown": str(body_path),
        "cover_image": str(cover_path),
        "cover_png": str(cover_png) if cover_png else "",
        "cover_prompt": str(cover_prompt_path),
        "cover_policy": "codex_image_per_post_required; svg_png_is_fallback_only",
        "source": str(source),
        "status": "draft",
        "korean_check": {"title": has_korean(title), "body": has_korean(body)},
    }
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return package


def convert_png(source: Path, output: Path) -> Path | None:
    magick = shutil.which("magick")
    if not magick:
        return None
    subprocess.run([magick, str(source), str(output)], check=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a Korean Tistory posting package.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--title")
    parser.add_argument("--summary")
    parser.add_argument("--tags", nargs="*")
    parser.add_argument("--category", nargs="*")
    parser.add_argument("--badge", default="Codex draft")
    parser.add_argument("--accent", default="")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args()
    package = package_article(args.source, args.output_dir, args)
    if not package["korean_check"]["title"] or not package["korean_check"]["body"]:
        print("warning: package does not look fully Korean; translate before Tistory posting", file=sys.stderr)
    print(json.dumps(package, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
