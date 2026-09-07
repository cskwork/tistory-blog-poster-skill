---
name: tistory-seo-blog-poster
description: Write a Korean article and prepare or save it in the Tistory editor, with a topic-specific cover and verified private status by default. Use for Tistory article/draft/posting requests; generic blog writing or image-only requests do not imply Tistory access.
---

# Tistory SEO Blog Poster

Write the article before posting it. Follow the requested delivery scope: article-only work ends with the artifact; a Tistory posting request saves privately by default. Public publishing requires explicit authorization, which persists for the same article and unchanged scope.

## Phase A — Write

1. Identify the source/topic, intended blog, audience, and delivery status from the request and existing context. Ask only for information that changes the result. Do not default to an example blog or use an authenticated account merely because it is available.
2. Read [references/korean-blog-writing.md](references/korean-blog-writing.md). Research claims that need current evidence and write the complete Korean article. Use relevant repository brand/style/SEO/internal-link guidance when present. Preserve source code, URLs, names, numbers, and supported claims; do not invent statistics or links.
3. Save `article.ko.md` in a task-specific directory. Keep the image prompt separate from the article body. For existing articles, apply the requested translation/editing scope without silently rewriting content the user asked to preserve.

## Phase B — Package and cover

Resolve helper paths relative to this installed skill directory:

```bash
python3 <skill-dir>/scripts/prepare_tistory_package.py \
  --source /abs/article.ko.md --output-dir /abs/tistory-post
```

The package contains `package.json`, `body.ko.md`, `cover_prompt.md`, and preview/fallback cover assets. Set `--category` from the target blog's current taxonomy; use the actual subcategory label, not an invented value. If the category is unknown, inspect the live selector once before choosing it.

Generate a fresh topic-specific bitmap from `cover_prompt.md` using the user's requested image tool or an available authorized image model. Reflect concrete article concepts; follow the requested visual style rather than forcing a particular palette or 3D treatment. Do not reuse an unrelated previous cover. Save it beside the package and update `package.json` → `cover_png` to its actual path.

For CLI-based generation, use a bounded timeout (the existing default is 300 seconds) and terminate only the process started for this task. On failure, inspect the actual error. One permitted alternative provider or a retry guided by an explicit rate-limit response is reasonable; do not infer account quotas, capability loss, or a fixed cooldown from `NO_IMAGE_CAPABILITY`. Avoid overlapping duplicate submissions. Never bypass sandbox/approval settings.

Local bitmap/SVG scripts are preview/fallback tools. Use them as the final cover only when the user accepts that substitution; do not silently replace a specifically requested image model. Inspect the final image before upload. Label the maker truthfully; do not rely on generated image text for the article title.

## Phase C — Connect and fill

Read [references/playwright-connect.md](references/playwright-connect.md) for browser attachment and [references/tistory-editor.md](references/tistory-editor.md) for editor behavior.

- Prefer the available authorized browser connection that preserves the user's login. Verify the current tab and target blog before changing it. A login wall requires the user to log in; never request passwords, 2FA codes, or exported cookies.
- Use a task-specific tab and keep one CLI session/working directory for related steps. Do not relaunch the user's browser or weaken remote-debugging restrictions as a routine fix.
- Inspect an existing draft before navigating to newpost. The helper's private-publish flow dismisses the restore dialog to start fresh; do not use that path when it could discard unrelated unsaved work. Separate navigation/dialog handling from subsequent run-code calls.
- Upload the cover first, then fill the title, body, category and tags from the package. For a long body, use the helper's TinyMCE path and verify visible content afterward.
- Refresh snapshots after UI changes. Never reuse example element refs or a previous run's selector blindly.

Inspect helper commands without browser actions when needed:

```bash
python3 <skill-dir>/scripts/tistory_playwright_cli.py \
  --package /abs/tistory-post/package.json --dry-run
```

For an authorized private save in the verified target blog, the helper accepts `--private-publish --confirm-private-publish`. Configure its current session, attachment and target URL explicitly from observed state. These flags express the existing task authorization; they do not require a second approval question.

The helper demotes body headings one level so Tistory's title remains the only H1. Its returned `categorySet:false` means no category matched even if save succeeded: resolve the requested category or report the gap. A CLI `### Error` is failure, not a successful save. `hasCover:true` checks image presence but does not alone prove the right cover or durable save.

## Phase D — Verify saved state

After saving, verify both the management-list entry and the reopened post/editor. Confirm title, correct cover, body section order, links/code blocks, category/tags, and actual private/public status against the prepared source. A preview or successful button click alone is not durable-save proof.

Tistory may encode uploaded images as `[##_Image...]` in TinyMCE `getContent()` while the visible iframe contains `<img>`; inspect both before uploading a duplicate. If upload is blocked by the connection transport, use an available authorized alternative or a manual chooser handoff.

Return the article/post link, actual saved status, checks performed, and any unresolved mismatch. If public release was explicitly requested, verify the public URL after that action; otherwise leave the post private. Keep cookies, credentials, and browser state out of the repository, and remove only task-created transient material when no longer needed.

## Resources

- [references/korean-blog-writing.md](references/korean-blog-writing.md): Korean writing structure, research, and source treatment.
- [references/playwright-connect.md](references/playwright-connect.md): current-capability attachment and recovery boundaries.
- [references/tistory-editor.md](references/tistory-editor.md): field mapping, helper options, TinyMCE and save behavior.
- `scripts/build_codex_cover_bitmap.py`, `scripts/build_tistory_cover_svg.py`: optional preview/fallback assets.
