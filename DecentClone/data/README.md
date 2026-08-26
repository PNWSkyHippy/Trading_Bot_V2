# Astral Drift map data folder

Browser saves are **origin-scoped**:

- `file:///.../index.html` — one storage bucket
- `http://localhost:8127/` — a different bucket (this is `start_astral.bat`)
- A live hosted URL — a third bucket

They do not share maps automatically.

## Gullet Maze 1 (shareable hard copy)

The Gullet arcade maze is a generated station map. Each origin needs its own copy.

1. On the machine that built it, press **Alt+Shift+P** (or Ctrl+Shift+L → **Export Gullet Maze**).
2. That downloads `gullet-maze-library.json` (library backup) and `gullet-maze-1.json` (single map).
3. On localhost or the live server: Ctrl+Shift+L → **Import Library Backup** → pick `gullet-maze-library.json`.
4. Load **Gullet Maze 1** from the library list. Do not rely on Alt+P alone if you need the same rooms on another origin.

Repo copy for `start_astral.bat` auto-merge when the named map is missing:

- `data/gullet-maze-library.json`

## Move other maps to localhost

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
| `gullet-maze-library.json` | Gullet Maze 1 (merged in even if other maps already exist, unless that named map is already saved) |
| `tunnel_autosave.json` | Autosave only (single map JSON) |

Use **Export Library Backup** or **Export Gullet Maze** in-game to generate valid bundle files.
