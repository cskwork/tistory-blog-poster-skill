# Playwright Browser Connection

Use an authorized connection to the user's existing Tistory session. Browser and driver capabilities change; local help, current tool documentation, and observed errors govern the connection path.

## Attach

1. Inspect the available browser connector/CLI and its help for supported attachment modes. Prefer an existing working session over installing another driver.
2. If using Playwright CLI, choose a task working directory and one session name; keep both consistent for later commands. Inspect the helper's `--dry-run` output to see its exact invocation.
3. Attach through the supported extension or an already authorized local CDP endpoint. Obtain the current endpoint from browser-provided discovery or its current `DevToolsActivePort` file when supported. A listening port or exit 0 is not enough: verify tab listing and a current snapshot.
4. Open a task tab for posting; do not navigate the user's unrelated active tab away. Verify the target blog and account before edits.

For current CLI details, consult [Playwright Agent CLI](https://playwright.dev/agent-cli/cli-command); for an available MCP extension, consult [Playwright MCP configuration](https://playwright.dev/mcp/configuration/browser-extension).

## Recover from failure

- Inspect the concrete error, driver version, session cwd/name, endpoint, and port ownership with read-only checks before asking the user to change settings.
- Ask the user to complete login, connection consent, or an unavailable extension/setup step only when that is the actual blocker. Never request credentials or export cookies/profiles as a workaround.
- A browser restart can disrupt unrelated work; perform it only when authorized. Do not automatically add a wildcard origin allowlist, alter the main profile, or assume historical Chrome-version workarounds are still necessary.
- A dedicated debug profile, when explicitly chosen, may need a fresh user login. Keep debugging local and use the supported least-privileged connection configuration.
- Keep the same CLI package version and npm cache across attachment and commands unless evidence requires a change. Cache changes can select another daemon/session.
- If extension-mode upload fails with `fileChooser.setFiles ... Not allowed`, the browser connection may still work. Use a permitted CDP route or manual chooser handoff; do not repeatedly upload or treat the article package as corrupt.

## Editor operation

Refresh snapshots after state changes and use current labels/roles. Keep `.playwright-cli/` state untracked. Read category labels from the live selector when needed. Restore-draft dialogs require preserving unrelated draft work before dismissing them; `goto` and dialog handling must finish before run-code.

Historical attach observations are troubleshooting clues, not guarantees about all Chrome versions or user accounts. Report the actual attempted route and blocker if attachment remains unavailable.
