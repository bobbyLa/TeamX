# TeamX Obsidian Config Snapshot

This directory stores the reproducible subset of the shared vault's `.obsidian/` state.

Included:
- Root config files such as `app.json`, `appearance.json`, `community-plugins.json`, `core-plugins.json`, `hotkeys.json`, and `types.json`
- `snippets/` and `themes/`
- Per-plugin `data.json` files under `plugins/<plugin>/`

Excluded on purpose:
- `workspace.json`, `graph.json`, and other session/layout state
- Plugin binaries (`main.js`, `manifest.json`, `styles.css`)
- Cache-like or machine-local files

Refresh this snapshot with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-vault-config.ps1
```
