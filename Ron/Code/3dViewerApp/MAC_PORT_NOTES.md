# 3dViewerApp: handoff notes for Claude Code on the Mac

Read this first. It is the project memory from the Windows sessions (2026-10-10 to 2026-10-20).

## What this is
- `viewer3d.py` is a tkinter 3D scene editor built around the user's own OO 3D library, `class3d.py` with `overloaded_inc.py`. That library is their PY103 Python learning project.
- The scene lives in `scene3d.csv`: one object row, then its transform, group, pov, twin, csg and hollow rows. On save, `snapshot_rows()` collapses each object's steps.
- POV-Ray is the renderer. `pov_export.py` generates `pov/scene3d.pov` from the scene, so the viewer is the source of truth.
- `taichi_preview.py` is a separate GPU process (Taichi GGUI). It shows the scene live and is the port target: the user wants the whole UI moved into Taichi over time.
- The user plans to publish it for ray-tracing fans, since POV-Ray has no GUI on Mac or Linux. On Apple Silicon (Metal) it runs about 20× faster than on the user's PC.

## Files (all in `Ron/Code/3dViewerApp/`)
| file | role |
|---|---|
| `viewer3d.py` | main Tk app (App class), panels, tree, CSV load/save, undo, replicate/ring/align, preview link |
| `taichi_preview.py` | GGUI preview; talks to the viewer over stdout lines |
| `pov_export.py` | scene to .pov; Z-up to POV via `<x,z,y>`; materials, volumes, CSG, twin, hollow |
| `director3d.py` | camera director (F8): key poses, movie render, "Play in Taichi" |
| `lathe3d.py` | lathe profile tool (F7) |
| `solids3d.py` | hooks prism, pyramid, ellipsoid, polyhedra and caps into the viewer and POV |
| `ui_scroll.py` | scroll panels + `x11_wheel` shim (Button-4/5 → wheel) |
| `class3d.py`, `overloaded_inc.py`, `test3d_lib.py` | **user's library and learning code** |
| `pov/` | renders, textures (image maps must sit here), `_preview.npz`, `_preview.log`, `_preview_cam.json`, `director_shot.json` |

Backups go in `Ron/Code/backups/` as `<file>_before_<feature>.py`. Make one before every edit.

## Working rules (the user's preferences)
- Keep replies terse. No typo sweeps: answer only what was asked. Refer to the user as they/them.
- `class3d.py` and `mfind.py` are learning code. Describe fixes in words, no code, unless the user explicitly asks you to patch them. Don't add features they only brainstorm. `viewer3d.py` and the other tool files can be extended freely.
- Never touch the real `scene3d.csv` in tests. Copy it to a scratch directory.
- Don't commit or push without asking. Don't ask for a go-ahead on each port step; just keep going.
- Don't drive the real mouse or keyboard while the user's viewer or browser is open. Test headless instead.
- The user values both live drag and typed "old-style engineering" precision. Keep both paths for every tool.
- The user designs their own scenes, often at huge scale (coordinates around ±12000 to 36000; "Rescale world" exists for that).

## Library quirks the viewer works around (don't fix unless asked)
- `Sphere3d` has no `_points`, so move and rotate on it would crash. The viewer handles spheres itself.
- `OpOverloaded.__init__` is never called, so all points compare equal and are falsy. Use `is` or `id()`.
- `MINRAD=0.17` mismatch: flagged, not changed. `get_perpendicular_vectors` uses `get_end()` only, which is wrong when start ≠ origin (affects Plane3d): flagged.
- `TruncatedCone3d` subclasses `Cylinder3d`, so `solids3d` must intercept before `is_round`.
- `scene3d.csv` around line 2705 once had `cylinder1_4` with 6 numbers (missing height). The user was told; it was not edited.

## Taichi 1.7.4 GGUI quirks
- Widgets available: `sub_window`, `button` and `checkbox` only.
- **Number keys are never reported.** Use letters (M/T/B tools, G snap, F fly, R reset, P play, Tab menu). `ti.ui.RETURN == 'Return'`.
- The GGUI cursor y is up (0 = bottom).
- Don't use `Camera.track_user_inputs`: it multiplies moves by frame time ×60 and is Y-up, so a slow frame flings the view. Use `walk_look()` instead (dt capped at 0.05, Z-up).
- The ImGui assert "Mismatching io.KeyCtrl vs KeyMods" (exit 3) happens on window switches. The viewer auto-reopens the preview with `--resume`, restoring camera and menu state from `pov/_preview_cam.json`.
- Off-screen tests use `ti.ui.Window(..., show_window=False)`. Its `show()` access-violates on Windows, so stub it with `win.get_image_buffer_as_numpy()`. Call `save_image` before `show`.

## Preview ↔ viewer protocol
- The viewer writes `pov/_preview.npz` (atomic) on every save. The preview reloads it.
- The preview prints lines to stdout:
  - `PICK <iid> set|add`
  - `XF <iid> move dx dy dz | xrot/yrot/zrot deg | scale f`
  - `KEY undo|redo|delete`
  - `CMD <name> [args]`
- The viewer reads these on a thread into a queue and handles them in `_preview_picks` / `_preview_cmd`.
- Anything that needs typing pops a Tk `_ask` box, raised via `_to_front`. A field can be `(label, var)`, `(label, var, choices)` or `(label, [x, y, z vars])`.
- The preview's stderr goes to `pov/_preview.log`. `[click]` and `[release]` lines there help debug user reports.
- While the preview is open, the Tk 3D view is paused (`tk_paused`). The "Draw here too" checkbox re-enables it.
- The npz carries `moves_done` and tickets. The preview draws pending offsets until the viewer acks them.

## Feature history (all done and tested)
- **Primitives and views:**
  - circle, cylinder and cone family;
  - curved tubes (bends, chains, CurvedTorus);
  - Properties editor (double-click; Apply bakes transforms into the numbers);
  - planes with image maps.
- **POV and director:**
  - POV export: materials and include library, volumes (nebula, dust, smoke, star light, prism glass).
  - Director (camera paths, movies, GIF output).
  - Lathe tool.
  - All extra solids.
- **Scene editing:**
  - Groups (nested `group,a/b` paths) and "whole group" mode.
  - Twin (`twin,` row), CSG (`csg,<combine|cut|overlap>,<target|@group>`) and Hollow (`hollow,` row).
  - Align, Replicate, and Rescale world.
  - Snapshot save.
  - Global undo/redo (in memory, max 200).
- **Taichi preview** (F10):
  - Play the director path.
  - Click-select and drag-move (Ctrl drags along z).
  - M/T/B rotate/scale tools and G snap.
  - Menu sub-window with Tools / Edit / Add / View / Windows / Objects.
  - Orbit, pan and fly navigation.
  - Crash auto-reopen.
- **Big-scene speedups:** caches, deep-copy replicate; 402 objects: replicate 3.2 s, undo 3.2 s.
- **2026-10-19/20:**
  - View-jump fix (`walk_look`).
  - Typed Move / Center / Rotate / Scale boxes and Properties (Enter key) in the preview menu.
  - **Ring copy**: copies spread around a pivot from a start angle to an end angle. A full 360° drops the end point, and the 0° copy is skipped because the original is there. It takes an optional step (spiral) and a "size each copy ×" (fountain rings shrinking as they rise). Replicate got the same size option.
  - Shared copier: `_make_copies(src, ids, per_copy_tfs, sizes)`.
  - **Selected section** at the top of the preview menu. Its title shows the picked name (+N). Buttons open Tk `_ask` boxes for Properties, Rename, Colors (with `...` color pickers), Material (the name list follows the group), Twin, CSG, Hollow and Align. `_ask` now takes BooleanVar → checkbox, `ASK_COLOR`, and callable choices (follow combos). A right-drag that starts on the menu or HUD no longer looks around.
- **Next: Layers.** Each object gets a layer, saved in the CSV, with show/hide per layer in both windows.

## Testing pattern (headless; reuse it)
```
copy scene3d.csv to a scratch dir
import viewer3d as V; V.SCENE_FILE / V.POV_DIR / V.POV_FILE = scratch paths
V.App._to_front = staticmethod(lambda w: w.withdraw() if isinstance(w, tk.Toplevel) else None)
root = tk.Tk(); root.withdraw(); app = V.App(root)
settle(): loop root.update() until app.job_running has been False ~20 ticks
drive app methods / feed lines into app._ti_picks / call app._preview_cmd(...)
compare copies vs a fresh rebuild (V.sample_points), reload with V.load_scene
log to a file; end with os._exit(0)
```
On Windows these tests were run with `t_ring.py`, `t_typed.py`, `t_props.py`, `t_big2.py`, `t_undo.py`, `t_tixf.py`, `t_menu.py` and `t_walk.py`. They lived in a scratchpad that won't be on the Mac, so rebuild them from this pattern as needed.

## Mac setup (already working as of 2026-10-18)
- Use python.org **Python 3.12** with Tk. 3.13+ has no taichi wheels.
- Install the packages:
  ```bash
  python3.12 -m pip install taichi numpy pillow
  ```
- Install POV-Ray:
  ```bash
  brew install povray
  ```
  On the Mac, `pov_export` / `director3d` call `povray` directly; Windows goes through `wsl povray`. `LIB_DIRS` already include the Homebrew and Linux include paths.
- Run it:
  ```bash
  cd Ron/Code/3dViewerApp && python3.12 viewer3d.py
  ```
- `viewer3d._taichi_python` honours the `TAICHI_PYTHON` env var, then `sys.executable`, then `python3.12` / `python3`.
- `ti.init(arch=ti.gpu)` picks Metal on Apple Silicon.

## Mac things to check or polish
- The POV GUI button uses the Windows `PVENGINE` path. Hide it, or make it open the render image on the Mac.
- No middle mouse button: Ctrl+LMB pans in the preview. Right-click is a two-finger click, and is already handled in viewer3d's `_mac` block.
- Tk trackpad wheel deltas on macOS are small (±1..±10, not ±120). Check that zoom speed feels right.
- Cmd vs Ctrl: undo, redo and select-all are bound to Ctrl. Add Command bindings on the Mac.
- `_to_front` focus: confirm the `_ask` boxes come up above the Taichi window.
- Retina / HiDPI: check GGUI window size and pick accuracy.
- Cross-process file writes: the npz is written atomically via rename. That's fine on APFS.

## Release checklist (when the user says go)
- **Own new repo.** Do NOT publish from `Trading_Bot_V2`: it holds trading code, keys and history. Copy only the 3dViewerApp files.
- Licence is the user's choice (MIT suggested). POV-Ray (AGPL) runs as a separate program, which is OK. Taichi is Apache-2.0, numpy BSD, Pillow HPND.
- `requirements.txt`, a README with renders and GIFs, sample scenes (not the user's private ones), and a keys cheat-sheet.
- Test on Linux too (WSL or a VM).
- First-run polish:
  - check whether POV-Ray is installed;
  - show viewer messages in the Taichi HUD;
  - give a friendly error if taichi is missing;
  - make the ImGui crash rarer.
- Decide what to do with `class3d.py`: it is the user's own library and ships as part of the app.

## Open ideas (not started)
- Cache the `preview_mesh` solids mesh and bend `radial_dir`. They take about 2 s per update on big scenes.
- Show viewer status messages in the Taichi HUD.
- Hollow for tubes and caps. CSG preview shading (cut parts are only dashed in Tk and not shown in Taichi).
- User's long-term dream: write their own ray, camera, light and texture classes. Keep the exporter swappable.
