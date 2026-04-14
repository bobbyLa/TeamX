# Local Config Notes

This file documents local-only configuration conventions for TeamX.

## Secrets

- Do not store API keys or other secrets in `.claude/settings.local.json`.
- Put secrets in process environment variables or the repo-root `.env` file.
- Keep sample variable names in `.env.example` only; never place real values there.

## Gemini Vision

- `GEMINI_API_KEY` is loaded by `.claude/skills/gemini-vision/gemini_vision.py`.
- The script reads `GEMINI_API_KEY` from the current environment first, then falls back to the repo-root `.env`.
- If another local tool needs the same key, reuse that lookup pattern instead of embedding the key in JSON config.

## settings.local.json

- Treat `.claude/settings.local.json` as a local permissions/config file, not a secret store.
- Keep entries there limited to non-secret local allowlists and tool wiring.
