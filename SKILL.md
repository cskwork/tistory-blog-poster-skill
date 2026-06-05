---
name: tistory-seo-blog-poster
description: Use when the user wants a Tistory blog post. The skill WRITES the Korean article first (from a keyword, topic, link, memo, or existing source, following the Korean blog writing standard), THEN runs the posting pipeline — generate a Codex cover, attach to the user's logged-in Chrome via Playwright CLI, upload the cover, render the body, and save the Tistory post as private. Trigger for Tistory, tistory.com, 글쓰기, "블로그 글 작성", "네이버/티스토리 블로그용", Korean blog posting, SEO article publishing, browser-session reuse, Playwright CLI automation, or cover-image generation for blog posts.
---

# Tistory SEO Blog Poster

## Overview

For a Tistory blog request, writing comes first, posting second:

- **Phase A — Write.** Turn the user's keyword/topic/link/memo (or an existing source article) into a finished, publish-ready Korean article, following `references/korean-blog-writing.md`. Do the web research and produce the full body BEFORE touching the browser.
- **Phase B — Post.** Package the written article, generate a real per-post Codex cover, attach to the user's already-authenticated Chrome via Playwright CLI, upload the cover first, render readable Korean body HTML, and save the Tistory post as private for the user to review.

Prefer the Playwright Agent CLI (it attaches to the real browser); use MCP only when the CLI path is unavailable. In the SEO Machine workflow this is the final distribution step. Public conversion stays the user's manual action.

## Workflow

### Phase A — Write the Korean article first

1. Confirm inputs and side effects.
   - Identify what to write from: a keyword/topic/link/memo, or an existing source (article path, URL, pasted content).
   - Identify the target Tistory blog if the user provided one.
   - Treat public publishing as a side effect. Save as a private draft and stop for review unless the user explicitly says to publish publicly now.
   - Never ask for passwords or 2FA codes. If Tistory shows a login wall, ask the user to log in inside Chrome, then reconnect.

2. Write the article following `references/korean-blog-writing.md`.
   - This is the primary content step and happens BEFORE any browser work.
   - Present the short 작성 방향 체크리스트, do web research (2+ trusted sources for time-sensitive topics), then produce the full finished Korean article: 제목 → 한줄요약 → 썸네일 프롬프트 → 인트로 → 본문 → 참고자료.
   - If the source is an existing English/Hugo article, translate to natural Korean and strip front matter; preserve code blocks, URLs, product names, numbers, and sourced claims.
   - For this repo, also consult `context/brand-voice.md`, `context/style-guide.md`, `context/seo-guidelines.md`, and `context/internal-links-map.md` when present.
   - Do not invent stats, citations, or internal links. If a claim needs a current source, verify it first.
   - Save the finished article as a Korean Markdown file (e.g. `/tmp/tistory/<slug>/article.ko.md`) for Phase B.

### Phase B — Post to Tistory

3. Prepare the package.
   - Create a deterministic package from the written Korean Markdown with `scripts/prepare_tistory_package.py`. It maps the H1/tags/summary and carries the 썸네일 프롬프트 into `cover_prompt.md`.
   - Keep the body beginner-friendly: shorter paragraphs, first-use jargon definitions, no unnecessary exhaustive background.

4. Create the top image.
   - For every post, generate a new topic-specific bitmap image with a real image model first. Both `codex` and the `agy` CLI generate real covers (see "Cover Image Script"); use one as the primary and ALWAYS keep the other - codex in particular - available as the fallback. Do not reuse the previous post's image, background, layout, palette, or motif.
   - The image must look like a premium custom editorial illustration for the exact article, not a generic AI cover. Read the title, summary, tags, headings, and body excerpt, then make at least three concrete article concepts visible in the scene.
   - Prefer true image-model output for the final cover: cinematic lighting, depth, material detail, strong focal object, and polished 1200x630 composition. Flat vector diagrams are not acceptable as final covers unless the user explicitly asks for a diagram style.
   - Read `cover_prompt` from the package and use that prompt as the source of truth for the image request.
   - Save the generated image next to the package as `cover.codex.png` or `cover.codex.jpg`, then update `package.json` `cover_png` to that file before browser upload.
   - Both `codex` and `agy` are real image-model generators. ALWAYS keep `codex` available as the fallback: whenever the primary generator fails or returns `NO_IMAGE_CAPABILITY` for a cover, immediately retry that cover with `codex` (and vice versa) before giving up. See both commands in "Cover Image Script".
   - Image generation enforces a quota/rate limit. A large parallel batch can exhaust it partway through (seen at roughly 7-8 images), after which calls return `NO_IMAGE_CAPABILITY` for the remainder. Retry the failed covers with the OTHER generator one at a time, and if both still return `NO_IMAGE_CAPABILITY`, wait for the limit to reset and retry.
   - Use `scripts/build_codex_cover_bitmap.py` or `scripts/build_tistory_cover_svg.py` only as preview/fallback assets. If the user required Codex Image 2.0 and image generation is blocked, stop instead of silently uploading fallback.
   - Use a truthful Codex maker label only when Codex actually prepared the draft or image. Avoid relying on readable text inside the image; the Tistory title field carries the headline.
   - If Tistory rejects SVG upload, render the SVG to PNG with the available browser or image tooling and upload the PNG.

5. Connect to the existing Chrome session.
   - Read `references/playwright-connect.md` before automating the browser.
   - Preferred (verified 2026-06-02): `npx -y @playwright/cli@latest attach --cdp=chrome --session=tistory-cdp`. This attaches to the user's already-running Chrome, preserves the Tistory login, AND allows cover upload — extension attach could not do both.
   - The global `playwright-cli` (e.g. v0.1.0) has NO `attach` subcommand and launches its own login-less browser; use `npx @playwright/cli@latest` for attach and all session commands.
   - `attach` exits 0 immediately but the session persists under `.playwright-cli/` in the cwd. Run every later command from the SAME cwd and `-s=tistory-cdp`.
   - Verify with `npx -y @playwright/cli@latest -s=tistory-cdp tab-list` and `... snapshot` before interacting.
   - Use `scripts/tistory_playwright_cli.py` for repeatable open/fill/publish steps.

6. Open Tistory 글쓰기.
   - Known blog host (this repo): `memoryhub.tistory.com`; new-post URL `https://memoryhub.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F`.
   - Otherwise start from `https://www.tistory.com/` and navigate by visible Korean labels: `글쓰기`, `제목을 입력하세요`, `글 내용 입력`, `첨부`→`사진`, `카테고리`, `태그`, `완료`.
   - On opening newpost, Tistory may raise a confirm() restore dialog ("저장된 글이 있습니다. 이어서 작성하시겠습니까?"). It blocks run-code with `does not handle the modal state`. The helper now handles this by doing `goto` then `dialog-dismiss` as separate CLI steps before any run-code — do NOT goto inside a run-code script.

7. Draft the post.
   - Upload or insert the cover image first so it appears at the top of the post.
   - Fill the title, body, category, tags, and summary/meta fields from the prepared Korean package.
   - For long bodies, set the TinyMCE content via the helper's `--tinymce-body` / private-publish scripts rather than typing. Confirm visible text after insertion.
   - The helper demotes body headings one level (h1→h2, h2→h3) so the Tistory title stays the only H1 and the body keeps a clean SEO heading hierarchy.
   - For SEO Machine final distribution, use private publish (`비공개 저장`) by default via `--private-publish --confirm-private-publish`. Public conversion is the user's final action; never click public publish without explicit approval in the current request.
   - The helper now treats a CLI `### Error` line as failure (nonzero exit) and asserts the editor reports a cover image before returning, so partial failures surface instead of looking successful.

8. Verify before claiming completion.
   - Capture a browser screenshot or preview state showing the title, cover image, first body section, tags/category, and publish/draft state.
   - Compare the visible Tistory draft against the prepared Korean source for title, section order, links, and code blocks.
   - If published, report the final public URL and verify it loads.

## Cover Image Script

Create a complete posting package from a Korean Markdown file:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/prepare_tistory_package.py \
  --source /tmp/article.ko.md \
  --output-dir /tmp/tistory-post
```

The package contains `package.json`, `body.ko.md`, `cover_prompt.md`, `cover.svg`, and `cover.png` when ImageMagick is available. `cover.svg`/`cover.png` are fallback assets; use `cover_prompt.md` to make a fresh `agy`/`codex` image per post before posting.

Generate the real per-post cover with `codex`. Run inside the package dir so any stray files land in `/tmp`, and never use `--dangerously-bypass-approvals-and-sandbox`:

```bash
codex exec -s workspace-write --skip-git-repo-check -C /tmp/tistory-post \
  "Read cover_prompt.md in this directory. Generate a real 1200x630 raster cover image \
   (premium editorial 3D illustration, topic-specific, cinematic lighting/depth) and save it \
   as cover.codex.png. Must be a true image-model bitmap, not an SVG and not a matplotlib/PIL \
   diagram. If you cannot, print exactly NO_IMAGE_CAPABILITY and stop."
```

`agy` is an alternative real image-model generator and the always-on fallback - whenever `codex` returns `NO_IMAGE_CAPABILITY` (commonly when a parallel batch exhausts the shared image quota after roughly 7-8 images), retry that cover with `agy` one at a time, and vice versa. Use absolute paths plus `--add-dir` for workspace access, and never pass `--dangerously-skip-permissions` (the file write succeeds without it):

```bash
agy --add-dir /tmp/tistory-post -p \
  "Read cover_prompt.md in /tmp/tistory-post. Generate a real 1200x630 raster cover image \
   (premium editorial 3D illustration, topic-specific, cinematic lighting/depth) and save it \
   as /tmp/tistory-post/cover.codex.png. It must be a true image-model bitmap, not an SVG and not \
   a matplotlib/PIL diagram. If you cannot, print exactly NO_IMAGE_CAPABILITY and stop."
```

Only if BOTH `codex` and `agy` cannot produce an image (including after a reset wait), and the user accepts fallback publishing, use the local SVG/PNG preview assets. Otherwise stop.

Then point the package at it before upload:

```bash
python3 - <<'PY'
import json, os
d = "/tmp/tistory-post"; p = os.path.join(d, "package.json")
j = json.load(open(p)); j["cover_png"] = os.path.join(d, "cover.codex.png")
json.dump(j, open(p, "w"), ensure_ascii=False, indent=2)
PY
```

Visually inspect the PNG and reject any generic/reused/diagram-like cover before upload. For many posts, covers are independent and can run in parallel background batches: put the generation command in a small per-slug helper script and fan out with `xargs -P 3 -n1 helper.sh` (an inline `xargs -I {}` body carrying the full prompt fails with `command line cannot be assembled, too long`). Keep concurrency low (around 3), and expect the quota to cut in mid-batch - retry the stragglers with the other generator one at a time, or after a reset wait.

Open Tistory with Playwright CLI and stop after a snapshot:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json
```

After a snapshot exposes current refs, fill a draft without publishing:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json \
  --title-target e12 \
  --tinymce-body \
  --cover-button-target e15 \
  --tags-target e24 \
  --save-target e30
```

When a cover is already uploaded in the active editor, reuse the page without navigation:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json \
  --session tistory-cdp \
  --attach none \
  --skip-open \
  --tinymce-body \
  --title-target e21 \
  --tags-target e118
```

Private-publish end-to-end in one call (verified). Navigates to newpost, dismisses the restore dialog, fills title, uploads the cover, inserts the body, adds tags, and saves as `비공개`:

```bash
cd /tmp && python3 .claude/skills/tistory-seo-blog-poster/scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json \
  --cli "npx @playwright/cli@latest" --npm-cache /private/tmp/npm-cache \
  --session tistory-cdp --attach none \
  --target-url "https://memoryhub.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F" \
  --private-publish --confirm-private-publish
```

For multiple posts, loop this sequentially (one shared browser tab — do not run in parallel). A successful run prints a final JSON with `"hasCover":true` and a `/manage/posts/` URL.

Create only a fallback cover SVG:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/build_tistory_cover_svg.py \
  --title "Playwright CLI로 티스토리 자동화하기" \
  --subtitle "기존 Chrome 세션을 재사용하는 SEO 게시 워크플로우" \
  --output /tmp/tistory-cover.svg
```

Use `--badge`, `--category`, and `--accent` when the fallback image needs different labeling or color. If no accent is passed, the package generator chooses a post-specific fallback accent from the title/category hash.

## References

- `references/korean-blog-writing.md`: Phase A writing standard — how to write the Korean article (structure, sections, tone, research, output rules) before posting.
- `references/playwright-connect.md`: CLI-first browser attachment, CDP-chrome preferred path, MCP fallback, and safety checks.
- `references/tistory-editor.md`: Tistory field mapping, editor handling, restore-dialog/modal handling, and publish gate.

## Guardrails

- Do not store Tistory cookies, passwords, or exported browser profiles in the repo.
- Do not use selectors copied from a prior run without validating the current snapshot.
- Do not upload the same Codex image across different posts. Each final post needs a new generated image based on its own `cover_prompt.md`; fallback SVGs are preview assets unless the user explicitly accepts fallback publishing.
- Reject generic or low-polish covers before upload. If the image could fit any AI post, looks like a reusable template, or reads as a simple diagram rather than publish-ready editorial art, regenerate it with stronger topic cues from the article headings/body.
- In extension attach mode, file upload may fail with `fileChooser.setFiles ... Not allowed`; try CDP mode or a manual chooser handoff before treating the package as broken.
- Tistory's TinyMCE `getContent()` may store uploaded images as `[##_Image...]` placeholders while the visible editor iframe shows `<img>`; verify both content and visible frame before re-uploading.
- Do not click final publish controls unless the user explicitly approved publishing in the current task.
- Do not publicly publish SEO Machine posts by default. Private Tistory publishing is allowed only when the user has approved private publishing in the current task or command.
- Do not use demo/reference copy as if it were the user's article.
