# Playwright Browser Connection

Use this reference when connecting to a user's already-authenticated Chrome session for Tistory posting.

## Source Of Truth

- Playwright Agent CLI docs: `https://playwright.dev/agent-cli/cli-command`
- Playwright MCP configuration docs: `https://playwright.dev/mcp/configuration/browser-extension`

## Preferred Path (verified 2026-06-02)

For SEO Machine posting, prefer CDP attach to the user's already-running Chrome. In a live 10-post run it preserved the user's Tistory login AND allowed cover-image upload — the two things extension attach could not do together.

```bash
# The global `playwright-cli` (e.g. v0.1.0) has NO `attach` subcommand and
# launches its own browser (no login). Use the latest CLI via npx instead.
cd /tmp/tistory   # session state lives in ./.playwright-cli — keep one cwd
env npm_config_cache=/private/tmp/npm-cache \
  npx -y @playwright/cli@latest attach --cdp=chrome --session=tistory-cdp
```

Notes:
- `attach` exits with code 0 immediately; the session persists on disk under `.playwright-cli/` in the cwd. It did not fail or hang — do not retry it as if it crashed.
- Every later command must run from the SAME cwd and the same `-s=tistory-cdp` session, e.g. `npx -y @playwright/cli@latest -s=tistory-cdp tab-list`.
- `--cdp=chrome` attaches to the existing Chrome process; if the user is already logged into Tistory there, no re-login is needed.
- npx re-resolves the package (~5-10s) on every call. For long multi-post runs, consider a global install to cut cold-start, or batch steps into fewer `run-code` invocations.

## Decision Tree

1. Use the Agent CLI when available.
   - Check `playwright-cli --help`.
   - Check `playwright-cli attach --help` or the top-level command list for `attach`.
   - If no global binary exists or the global binary is too old, prefer `npx @playwright/cli@latest --help` rather than installing globally.
   - If npm cache permissions fail on this Mac, run npx with `npm_config_cache=/private/tmp/npm-cache`.
   - Attach with the browser extension:

```bash
playwright-cli attach --extension -s=tistory
npx @playwright/cli@latest attach --extension --session=tistory
```

2. Verify the session before touching Tistory.

```bash
playwright-cli -s=tistory tab-list
playwright-cli -s=tistory snapshot
```

3. Use CDP only when extension attach is unavailable and the user has Chrome running with remote debugging.

```bash
playwright-cli attach --cdp=chrome -s=tistory
playwright-cli attach --cdp=http://localhost:9222 -s=tistory
npx @playwright/cli@latest attach --cdp=chrome --session=tistory
```

4. Use MCP fallback when CLI control is not available in the current harness.

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--extension"]
    }
  }
}
```

For CDP fallback through MCP:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--cdp-endpoint=chrome"]
    }
  }
}
```

Use `--cdp-endpoint=http://localhost:9222` instead when Chrome was launched with a known remote-debugging port.

## Browser Extension Notes

- Browser-extension mode is for reusing a real, existing browser session.
- It is useful for Tistory because the user can stay logged in without sharing credentials.
- If the extension is missing or disabled, pause and ask the user to install/enable it in Chrome.
- Do not export cookies or profiles as a workaround.

## Automation Rules

- Use snapshots before every fragile interaction.
- Interact by current visible labels and roles, not stale refs from an older session.
- Keep the session scoped to Tistory plus the source article/image files needed for the post.
- If a command tries to create `.playwright-cli/` state, keep it untracked.
- Use `scripts/tistory_playwright_cli.py --dry-run` to inspect the exact CLI commands before running a fill or save operation.
- If `upload` returns `fileChooser.setFiles: ... Not allowed` under extension attach, the browser is connected but file upload is blocked by that transport. Retry through CDP or pause for a manual file chooser handoff.
- Live check on 2026-05-31: extension attach could navigate and open the editor, but PNG upload was blocked; `npx @playwright/cli@latest attach --cdp=chrome --session=tistory-cdp` then `upload /path/to/cover.png` succeeded.
