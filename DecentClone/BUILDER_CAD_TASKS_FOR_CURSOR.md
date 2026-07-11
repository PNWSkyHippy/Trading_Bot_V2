# Astral Drift Builder CAD Tasks

Use `index.html` as the current source of truth. Preserve the existing flight/render path and avoid rewrites.

## Already Done

- Tunnel range selection exists: click segment A, `Alt+Shift+LMB` segment B, then `V` applies one texture/rib color to all selected tunnel segments.
- Selected tunnel ranges can be deleted with `Del`.
- Selected connected tunnel ranges can be reshaped/refit with a middle C bend and the XYZ gizmo, but obsolete artifact tunnel pieces are still left behind.
- Target box multi-select exists: `Shift+LMB` target boxes, click one selected target to edit all, `Del` deletes selected target boxes.
- Free orbit anchor exists: `Alt+Shift+LMB` empty space on the active plane sets a yellow ORBIT anchor, then `Alt+drag` or middle-drag can orbit around it.
- Multi-segment draft route mode exists: `N` starts a route, each segment has a C handle, `U` undoes route steps, and `Y` generates the route in chunked tunnel segments.
- Route points default to the active XY/YZ/ZX plane and can be pulled off-plane with the XYZ gizmo.
- Route C handles have editable numeric angles.
- The XYZ transform gizmo works on route nodes/handles, join points, portal endpoints, target boxes, sentries, and selected tunnel-range bends.
- `Alt+N` generates editable corkscrew/helix N-routes with fractional turns, taper, variable pitch, direction/axis controls, optional reverse helix, and compatible fit-to-B behavior.

## Build Next

### 1. Existing Tunnel Range Operations

Expand current range selection:

- Fix ABC/middle-C range refitting so it removes the old path completely and leaves no duplicate, disconnected, or overlapping artifact tunnel pieces.
- Later: copy/cut/move/resize selected connected run.

### 2. Target Batch Operations

Expand current target batch selection:

- Batch set explosive red/normal blue already works via target edit dialog.
- Add optional batch labels with prefix + sequence number.
- Add batch texture/sprite when target texture assets are added.

## Safety Rules

- Do not remove `applyMapGeometryChange()`.
- After geometry edits, call:
  - `syncBuilderTargetsFromGeometry()` when tunnel geometry changes.
  - `rebuildTunnelStars()`.
  - `rebuildTunnelTargets()`.
  - `invalidateTunnelSegmentCache()`.
  - `saveTunnelMap()`.
- Keep map save format backward-compatible.
- Run the script parse check after edits:

```powershell
$p = "Ron\Coding Projects\DecentClone\index.html"
$html = Get-Content $p -Raw
$m = [regex]::Match($html, '(?s)<script>(.*)</script>')
$scriptPath = Join-Path $env:TEMP 'astral_index_inner_script.js'
Set-Content -Path $scriptPath -Value $m.Groups[1].Value
$checkPath = Join-Path $env:TEMP 'astral_index_script_check.js'
Set-Content -Path $checkPath -Value "const fs=require('fs'); new Function(fs.readFileSync(process.argv[2], 'utf8')); console.log('script parse OK');"
node $checkPath $scriptPath
```
