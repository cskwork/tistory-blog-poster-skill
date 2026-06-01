#!/usr/bin/env python3
"""Build a deterministic SVG cover for a Korean Tistory SEO post."""

from __future__ import annotations

import argparse
import html
from pathlib import Path


def chunks(text: str, width: int) -> list[str]:
    parts: list[str] = []
    for word in text.split():
        if len(word) <= width:
            parts.append(word)
            continue
        parts.extend(word[i : i + width] for i in range(0, len(word), width))
    return parts


def wrap_lines(text: str, width: int, max_lines: int) -> list[str]:
    words = chunks(" ".join(text.split()), width)
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = lines[-1].rstrip(".") + "..."
    return lines


def text_block(lines: list[str], x: int, y: int, size: int, weight: int) -> str:
    escaped = [html.escape(line) for line in lines]
    return "\n".join(
        f'<text x="{x}" y="{y + index * int(size * 1.25)}" '
        f'font-size="{size}" font-weight="{weight}" fill="#F8FAFC">{line}</text>'
        for index, line in enumerate(escaped)
    )


def build_svg(title: str, subtitle: str, badge: str, category: str, accent: str) -> str:
    title_lines = wrap_lines(title, 19, 3)
    subtitle_lines = wrap_lines(subtitle, 38, 2)
    badge_text = html.escape(badge)
    category_text = html.escape(category)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630">
  <rect width="1200" height="630" fill="#111827"/>
  <path d="M0 0 H1200 V175 L0 310 Z" fill="{accent}" opacity="0.92"/>
  <path d="M735 0 H1200 V630 H890 Z" fill="#0F766E" opacity="0.9"/>
  <path d="M0 470 L1200 250 V630 H0 Z" fill="#27272A" opacity="0.82"/>
  <g stroke="#F8FAFC" stroke-opacity="0.10" stroke-width="1">
    <path d="M80 80 H1120"/><path d="M80 160 H1120"/><path d="M80 240 H1120"/>
    <path d="M80 320 H1120"/><path d="M80 400 H1120"/><path d="M80 480 H1120"/>
    <path d="M160 40 V590"/><path d="M320 40 V590"/><path d="M480 40 V590"/>
    <path d="M640 40 V590"/><path d="M800 40 V590"/><path d="M960 40 V590"/>
  </g>
  <rect x="76" y="76" width="270" height="54" rx="27" fill="#F8FAFC" fill-opacity="0.14"/>
  <text x="104" y="111" font-size="24" font-weight="700" fill="#F8FAFC">{badge_text}</text>
  <text x="84" y="192" font-size="28" font-weight="700" fill="#E5E7EB">{category_text}</text>
  <g font-family="Pretendard, Apple SD Gothic Neo, Noto Sans KR, Arial, sans-serif">
    {text_block(title_lines, 82, 285, 62, 800)}
    {text_block(subtitle_lines, 86, 510, 27, 500)}
  </g>
  <text x="935" y="555" font-family="Arial, sans-serif" font-size="23" font-weight="700" fill="#F8FAFC">AI Insights Lab</text>
  <text x="935" y="588" font-family="Arial, sans-serif" font-size="18" fill="#CBD5E1">SEO Machine</text>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Tistory cover SVG.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--subtitle", default="Korean SEO blog draft")
    parser.add_argument("--badge", default="Codex draft")
    parser.add_argument("--category", default="AI SEO")
    parser.add_argument("--accent", default="#2563EB")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        build_svg(args.title, args.subtitle, args.badge, args.category, args.accent),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
