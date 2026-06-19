# Playwright Browser Connection

Use this reference when connecting to a user's already-authenticated Chrome session for Tistory posting.

## Source Of Truth

- Playwright Agent CLI docs: `https://playwright.dev/agent-cli/cli-command`
- Playwright MCP configuration docs: `https://playwright.dev/mcp/configuration/browser-extension`

## Preferred Path (Chrome 136+/148 — verified 2026-06-06)

CDP attach to the user's already-running Chrome preserves the Tistory login AND allows cover-image upload (extension attach could not do both). But on Chrome 136+/148 the naive `--cdp=chrome` and the `chrome://inspect` toggle-only approach FAIL — see "Chrome 136+/148 default-profile breakage" below for the mechanism. Do NOT relearn that failure every run: use this deterministic procedure.

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

## Chrome 136+/148 default-profile breakage (verified 2026-06-03)

**FIRST RESPONSE WHEN ATTACH FAILS — PROMPT THE USER.** Before any WS-URL debugging, ask the user to open `chrome://inspect/#remote-debugging` in their Chrome and turn ON "Allow remote debugging for this browser instance". Tell them to wait until that page shows `Server running at: 127.0.0.1:9222` — while it still reads `Server running at: starting…` the CDP endpoint is not up yet and attach will keep failing. Only after it shows the running address should you (re)attach. This is a USER action; never bypass it. Once the toggle is on, `~/Library/Application Support/Google/Chrome/DevToolsActivePort` line 2 holds the GUID path (e.g. `/devtools/browser/<guid>`) used to build the explicit endpoint above. Note: the toggle opens the port but does NOT add `--remote-allow-origins=*`; if attach still times out after the server is running, Chrome must be relaunched with that flag (FIX A below).

`attach --cdp=chrome` stopped working overnight after Chrome auto-updated to 148. Symptom chain and the fix that actually worked in a live 10-post run:

What you see:
- `attach --cdp=chrome` resolves (via the default profile's `DevToolsActivePort`) to the BARE path `ws://localhost:9222/devtools/browser` (no GUID) and fails:
  - toggle OFF → `403 Forbidden` / `Connection rejected` / "Could not connect to chrome".
  - toggle ON but missing origin flag → `<ws connecting> ...` then `Timeout 30000ms exceeded` (the WS upgrades but no CDP data ever flows).
- `curl -s http://127.0.0.1:9222/json/version` returns `404` on the default profile. This is NORMAL on modern Chrome (HTTP discovery is disabled); it is not the root cause — rely on the WS endpoint, not `/json`.

Three root causes stack up:
1. Chrome 136+ gates remote debugging on the DEFAULT `user-data-dir`. Enable `chrome://inspect/#remote-debugging` → "Allow remote debugging for this browser instance" (it shows `Server running at: 127.0.0.1:9222`). This is a USER action — ask for it, never bypass.
2. Chrome 111+ accepts the CDP WebSocket upgrade but sends no protocol data unless Chrome was launched with `--remote-allow-origins=*` → looks like a hang/timeout, not a 403.
3. `--cdp=chrome` connects to the bare `/devtools/browser`; modern Chrome wants the exact GUID path. Pass the EXPLICIT ws URL instead.

FIX A — preserve the user's Tistory login (what worked here). On the user's MAIN Chrome: enable the toggle (1), make sure it runs with `--remote-debugging-port=9222 --remote-allow-origins=*` (relaunch if it lacks the origin flag), then attach with the explicit endpoint read from `/json/version` (or built from `DevToolsActivePort`):

```bash
cd /tmp
WS=$(curl -s -m5 http://127.0.0.1:9222/json/version | sed -n 's/.*"webSocketDebuggerUrl": *"\([^"]*\)".*/\1/p')
# if /json/version is 404, build it from line 2 of DevToolsActivePort:
[ -z "$WS" ] && WS="ws://127.0.0.1:9222$(sed -n '2p' "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort")"
npx -y @playwright/cli@latest attach --cdp="$WS" --session=main9222   # rc=0 = attached
npx -y @playwright/cli@latest -s=main9222 tab-list
```

FIX B — dedicated debug profile (deterministic, version-proof, but a FRESH profile is NOT logged into Tistory → user must log in once). Launch on a FREE port (9222 is usually held by the broken default instance) via `open -na` so launchd owns it:

```bash
open -na "Google Chrome" --args \
  --remote-debugging-port=9333 "--remote-allow-origins=*" \
  --user-data-dir="$HOME/.chrome-tistory-debug" --no-first-run \
  https://memoryhub.tistory.com/
WS=$(curl -s -m5 http://127.0.0.1:9333/json/version | sed -n 's/.*"webSocketDebuggerUrl": *"\([^"]*\)".*/\1/p')
npx -y @playwright/cli@latest attach --cdp="$WS" --session=tcdp
```

Gotchas that cost time here, so you do not repeat them:
- Quote `--remote-allow-origins=*` (single arg) or zsh globs the `*` → `no matches found`.
- The agent's sandboxed Bash REAPS background children when the call returns: a Chrome started with `nohup ... &`/`&` dies before the next command. Use `open -na` (launchd-owned) for Chrome; run long codex/posting batches as ONE background task that `wait`s on its children.
- Open a NEW tab (`tab-new <url>`) for posting work instead of `goto` on the user's active tab, so you do not navigate away from what they have open.
- Read the live category list once from the publish dialog (`완료` → open the `카테고리 선택` combobox → `getByRole('option').allTextContents()`); the `/manage/category` tree renders names lazily and snapshots come back empty.

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
