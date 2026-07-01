## Astral Drift Current Work List

Use `DecentClone/index.html` as the source of truth. Preserve the existing
flight/render path and keep map saves backward-compatible.

## Highest Priority Bugs

### 1. Straight Up / Straight Down Tunnel Flight Control

Vertical tunnel runs are now easy to build with the 3D tool, but flying into
straight-up or straight-down tunnels quickly breaks control orientation:

- Pitch/yaw/strafe directions feel reversed or crossed.
- Ship can lose useful forward/up reference and becomes hard to steer.
- Fix likely belongs in tunnel-frame/orientation math, not in builder geometry.
- Goal: full 6DOF flight must remain stable through vertical shafts, loops, and
  sharp 3D changes without camera/ship axes flipping.

### 2. Branch / Auto-Connect Junctions Are Not Reliably Enterable

Auto-connect often creates geometry that visually touches a tunnel but does not
produce a clean flyable entrance:

- Branch line may pass through the existing tunnel and end outside it.
- Auto-connect from outside into an existing tunnel can cut a big notch.
- Starting from the tunnel outward looks cleaner but still may not create an
  enterable opening.
- Goal: click an existing tunnel, draw/build a branch, and have the code create
  a clean junction opening/connector object automatically.

Treat manual angle tweaking as a fallback, not the main workflow.

### 3. ABC Existing-Tunnel Move Tool Stability

ABC move mode mostly works now and the old leftover-artifact trail was improved,
but it still needs hardening:

- After using the 3D tool a few times, the gizmo can become inactive and stop
  moving the selected item.
- It has previously relinked a tunnel run to a far-off tunnel unexpectedly.
- It has previously punched holes in nearby unrelated tunnel runs.
- Goal: moving A/B/C on an existing connected tunnel run should only affect the
  intended connected range and should keep a smooth fit.

Preferred edit model:

- Select start and end of a connected tunnel range.
- Drag a middle C/control point.
- Refit the selected run smoothly between start/end instead of making jagged
  per-segment kinks.

### 4. 3D Gizmo Axis Consistency

The 3D move tool axis labels/directions do not always match the X/Y/Z grid panel
that appears when clicking tunnel pieces.

- Make gizmo X/Y/Z directions consistent with the grid/plane UI.
- Keep axis movement one dimension at a time.
- Avoid oversensitive handle picking.

## Builder Features To Keep / Already Working

- Enemy ship sprite loading and scaling is working.
- Enemy AI chase/targetability is working well enough for now.
- Tunnel opacity/neighbor visibility is much improved and acceptable for now.
- AutoBoost exists and is liked, but `;`/semicolon behavior should stay watched
  because it previously stopped the ship when pressed during W/Shift movement.
- Multi-segment route mode exists:
  - `N` starts route mode.
  - `U` undoes route steps.
  - Drawing can be paused/resumed so left-click does not keep adding unwanted
    segments while editing.
  - `Y` renders routes, including free-floating routes.
- Plane-locked creation is working well.
- XYZ gizmo works well on draft segment nodes/handles.
- HUD map no longer shows all sentries/enemies by default.

## Medium Priority Builder Improvements

### 5. Free-Drag Yellow Build Handle

Add an optional way to click/drag the yellow build handle freely in 3D:

- Should allow orienting a new branch more naturally than only `Q/E` and `[]`.
- Must not be oversensitive or move just because the user tried to select it.
- Keep existing keyboard controls as fallback.

### 6. Tunnel Range Operations

Existing range selection should grow into safer CAD-style operations:

- Delete selected A-to-B connected tunnel range.
- Move/refit selected connected run.
- Later: copy/cut/resize selected connected run.

Texture/rib-color range apply through `V` already works; keep it.

## Gameplay / Map Ideas Backlog

### Cache Rooms, Hidden Doors, And Quest Rooms

Add side rooms/caves that can be connected by visible or hidden doors:

- Some doors clearly marked.
- Some doors found by scanner while stopped/not moving.
- Scanner chance starts low, around 10%, and can be upgraded at garages.
- Rooms can contain treasure, quest objects, guards, or hostile groups.
- Room entrances may also be portals to small off-map cave rooms.

### Gadgets Backlog

Player gadgets are still back-burner:

- Cloaking mode.
- Smoke bomb.
- Nanobot slick.
- EMT/EMP bomb.
- Developer god mode with unlimited gadget use for testing.

## Documentation Backlog

Write `astral_technical_reference.md` later:

- Explain architecture for a new programmer.
- Flow-chart game loop, builder mode, map geometry, rendering, controls, and
  save/load path.
- Comment complex code, but do not bury simple code in noisy comments.

## Required Safety Rules For Code Edits

- Do not remove `applyMapGeometryChange()`.
- After tunnel geometry edits, call the required rebuild/sync functions:
  - `syncBuilderTargetsFromGeometry()`
  - `rebuildTunnelStars()`
  - `rebuildTunnelTargets()`
  - `invalidateTunnelSegmentCache()`
  - `saveTunnelMap()`
- Keep map save format backward-compatible.
- Run the script parse check after edits:

```powershell
$p = "DecentClone\index.html"
$html = Get-Content $p -Raw
$m = [regex]::Match($html, '(?s)<script>(.*)</script>')
$scriptPath = Join-Path $env:TEMP 'astral_index_inner_script.js'
Set-Content -Path $scriptPath -Value $m.Groups[1].Value
$checkPath = Join-Path $env:TEMP 'astral_index_script_check.js'
Set-Content -Path $checkPath -Value "const fs=require('fs'); new Function(fs.readFileSync(process.argv[2], 'utf8')); console.log('script parse OK');"
node $checkPath $scriptPath
```
