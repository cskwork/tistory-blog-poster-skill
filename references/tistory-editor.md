# Tistory Editor Workflow

Use this reference after the browser connection is verified.

## Required Inputs

- Source article path, URL, or pasted content.
- Target blog, if known.
- Desired status: draft, private publish, scheduled, or public publish.
- Category and tags, if the user has preferences.

## Content Preparation

1. Translate to Korean first.
   - Preserve code blocks, links, product names, numbers, and source attributions.
   - Keep the tone aligned with this repo's `context/brand-voice.md` and `context/style-guide.md`.
   - Keep SEO intent from `context/seo-guidelines.md`.
   - Keep the body beginner-friendly: short paragraphs, first-use jargon definitions, and practical examples instead of long theory.

2. Prepare a posting package:
   - Korean title.
   - Korean body.
   - SEO summary/meta description.
   - Tags.
   - Category recommendation.
   - Cover image path.
   - Cover prompt path for a fresh Codex-generated image.
   - Prefer the generated `package.json` from `scripts/prepare_tistory_package.py` as the automation input.

3. Normalize body content for Tistory:
   - Remove Hugo front matter.
   - Remove duplicate H1 if the title field already contains it.
   - Convert internal Hugo-relative links to public URLs when the Tistory audience needs working links.
   - Keep code fenced or HTML-safe according to the active Tistory editor mode.

## Opening 글쓰기

- Start from `https://www.tistory.com/` if the blog admin URL is unknown.
- If the target host is known, direct routes may be faster, but validate the loaded page visually before acting.
- Expected labels may include `글쓰기`, `제목`, `본문`, `카테고리`, `태그`, `임시저장`, `미리보기`, `발행`, and `공개`.
- If Tistory shows login or account selection, stop and ask the user to complete it inside Chrome.

## Filling The Editor

1. Use a fresh snapshot to locate the title field.
2. Read the generated package, `cover_prompt`, and `body_markdown`.
3. Generate a fresh Codex image from `cover_prompt.md` for this post and save it as `cover.codex.png` or `cover.codex.jpg`.
   - The image must be topic and content specific. It should make concrete article concepts visible, such as mobile chip plus edge nodes for on-device LLMs, browser canvas plus GPU blocks for WebGPU posts, or local endpoint plus model server for API posts.
   - The final cover should be image-model quality: cinematic lighting, depth, material detail, strong focal object, and polished 1200x630 hero composition.
   - Reject a cover before upload if it looks like a reusable AI banner, generic gradient, random network, stock photo, simple flat diagram, or template with only the text changed.
   - Use the local bitmap/SVG scripts only as preview assets unless the user explicitly accepts fallback publishing.
4. Insert the Codex image before the first paragraph.
5. Fill the title and body.
6. Add category and tags.
7. Save draft, privately publish, or open preview according to the user's approved status.

If Codex image generation is unavailable, stop and report the blocker when the user required Codex Image 2.0. Do not silently upload fallback images.

For long bodies, avoid typing character by character. Use a paste/import path, or run a Playwright script against the currently focused editor only after confirming the active element is the Tistory body editor.

The helper `scripts/tistory_playwright_cli.py` can run the repeatable parts:

```bash
python3 .claude/skills/tistory-seo-blog-poster/scripts/tistory_playwright_cli.py \
  --package /tmp/tistory-post/package.json \
  --target-url https://www.tistory.com/ \
  --title-target <snapshot-ref> \
  --tinymce-body \
  --cover-button-target <snapshot-ref> \
  --tags-target <snapshot-ref> \
  --save-target <snapshot-ref>
```

Use `--skip-open --attach none` when the active editor already has uploaded media that should not be lost by reloading the new-post URL.

Tistory stores uploaded images in TinyMCE content as `[##_Image...]` placeholders while the visible iframe renders real `<img>` elements. Treat either form as valid cover evidence.

Do not pass `--publish-target` unless the user has explicitly approved public publishing; the helper refuses to click it without `--confirm-publish`. For SEO Machine final distribution, prefer `--private-publish --confirm-private-publish`.

Current live Tistory editor observations:

- Account menu write link: `쓰기` opened `https://memoryhub.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F`.
- Title field label: `제목을 입력하세요`.
- Body iframe textbox label: `글 내용 입력`.
- Attachment path: `첨부` -> `사진` opens a file chooser.
- Extension attach navigates correctly, but CDP attach may be required for file upload.
- Bottom controls include `미리보기`, `임시저장`, and `완료`.
- Restore-draft modal: opening newpost when an autosaved draft exists raises a `confirm()` ("저장된 글이 있습니다. 이어서 작성하시겠습니까?"). The CLI then reports `Tool "browser_run_code_unsafe" does not handle the modal state` and refuses run-code/upload. Handle it as separate CLI steps: `goto` the newpost URL, then `dialog-dismiss` (start fresh), THEN run the fill/upload scripts. Do not call goto inside a run-code script. `tistory_playwright_cli.py --private-publish` does this automatically; `dialog-dismiss` is tolerated when no modal is pending.
- Publish dialog after `완료`: choose the `비공개` radio, then click `비공개 저장`; the page redirects to `/manage/posts/` on success.

## Verification

Before declaring success:

- Screenshot or preview the draft.
- Confirm the title is Korean and visible.
- Confirm the cover image is at the top.
- Confirm the first two body sections match the prepared Korean package.
- Confirm links and code blocks survived insertion.
- Confirm status: draft, private, scheduled, or published.

## Publish Gate

- Draft/save is allowed when the user asked to prepare a post.
- Private publish is allowed when the user asked for SEO Machine final distribution or explicitly requested Tistory private publishing.
- Final public publish requires explicit approval in the current request.
- If approval is missing, stop at the preview or final confirmation screen and report what remains.
