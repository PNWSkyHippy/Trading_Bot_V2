# Astral Drift Builder CAD Tasks

Use `index.html` as the current source of truth. Preserve the existing flight/render path and avoid rewrites.

## Already Done

- Tunnel range selection exists: click segment A, `Alt+Shift+LMB` segment B, then `V` applies one texture/rib color to all selected tunnel segments.
- Target box multi-select exists: `Shift+LMB` target boxes, click one selected target to edit all, `Del` deletes selected target boxes.
- Free orbit anchor exists: `Alt+Shift+LMB` empty space on the active plane sets a yellow ORBIT anchor, then `Alt+drag` or middle-drag can orbit around it.

## Build Next

### 1. Multi-Segment Draft Route

Current builder only has A, B, and optional C midpoint for one join. Add a draft route mode:

- A route is an ordered list of nodes.
- Each segment is `node[i] -> node[i+1]`.
- Each segment owns its own C handle:
  - `handle.point`
  - `handle.angleDeg`
  - `handle.plane`
- Draw all route segments live before generation.
- `Y` should generate the whole route into tunnel segments in one operation.
- Keep generated segments chunked near `mapAutogenTargetLength()`, not long stretched mega-segments.

### 2. Plane-Locked Point Creation

When adding a new route node:

- Default to the current active plane (`mapMouse.editPlane`).
- If the first point is `{x, y, z}`, the next point should keep the fixed axis from that plane until the user drags it off-plane with the XYZ tool.
- Examples:
  - XY plane keeps Z constant.
  - YZ plane keeps X constant.
  - ZX plane keeps Y constant.

### 3. C Handle Angle

For each C handle, add a numeric angle field:

- Positive angle pushes the handle out of the active plane in one direction.
- Negative angle pushes the handle the opposite way.
- The generated route should arc through that adjusted handle.
- Keep the handle draggable on the active plane plus editable numerically.

### 4. XYZ Transform Gizmo

Add a small CAD-style gizmo for selected route nodes, C handles, existing tunnel endpoints, portal discs, and target boxes:

- X axis drag moves only X.
- Y axis drag moves only Y.
- Z axis drag moves only Z.
- The gizmo should show red/green/blue or labeled X/Y/Z arms.
- Dragging an existing tunnel endpoint should recompute adjacent segment basis/length and smooth neighbor continuity instead of creating a kink.

### 5. Existing Tunnel Range Operations

Expand current range selection:

- Delete selected A-to-B connected tunnel range.
- Apply texture/rib color to range already works through `V`; keep that.
- Later: copy/cut/move/resize selected connected run.

### 6. Target Batch Operations

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
