## Astral Drift Current Work List

Use `DecentClone/index.html` as the source of truth. Preserve the existing
flight/render path and keep map saves backward-compatible.

## Remaining Priority Bugs

### Vertical Two-Way Spline Handoff — Major Fix Verified

`CorkScrew1` reproduced a jerky cockpit toss near world position
`(-1350, -3348, 9567)`, where join-curve segment 431 meets segment 389.
This is the crest where flight changes from climbing upward to nosing over and
traveling backward/downward relative to world-up.
The centerlines have zero gap and are covered by the junction bubble, but their
stored right/down frames differ by roughly 30 degrees. Two-way junction flight
assist was blending that roll discontinuity into the cockpit as though the seam
were a multi-outlet steering choice.

The runtime fix preserves the ship's current roll frame across two-piece curved
handoffs and blends only toward the next centerline direction. True intersections
with three or more outlets retain normal branch-selection assistance.

Flight verification on 2026-07-11 passed repeatedly in both directions through
the same location: the jerking/tossing did not recur. One pass may have included
a single barely noticeable perspective adjustment of roughly 15 degrees. Keep
that as low-priority transition polish, but the disruptive bug is resolved.

### 1. General Flight-Control Jitter Polish

- Remaining issue: motion/control can feel a little jittery, likely from guard
  checks added to prevent orientation flips.
- Goal: smooth out the jitter without reintroducing reversed controls or camera
  attitude flips.
- Keep this as polish unless flight becomes unstable again.

### 2. ABC Existing-Tunnel Move Tool Stability

ABC move mode mostly works, but modifying/refitting a selected tunnel section
still leaves artifact tunnel pieces behind. This remains an active verified bug:

- Remove every obsolete segment created by the pre-move tunnel path after a refit.
- Rebuild the affected connected range without leaving duplicate, disconnected,
  or partially overlapping tunnel geometry.
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

### 3. 3D Gizmo Axis Consistency

The 3D move tool axis labels/directions do not always match the X/Y/Z grid panel
that appears when clicking tunnel pieces.

- Make gizmo X/Y/Z directions consistent with the grid/plane UI.
- Keep axis movement one dimension at a time.
- Avoid oversensitive handle picking.

## Builder Features To Keep / Already Working

- Major 6DOF control reversal is fixed through vertical climbs, barrel rolls,
  nose-over past 180 degrees, and 360-degree loop peaks.
- Auto-connect from an existing tunnel to a new branch now creates a proper
  branch in the tested simple case.
- Multi-outlet junction traversal is fixed: an eight-way intersection can be entered through any connected outlet at full speed without collision or routing errors.
- Vertical 90-degree climbs/descents and orientation transitions are fixed; controls no longer reverse or trap the ship in an orientation loop.
- Builder-created spherical chambers are fully flyable in 360 degrees, including vertical `R/F` movement, with textures correctly covering walls, floor, and ceiling.
- Portals can be marked as doorways into chambers for loot, quest items, traps, and guarded rooms.
- Enemy ship sprite loading and scaling is working.
- Enemy AI chase/targetability is working well enough for now.
- Tunnel opacity/neighbor visibility now uses connected-route topology rather than
  imported segment array order. Opaque shells hide adjacent routes, sentries, and
  weapons; deliberately non-opaque sections retain the authored glass-tunnel view.
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
- Selected A-to-B tunnel ranges can be deleted with `Del`; middle-C reshaping/refitting exists but still leaves artifact tunnel pieces and is not complete.
- Route C handles support numeric out-of-plane angles.
- Wall, enemy-ship, and weapon-effect texture libraries are loaded from the texture manifest and selectable in builder dialogs.
- Target-box multi-select and batch editing are working.
- Free orbit anchors are working.
- HUD map no longer shows all sentries/enemies by default.
- **Pending HUD exploration map:** at the start of a level, show only the player
  dot. Reveal and retain tunnel/map geometry only as the player travels through it;
  do not expose unexplored routes or the complete level layout.

## Medium Priority Builder Improvements

### 5. Free-Drag Yellow Build Handle

Add an optional way to click/drag the yellow build handle freely in 3D:

- Should allow orienting a new branch more naturally than only `Q/E` and `[]`.
- Must not be oversensitive or move just because the user tried to select it.
- Keep existing keyboard controls as fallback.

### 6. Tunnel Range Operations

Existing range selection should grow into safer CAD-style operations:

- Later: copy/cut/resize selected connected run.

Texture/rib-color range apply through `V` already works; keep it.

## Gameplay / Map Ideas Backlog

- Galaga combat difficulty has level-aware interpolation for levels 1–10. The
  original commented values are level 1 and the current hard settings are level
  10. The campaign director still needs to call `startGalagaPhase(level)` with the
  correct arcade-family level number.

### Cache Rooms, Hidden Doors, And Quest Rooms

Doorway portals and fully flyable spherical chambers now provide the room foundation. Expand their gameplay content:

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
