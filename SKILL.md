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
   - Present the short 작성 방향 체크리스트, do web research (2+ trusted sources for time-sensitive topics), then produce the full finished Korean article: 제목 → 한줄요약 → 인트로 → 본문 → 참고자료. The cover/thumbnail prompt is NOT a body section — keep it out of the published article and deliver it separately (in chat or directly as `cover_prompt.md`); it is for image generation only.
   - If the source is an existing English/Hugo article, translate to natural Korean and strip front matter; preserve code blocks, URLs, product names, numbers, and sourced claims.
   - For this repo, also consult `context/brand-voice.md`, `context/style-guide.md`, `context/seo-guidelines.md`, and `context/internal-links-map.md` when present.
   - Do not invent stats, citations, or internal links. If a claim needs a current source, verify it first.
   - Save the finished article as a Korean Markdown file (e.g. `/tmp/tistory/<slug>/article.ko.md`) for Phase B.

### Phase B — Post to Tistory

3. Prepare the package.
   - Create a deterministic package from the written Korean Markdown with `scripts/prepare_tistory_package.py`. It maps the H1/tags/summary, auto-generates `cover_prompt.md` from the title/summary/body signals, and strips any stray 썸네일 프롬프트 section from the published body so it never ships in the post.
   - Set `--category` to a real category name from the TARGET blog's taxonomy (the sub-category label, e.g. `MCP`, `VectorDB`, `Claude`, `Agents`, `Machine Learning`), not a made-up one. It is stored as the package `categories` and auto-selected at publish time; the editor option's leading `- ` is ignored when matching. If unsure of the blog's categories, open the editor category dropdown once and read the option list before choosing.
   - Keep the body beginner-friendly: shorter paragraphs, first-use jargon definitions, no unnecessary exhaustive background.

4. Create the top image.
   - For every post, generate a new topic-specific bitmap image with a real image model first. Use `agy` or `codex` (see "Cover Image Script"); in this environment `agy` is the verified primary for bulk covers and `codex` is the always-on fallback. Do not reuse the previous post's image, background, layout, palette, or motif.
   - The image must look like a premium custom editorial illustration for the exact article, not a generic AI cover. Read the title, summary, tags, headings, and body excerpt, then make at least three concrete article concepts visible in the scene.
   - Prefer true image-model output for the final cover: cinematic lighting, depth, material detail, strong focal object, and polished 1200x630 composition. Flat vector diagrams are not acceptable as final covers unless the user explicitly asks for a diagram style.
   - Read `cover_prompt` from the package and use that prompt as the source of truth for the image request.
   - Save the generated image next to the package as `cover.codex.png` or `cover.codex.jpg`, then update `package.json` `cover_png` to that file before browser upload.
   - Both `agy` and `codex` are real image-model generators. ALWAYS keep `codex` available as the fallback: whenever the primary generator fails or returns `NO_IMAGE_CAPABILITY` for a cover, immediately retry that cover with `codex` (and vice versa) before giving up. See both commands in "Cover Image Script".
   - HARD 5-MINUTE CAP PER IMAGE (never hang forever). Wrap every `agy`/`codex` image call in a 5-minute timeout: prefix with `timeout 300` / `gtimeout 300` (GNU coreutils), or run as a background task and kill it past 300s. `agy` and `codex` can silently hang at ~0% CPU on a single cover (observed ~18 min stuck). On timeout, KILL the process, then retry that cover ONCE with the OTHER generator (also under `timeout 300`). Do not keep waiting on a stalled generator.
   - `NO_IMAGE_CAPABILITY` from `codex` is USUALLY A TRANSIENT THROTTLE, NOT A DEAD END (verified 2026-06-06). `codex` generates through the OpenAI `gpt-image-2` / "ChatGPT Images 2.0" backend (launched 2026-04-21, compute-heavy "thinking mode"). When it prints `NO_IMAGE_CAPABILITY` it is almost always relaying a short-term rate-limit/fairness throttle that recovers in MINUTES — in one run codex failed at 03:16 and the identical request succeeded at 03:22 (~6 min). It is NOT a capability loss and (on ChatGPT Pro) NOT a plan-quota exhaustion: Pro has no fixed per-image cap; image access is governed by dynamic fairness/stability throttles. The trigger is BURST — firing several image calls in a short window (e.g. a stalled generator plus retries running near-simultaneously) trips the cooldown.
   - Therefore: (1) SERIALIZE cover generation — never run `agy`/`codex` image calls concurrently; one at a time. (2) On `NO_IMAGE_CAPABILITY`/rate-limit, first fall back to the OTHER backend (`agy` uses a separate provider, so it usually works immediately), and/or wait ~5 minutes and RETRY `codex` — do not declare the cover impossible after one failure. (3) Plus accounts (not Pro) do have rolling per-window caps (community-reported ~50 images / rolling 3h); only there does "wait for the window to reset" mean tens of minutes.
   - Only after BOTH `codex` and `agy` fail for a given cover (including after a reset wait) should you stop or, with explicit user consent, use a local preview asset.
   - Use `scripts/build_codex_cover_bitmap.py` or `scripts/build_tistory_cover_svg.py` only as preview/fallback assets. If the user required Codex Image 2.0 and image generation is blocked, stop instead of silently uploading fallback.
   - Use a truthful Codex maker label only when Codex actually prepared the draft or image. Avoid relying on readable text inside the image; the Tistory title field carries the headline.
   - If Tistory rejects SVG upload, render the SVG to PNG with the available browser or image tooling and upload the PNG.

5. Connect to the existing Chrome session.
   - Read `references/playwright-connect.md` before automating the browser.
   - When attach fails (403/timeout/`Could not connect`), PROMPT THE USER first: ask them to open `chrome://inspect/#remote-debugging` and turn ON "Allow remote debugging for this browser instance", and to wait until that page shows `Server running at: 127.0.0.1:9222` (not `Server running at: starting…`, which means it is not up yet). The toggle opens the port but does NOT add `--remote-allow-origins=*`; if attach still times out after the server is running, relaunch Chrome with that flag (deterministic path below).
   - Chrome 136+/148 reality (do NOT relearn this each run): the `chrome://inspect` toggle alone — and `--cdp=chrome` — is NOT enough. The port opens and the WS upgrades, but no CDP data flows without `--remote-allow-origins=*`, so attach dies with `Timeout 30000ms exceeded`. Do not lead with `--cdp=chrome` (it resolves to the bare `/devtools/browser` path → 403/timeout) and do not assume a listening 9222 means it will work.
   - Deterministic path (preserves the user's Tistory login): (re)launch the user's main Chrome WITH the debug flags, then attach with the EXPLICIT GUID WS. The relaunch quits their browser, so confirm with the user or have them run it via `!`:
     - `osascript -e 'quit app "Google Chrome"'; sleep 3; open -na "Google Chrome" --args --remote-debugging-port=9222 "--remote-allow-origins=*"` (quote the `*` or zsh globs it; same default profile keeps the login).
     - `WS="ws://127.0.0.1:9222$(sed -n '2p' "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort")"`
     - `cd /tmp/tistory && npm_config_cache=/private/tmp/npm-cache npx -y @playwright/cli@latest attach --cdp="$WS" --session=tistory-cdp`
   - `/json/version` returns empty/404 on modern Chrome even when the port works — build the WS from line 2 of `DevToolsActivePort` (the GUID path), never from `/json`.
   - If you cannot relaunch the main Chrome, use a dedicated debug profile on a FREE port (FIX B in `references/playwright-connect.md`): `open -na "Google Chrome" --args --remote-debugging-port=9333 "--remote-allow-origins=*" --user-data-dir="$HOME/.chrome-tistory-debug" --no-first-run https://memoryhub.tistory.com/`, then attach to 9333 — but that fresh profile needs a one-time Tistory login.
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
   - The private-publish flow auto-selects the category from the package `categories[0]` (override with `--category`): it opens the `카테고리 선택` combobox and clicks the matching option, ignoring the `- ` prefix. The returned JSON includes `category` and `categorySet`; if `categorySet` is false the name did not match any option and the post stays in 카테고리 없음 (publishing is not blocked). To set a category on an ALREADY-published post, open `/manage/post/<id>`, select the category, then 완료 → 비공개 → 비공개 저장.
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

Generate the real per-post cover with `codex` (verified working as a fallback 2026-06-06). Run inside the package dir so any stray files land in `/tmp`, and never use `--dangerously-bypass-approvals-and-sandbox`. ALWAYS wrap the call in `timeout 300` (`gtimeout 300` on macOS) so a stalled generator cannot hang the run past 5 minutes:

```bash
timeout 300 codex exec -s workspace-write --skip-git-repo-check -C /tmp/tistory-post \
  "Read cover_prompt.md in this directory. Generate a real 1200x630 raster cover image \
   (premium editorial 3D illustration, topic-specific, cinematic lighting/depth) and save it \
   as cover.codex.png. Must be a true image-model bitmap, not an SVG and not a matplotlib/PIL \
   diagram. If you cannot, print exactly NO_IMAGE_CAPABILITY and stop."
```

`agy` is the verified primary generator for bulk covers (2026-06-03) and `codex` above is the always-on fallback - use whichever is available and ALWAYS fall back to the other when one returns `NO_IMAGE_CAPABILITY`. Image generation enforces a quota/rate limit that a large parallel batch can exhaust after roughly 7-8 images; retry the failed covers with the other generator one at a time, and if both fail wait for the limit to reset before retrying. For `agy`, use absolute paths plus `--add-dir` for workspace access, and never pass `--dangerously-skip-permissions` (the file write succeeds without it):

```bash
timeout 300 agy --add-dir /tmp/tistory-post -p \
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
