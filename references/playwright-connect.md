# Playwright Browser Connection

Use this reference when connecting to a user's already-authenticated Chrome session for Tistory posting.

## Source Of Truth

- Playwright Agent CLI docs: `https://playwright.dev/agent-cli/cli-command`
- Playwright MCP configuration docs: `https://playwright.dev/mcp/configuration/browser-extension`

## Preferred Path (Chrome 136+/148 — verified 2026-06-06)

CDP attach to the user's already-running Chrome preserves the Tistory login AND allows cover-image upload (extension attach could not do both). But on Chrome 136+/148 the naive `--cdp=chrome` and the `chrome://inspect` toggle-only approach FAIL (mechanism in the Notes below). Do NOT relearn that failure every run: use this deterministic procedure.

The global `playwright-cli` (e.g. v0.1.0) has NO `attach` subcommand and launches its own login-less browser — always use `npx @playwright/cli@latest`.

1. (Re)launch the user's main Chrome WITH the debug flags. This quits their browser, so confirm or have them run it via `!`; the same default profile keeps the Tistory login (cookies on disk):

```bash
osascript -e 'quit app "Google Chrome"'; sleep 3
open -na "Google Chrome" --args --remote-debugging-port=9222 "--remote-allow-origins=*"
# quote the * or zsh globs it -> "no matches found"
```

   The DEFAULT profile is GATED: the flag alone does NOT open the port. After relaunch you must ALSO turn ON `chrome://inspect` → "Allow remote debugging for this browser instance" and wait until it reads `Server running at: 127.0.0.1:9222` (while it shows `starting…`, 9222 is not up and attach will keep timing out). So the login-preserving path needs BOTH the flag (relaunch) and the toggle. If the toggle dance is too fragile, prefer the dedicated debug profile (FIX B below) on a FREE port (e.g. 9333): a non-default `--user-data-dir` is NOT gated, so the flag alone opens the port with no toggle — at the cost of a one-time Tistory login in that profile. (Verified 2026-06-06: main-profile relaunch needed flag+toggle and several rounds; the 9333 dedicated profile came up instantly with just the flag.)

2. Attach with the EXPLICIT GUID WS read from DevToolsActivePort (NOT `--cdp=chrome`, NOT `/json`):

```bash
cd /tmp/tistory   # session state lives in ./.playwright-cli — keep one cwd
WS="ws://127.0.0.1:9222$(sed -n '2p' "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort")"
env npm_config_cache=/private/tmp/npm-cache \
  npx -y @playwright/cli@latest attach --cdp="$WS" --session=tistory-cdp
npx -y @playwright/cli@latest -s=tistory-cdp tab-list   # verify before interacting
```

Notes:
- Why `--cdp=chrome` / toggle-only fail: the port opens and the WS upgrades, but Chrome 111+ sends NO CDP data unless launched with `--remote-allow-origins=*`, so attach dies with `Timeout 30000ms exceeded`. The toggle opens the port; it does NOT add the origin allowlist. Relaunching with the flag is the fix. `--cdp=chrome` also resolves to the bare `/devtools/browser` path (no GUID) → `403`/timeout. A listening 9222 alone does NOT mean attach will work.
- `attach` exits with code 0 immediately; the session persists on disk under `.playwright-cli/` in the cwd. It did not fail or hang — do not retry it as if it crashed.
- Every later command must run from the SAME cwd and the same `-s=tistory-cdp` session.
- `/json/version` returns empty/404 on modern Chrome even when the port works — build the WS from line 2 of `DevToolsActivePort` (the GUID path), never from `/json`.
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
