#!/usr/bin/env python3
"""Drive Tistory drafting from a prepared package with Playwright CLI."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path


def load_package(path: Path, allow_non_korean: bool) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = data.get("korean_check", {})
    if not allow_non_korean and checks != {"title": True, "body": True}:
        raise SystemExit("package Korean checks failed; translate first or pass --allow-non-korean")
    for key in ("title", "body_markdown", "cover_image"):
        if not data.get(key):
            raise SystemExit(f"package missing required key: {key}")
    return data


def cli_base(args: argparse.Namespace) -> list[str]:
    return shlex.split(args.cli)


def command(args: argparse.Namespace, *parts: str, session: bool = True) -> list[str]:
    base = cli_base(args)
    if session:
        base.append(f"-s={args.session}")
    return [*base, *parts]


def cover_file(package: dict[str, object]) -> Path | str:
    package_path = Path(str(package.get("body_markdown", "."))).parent
    for name in ("cover.codex.png", "cover.codex.jpg", "cover.codex.jpeg", "cover.codex.webp"):
        candidate = package_path / name
        if candidate.exists():
            return candidate
    return package.get("cover_png") or package["cover_image"]


def attach_command(args: argparse.Namespace) -> list[str] | None:
    if args.attach == "none":
        return None
    if args.attach == "extension":
        value = "--extension" if not args.extension_channel else f"--extension={args.extension_channel}"
    elif args.attach == "cdp":
        value = f"--cdp={args.cdp_endpoint}"
    else:
        raise SystemExit(f"unsupported attach mode: {args.attach}")
    return [*cli_base(args), "attach", value, f"--session={args.session}"]


def run(args: argparse.Namespace, cmd: list[str], allow_error: bool = False) -> str:
    """Run a CLI command, capturing output.

    The Playwright CLI prints `### Error ...` to stdout while still exiting 0,
    so a clean returncode is not enough to prove success. Treat any `### Error`
    line (or nonzero exit) as failure unless allow_error is set (e.g. for a
    tolerant dialog-dismiss when no modal is pending).
    """
    printable = shlex.join(cmd)
    print(f"$ {printable}")
    if args.dry_run:
        return ""
    env = os.environ.copy()
    if args.npm_cache:
        env["npm_config_cache"] = args.npm_cache
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if out:
        print(out)
    if not allow_error and proc.returncode != 0:
        raise SystemExit(f"command failed (rc={proc.returncode}): {printable}")
    if not allow_error and "### Error" in out:
        raise SystemExit(f"command reported an error: {printable}")
    return out


def fill_if(args: argparse.Namespace, target: str | None, value: str) -> None:
    if target:
        run(args, command(args, "fill", target, value))


def click_if(args: argparse.Namespace, target: str | None) -> None:
    if target:
        run(args, command(args, "click", target))


READABILITY_STYLES = {
    "p": "margin: 0 0 1.15em; line-height: 1.85;",
    "h2": "margin: 2.2em 0 0.85em; line-height: 1.35;",
    "h3": "margin: 1.8em 0 0.7em; line-height: 1.4;",
    "ul": "margin: 0 0 1.35em 1.25em; line-height: 1.8;",
    "ol": "margin: 0 0 1.35em 1.25em; line-height: 1.8;",
    "li": "margin: 0.3em 0;",
    "pre": "margin: 1.4em 0; padding: 1em; line-height: 1.55; overflow-x: auto;",
    "table": "margin: 1.5em 0; border-collapse: collapse; line-height: 1.65;",
    "blockquote": "margin: 1.5em 0; padding-left: 1em; border-left: 4px solid #CBD5E1;",
}


def add_style(html_text: str, tag: str, style: str) -> str:
    return re.sub(rf"<{tag}(\s[^>]*)?>", lambda match: style_opening_tag(tag, match.group(1), style), html_text)


def style_opening_tag(tag: str, attrs: str | None, style: str) -> str:
    attrs = attrs or ""
    if "style=" in attrs:
        return f"<{tag}{attrs}>"
    return f'<{tag}{attrs} style="{style}">'


def apply_readability_spacing(html_text: str) -> str:
    for tag, style in READABILITY_STYLES.items():
        html_text = add_style(html_text, tag, style)
    return html_text.replace("<hr />", '<hr style="margin: 2em 0; border: 0; border-top: 1px solid #E5E7EB;" />')


def demote_headings(html_text: str) -> str:
    """Shift body headings down one level (h1->h2 ... h5->h6).

    The Korean writing standard uses `#` for top sections, but the Tistory
    title field already carries the page H1. Demoting keeps a single H1 per
    page and a cleaner SEO heading hierarchy. Process high-to-low so a heading
    is not demoted twice.
    """
    for level in (5, 4, 3, 2, 1):
        html_text = (
            html_text
            .replace(f"<h{level}>", f"<h{level + 1}>")
            .replace(f"<h{level} ", f"<h{level + 1} ")
            .replace(f"</h{level}>", f"</h{level + 1}>")
        )
    return html_text


def render_body_html(markdown_path: Path) -> str:
    source = markdown_path.read_text(encoding="utf-8")
    try:
        import markdown as markdown_lib
    except ImportError:
        return apply_readability_spacing(f"<pre>{html.escape(source)}</pre>")
    rendered = markdown_lib.markdown(source, extensions=["extra", "sane_lists", "nl2br"])
    return apply_readability_spacing(demote_headings(rendered))


def tinymce_script_path(args: argparse.Namespace) -> Path:
    if args.tinymce_script:
        return args.tinymce_script
    return args.package.parent / "tistory-tinymce-body.js"


def publish_script_path(args: argparse.Namespace) -> Path:
    if args.publish_script:
        return args.publish_script
    return args.package.parent / "tistory-private-publish-finish.js"


def publish_start_script_path(args: argparse.Namespace) -> Path:
    return args.package.parent / "tistory-private-publish-start.js"


def current_cover_start_script_path(args: argparse.Namespace) -> Path:
    return args.package.parent / "tistory-current-cover-start.js"


def write_tinymce_script(args: argparse.Namespace, package: dict[str, object]) -> Path:
    body_html = render_body_html(Path(str(package["body_markdown"])))
    payload = json.dumps({"bodyHtml": body_html}, ensure_ascii=False)
    script = f"""page => page.evaluate(payload => {{
  const tinymce = window.tinymce;
  const editor = tinymce && (tinymce.activeEditor || tinymce.editors[0]);
  if (!editor) throw new Error("Tistory TinyMCE editor is not available");
  const wrapper = document.createElement("div");
  wrapper.innerHTML = editor.getContent();
  wrapper.querySelectorAll('section[data-codex-tistory-body="true"]').forEach(node => node.remove());
  const preserved = wrapper.innerHTML.trim();
  const body = `<section data-codex-tistory-body="true" style="line-height: 1.85; word-break: keep-all;">${{payload.bodyHtml}}</section>`;
  const next = [preserved, body].filter(Boolean).join("<p></p>");
  editor.setContent(next);
  editor.undoManager.add();
  editor.setDirty(true);
  editor.save();
  editor.fire("change");
  editor.fire("input");
  const output = editor.getContent();
  return {{
    hasCover: /<img\\b|##_Image/i.test(output) || /<img\\b/i.test(editor.getBody().innerHTML),
    textLength: editor.getContent({{ format: "text" }}).length,
    preview: editor.getContent({{ format: "text" }}).slice(0, 120)
  }};
}}, {payload})
"""
    path = tinymce_script_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return path


def package_payload(args: argparse.Namespace, package: dict[str, object]) -> str:
    payload = {
        "targetUrl": args.target_url,
        "title": str(package["title"]),
        "bodyHtml": render_body_html(Path(str(package["body_markdown"]))),
        "tags": [str(item) for item in package.get("tags", [])],
        "cover": str(cover_file(package)),
    }
    return json.dumps(payload, ensure_ascii=False)


def write_private_publish_script(args: argparse.Namespace, package: dict[str, object]) -> Path:
    payload = package_payload(args, package)
    script = f"""page => (async () => {{
  const payload = {payload};
  await page.waitForFunction(() => /<img\\b|##_Image/i.test(window.tinymce?.activeEditor?.getContent() || "") || /<img\\b/i.test(window.tinymce?.activeEditor?.getBody()?.innerHTML || ""));
  const result = await page.evaluate(data => {{
    const editor = window.tinymce.activeEditor || window.tinymce.editors[0];
    const cover = editor.getContent().trim();
    const body = `<section data-codex-tistory-body="true" style="line-height: 1.85; word-break: keep-all;">${{data.bodyHtml}}</section>`;
    editor.setContent([cover, body].filter(Boolean).join("<p></p>"));
    editor.save();
    editor.fire("change");
    return {{ hasCover: /<img\\b|##_Image/i.test(editor.getContent()), chars: editor.getContent({{ format: "text" }}).length }};
  }}, payload);
  const tagInput = page.getByRole("textbox", {{ name: "태그" }}).last();
  for (const tag of payload.tags) {{
    await tagInput.fill(tag);
    await page.keyboard.press("Enter");
  }}
  await page.getByRole("button", {{ name: "완료" }}).click();
  await page.getByRole("radio", {{ name: "비공개" }}).click();
  await page.getByRole("button", {{ name: "비공개 저장" }}).click();
  await page.waitForURL(/\\/manage\\/posts\\/?/, {{ timeout: 60000 }});
  return {{ title: payload.title, url: page.url(), tags: payload.tags.length, ...result }};
}})()
"""
    path = publish_script_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return path


def write_private_publish_start_script(args: argparse.Namespace, package: dict[str, object]) -> Path:
    payload = json.dumps({"title": str(package["title"])}, ensure_ascii=False)
    script = f"""page => (async () => {{
  page.once("dialog", async dialog => {{
    const msg = dialog.message();
    try {{
      return msg.includes("이어서 작성") ? await dialog.dismiss() : await dialog.accept();
    }} catch (error) {{
      return null;
    }}
  }});
  await page.goto({json.dumps(args.target_url)});
  await page.waitForLoadState("domcontentloaded");
  const payload = {payload};
  await page.getByRole("textbox", {{ name: "제목을 입력하세요" }}).fill(payload.title);
  await page.getByRole("button", {{ name: "첨부" }}).click();
  await page.getByText("사진", {{ exact: true }}).first().click();
  return {{ title: payload.title, chooser: "open" }};
}})()
"""
    path = publish_start_script_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return path


def write_current_cover_start_script(args: argparse.Namespace, package: dict[str, object]) -> Path:
    payload = json.dumps({"title": str(package["title"])}, ensure_ascii=False)
    script = f"""page => (async () => {{
  const payload = {payload};
  await page.getByRole("textbox", {{ name: "제목을 입력하세요" }}).fill(payload.title);
  await page.evaluate(() => {{
    const editor = window.tinymce && (window.tinymce.activeEditor || window.tinymce.editors[0]);
    if (editor) {{
      editor.setContent("");
      editor.save();
      editor.fire("change");
    }}
  }});
  await page.getByRole("button", {{ name: "첨부" }}).click();
  await page.getByText("사진", {{ exact: true }}).first().click();
  return {{ title: payload.title, chooser: "open-current-page" }};
}})()
"""
    path = current_cover_start_script_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return path


def private_publish_start_nogoto_path(args: argparse.Namespace) -> Path:
    return args.package.parent / "tistory-private-publish-start-nogoto.js"


def write_private_publish_start_nogoto_script(args: argparse.Namespace, package: dict[str, object]) -> Path:
    """Start script that assumes the editor is already loaded and any restore
    dialog has been dismissed at the CLI level. Doing the goto + dialog handling
    as separate CLI steps avoids the `run_code does not handle the modal state`
    error that a confirm() dialog (autosaved-draft restore prompt) triggers."""
    payload = json.dumps({"title": str(package["title"])}, ensure_ascii=False)
    script = f"""page => (async () => {{
  const payload = {payload};
  await page.waitForLoadState("domcontentloaded");
  await page.getByRole("textbox", {{ name: "제목을 입력하세요" }}).fill(payload.title);
  await page.evaluate(() => {{
    const editor = window.tinymce && (window.tinymce.activeEditor || window.tinymce.editors[0]);
    if (editor) {{
      editor.setContent("");
      editor.save();
      editor.fire("change");
    }}
  }});
  await page.getByRole("button", {{ name: "첨부" }}).click();
  await page.getByText("사진", {{ exact: true }}).first().click();
  return {{ title: payload.title, chooser: "open-nogoto" }};
}})()
"""
    path = private_publish_start_nogoto_path(args)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(script, encoding="utf-8")
    return path


def execute(args: argparse.Namespace, package: dict[str, object]) -> None:
    attach = attach_command(args)
    if attach:
        run(args, attach)
    if args.private_publish or args.current_private_publish or args.finish_private_publish:
        if not args.confirm_private_publish:
            raise SystemExit("refusing private publish without --confirm-private-publish")
    if args.finish_private_publish:
        run(args, command(args, "run-code", "--filename", str(write_private_publish_script(args, package))))
        return
    if args.private_publish:
        cover = cover_file(package)
        # Navigate and clear the autosaved-draft restore confirm() at the CLI
        # level. Doing goto inside a run-code script collides with the CLI's
        # modal interception ("does not handle the modal state").
        run(args, command(args, "goto", args.target_url))
        run(args, command(args, "dialog-dismiss"), allow_error=True)
        run(args, command(args, "run-code", "--filename", str(write_private_publish_start_nogoto_script(args, package))))
        run(args, command(args, "upload", str(cover)))
        out = run(args, command(args, "run-code", "--filename", str(write_private_publish_script(args, package))))
        if not args.dry_run and '"hasCover":true' not in out:
            raise SystemExit("private publish did not confirm a cover image in the editor")
        return
    if args.current_private_publish:
        cover = cover_file(package)
        run(args, command(args, "run-code", "--filename", str(write_current_cover_start_script(args, package))))
        run(args, command(args, "upload", str(cover)))
        run(args, command(args, "run-code", "--filename", str(write_private_publish_script(args, package))))
        return
    if not args.skip_open:
        run(args, command(args, "goto", args.target_url))
    run(args, command(args, "snapshot"))
    fill_requested = any(
        [
            args.title_target,
            args.body_target,
            args.cover_button_target,
            args.tags_target,
            args.summary_target,
            args.tinymce_body,
        ]
    )
    if not fill_requested:
        return
    if args.cover_button_target:
        cover = cover_file(package)
        run(args, command(args, "click", args.cover_button_target))
        run(args, command(args, "upload", str(cover)))
    fill_if(args, args.title_target, str(package["title"]))
    if args.tinymce_body:
        run(args, command(args, "run-code", "--filename", str(write_tinymce_script(args, package))))
    else:
        fill_if(args, args.body_target, Path(str(package["body_markdown"])).read_text(encoding="utf-8"))
    fill_if(args, args.tags_target, ", ".join(str(item) for item in package.get("tags", [])))
    fill_if(args, args.summary_target, str(package.get("summary", "")))
    click_if(args, args.save_target)
    if args.publish_target:
        if not args.confirm_publish:
            raise SystemExit("refusing publish click without --confirm-publish")
        run(args, command(args, "click", args.publish_target))
    run(args, command(args, "screenshot", "--filename", args.screenshot))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Use Playwright CLI to open/fill a Tistory draft.")
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--cli", default="npx @playwright/cli@latest")
    parser.add_argument("--npm-cache", default="/private/tmp/npm-cache")
    parser.add_argument("--session", default="tistory")
    parser.add_argument("--attach", choices=["extension", "cdp", "none"], default="extension")
    parser.add_argument("--extension-channel", default="")
    parser.add_argument("--cdp-endpoint", default="chrome")
    parser.add_argument("--target-url", default="https://www.tistory.com/")
    parser.add_argument("--skip-open", action="store_true")
    parser.add_argument("--title-target")
    parser.add_argument("--body-target")
    parser.add_argument("--cover-button-target")
    parser.add_argument("--tags-target")
    parser.add_argument("--summary-target")
    parser.add_argument("--tinymce-body", action="store_true")
    parser.add_argument("--tinymce-script", type=Path)
    parser.add_argument("--private-publish", action="store_true")
    parser.add_argument("--current-private-publish", action="store_true")
    parser.add_argument("--finish-private-publish", action="store_true")
    parser.add_argument("--confirm-private-publish", action="store_true")
    parser.add_argument("--publish-script", type=Path)
    parser.add_argument("--save-target")
    parser.add_argument("--publish-target")
    parser.add_argument("--confirm-publish", action="store_true")
    parser.add_argument("--allow-non-korean", action="store_true")
    parser.add_argument("--screenshot", default=".playwright-cli/tistory-draft.png")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    package = load_package(args.package, args.allow_non_korean)
    execute(args, package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
