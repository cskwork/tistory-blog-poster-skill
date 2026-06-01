# Tistory SEO Blog Poster Skill

Reusable skill for preparing Korean SEO posts for Tistory, generating a topic-specific cover image, and drafting or privately publishing through an existing Chrome session.

## What It Does

- Converts a Korean Markdown/Hugo post into a Tistory package.
- Creates `cover_prompt.md` from the title, summary, tags, headings, and body signals.
- Requires a unique topic-specific Codex Image 2.0 `cover.codex.png` for each final post.
- Adds readable Tistory body spacing for paragraphs, headings, lists, tables, blockquotes, and code.
- Uses Playwright Agent CLI against an existing authenticated Chrome session.
- Refuses public publishing unless explicitly confirmed.

## Install

From a standalone clone:

```bash
ln -s "$PWD" ~/.codex/skills/tistory-seo-blog-poster
```

For Claude Code, link the same folder:

```bash
ln -s "$PWD" ~/.claude/skills/tistory-seo-blog-poster
```

## Prepare A Package

```bash
python3 scripts/prepare_tistory_package.py \
  --source /path/to/post.md \
  --output-dir /tmp/tistory-post
```

## Generate A Topic Cover

Read `/tmp/tistory-post/cover_prompt.md` and generate the final cover with Codex Image 2.0. Save the result as `/tmp/tistory-post/cover.codex.png`, then update `package.json`:

- `cover_png`: `/tmp/tistory-post/cover.codex.png`
- `cover_codex`: `/tmp/tistory-post/cover.codex.png`
- `cover_generation_mode`: `codex_image_2`
- `cover_source_image`: original generated-image path

`scripts/build_codex_cover_bitmap.py` and `scripts/build_tistory_cover_svg.py` are preview/fallback helpers only. Do not use them for final upload when real Codex image generation is available.

## Private Publish

Attach Chrome with Playwright CLI first, then run:

```bash
python3 scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json \
  --session tistory-cdp \
  --attach none \
  --target-url "https://YOUR_BLOG.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F" \
  --private-publish \
  --confirm-private-publish
```

## Dependencies

- Python 3.9+
- Pillow for `build_codex_cover_bitmap.py`
- optional ImageMagick for fallback SVG to PNG conversion
- Playwright Agent CLI for browser automation

## Guardrails

- Do not reuse a cover image across posts.
- Reject generic AI banners before upload.
- Do not use local fallback covers for final publishing when Codex Image 2.0 is available.
- Keep Tistory login state in the user's browser; do not export cookies or profiles.
- Use private publish or draft flows unless the user explicitly asks for public publishing.
