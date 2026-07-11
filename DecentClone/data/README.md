# Astral Drift map data folder

Browser saves are **origin-scoped**:

- `file:///.../index.html` — one storage bucket
- `http://localhost:8126/` — a different bucket

They do not share maps automatically.

## Move maps to localhost (recommended)

1. Open the game the way you originally saved (usually double-click `index.html`).
2. Press **Ctrl+Shift+L** to open the map library, then choose **Export Library Backup**.
3. Save the downloaded `astral-drift-maps-YYYY-MM-DD.json`.
4. Either:
   - **Import:** run `start_astral.bat`, press **Ctrl+Shift+L** → **Import Library Backup**, pick the JSON file, or
   - **Auto-load:** copy/rename that file to `data/map_library_bundle.json` in this folder, then restart via `start_astral.bat`.

## Optional bootstrap files

When running via `start_astral.bat`, Astral Drift auto-loads these if local storage is empty:

| File | Purpose |
|------|---------|
| `map_library_bundle.json` | Full backup (library + named maps + optional autosave) |
| `map_library.json` | Same format as bundle (alias) |
| `tunnel_autosave.json` | Autosave only (single map JSON) |

Use **Export Library Backup** in-game to generate a valid bundle file.
