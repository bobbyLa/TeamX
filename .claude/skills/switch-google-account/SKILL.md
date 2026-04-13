---
name: switch-google-account
description: Switch the Chrome profile's active Google account. Use when the current MCP Chrome session is on the wrong Google account (e.g., bobby instead of vach). Navigates to the Google account picker, selects the target account, and waits for redirect back to the original site.
---

# Switch Google Account

Chrome-devtools MCP uses a dedicated `.chrome-profile/` Chrome instance. Switching accounts **must** happen inside this MCP-controlled browser — manual switching in a separate Chrome window has no effect on the MCP session.

## Inputs
- `target_email` (optional) — exact Gmail address of the account to switch to. If omitted, defaults to `vachdongpham41866@gmail.com` (Vach Pham, TeamX's NotebookLM account).
- `return_url` (optional) — URL to navigate back to after account switch. If omitted, stays at `notebooklm.google.com`.

## Preconditions
- Chrome is running with `--user-data-dir=<project>/.chrome-profile` (the MCP browser).
- The account you want to switch to already appears in the Google "Choose account" picker.

## Playbook

1. Navigate to `https://accounts.google.com/SignOutOptions?hl=en&continue=<encodeURIComponent(return_url || 'https://notebooklm.google.com/')>`.
   - This URL forces the account picker even when a session already exists.
2. `take_snapshot` — confirm the "Choose account" screen appears.
3. Find the button whose accessible name matches `target_email` exactly. Use `evaluate_script` if the snapshot labels are ambiguous:
   ```js
   () => {
     const btns = Array.from(document.querySelectorAll('button'));
     const match = btns.find(b => b.textContent.trim() === 'Vach Pham vachdongpham41866@gmail.com');
     return match ? match.outerHTML : null;
   }
   ```
4. `click` the matching account button. **Do NOT navigate manually** after clicking — wait for the page to redirect automatically.
5. `wait_for` the `return_url` (or `notebooklm.google.com`) to appear in `window.location.href`. Timeout 20s.
6. `take_snapshot` and confirm the top-right account label shows the expected email.

## Common account labels in this profile

| Display name | Email |
|---|---|
| Bobby Lau | `bobby991113@gmail.com` |
| Vach Pham | `vachdongpham41866@gmail.com` |

## Failure modes
- Account not listed in picker: click "Add account", complete sign-in flow, then restart the switch skill.
- Picker doesn't appear (already on the right account): exit silently with no action.
- Redirect times out: re-run the skill — the account switch usually still succeeded.

## Example usage

```
/switch-google-account target_email=vachdongpham41866@gmail.com
```
