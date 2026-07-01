## Asrtal Drift play and builder modee work that nees doing

## Tasks in need of doing at the stop of the stack

#1
Fully document this code like you were doing so for youtr 10 year old son whos taken up an interest
  in programming and gamed  development. game devel is what fist drew me into the field of
  computers and this one extses me a lot.. I tried impementing the autoboost myself the other day and
  it took me a few hours to try and flow chart the code in my head and then start searhing similar
  code to mimic. Not only idiot proof comment the hell of of it but write up an atral_technical_reference.md
  that flow charts the flow of the program and goes into same detail we do on the trading bot , such
  as instructions a new coder would want to know to ge up to speed on it

 ##2

Its totatly losing the tunneleffect of the game that even ith fully texture covered tunne walls i can
still see the other tunnels visibly al around me. i like tis "Feature" to be kept fo special use. IE add
a tune flag option for if textues are Opaque or not opaque. The default is they are 100pct fdense, you cant see
anything throug hthm of the outside workd or neighboring tunnesls Big task make this a reality

#3
its tiring holding shft and w to keep yhe engines going which makes it dam near imppossibel to work
any headmovement, strafing or rolling with the same hand and right hands busty with mouse or arrow keys steering
Add an AutoBoost option, a toggle on or off, Whe on the game will ignore 'w' and'shift always boost your speed to max.
Besides the toggle off autoboost key sequencre you choose also make S or backup immediately disable autoboost.
As we have 2 speeds, w and shift ,make autoboost lock in the speed your doing when engaged, if jut 'w' then it makes
you keep going 'w', but if engage when your doing 'shift' 'w' then itll keep you at that speed even withouy holding either
key. if its engaged at 'w' youd temporaraily press 'w' and 'shift' and toggle auto boost off then on to make ti pock in
turbo speed

#4 AI Ships
once those things engage youll see them fly by once thenbo matter here you look, free spin look behind, do a uturn,
anything you wont see them and cant target them to shoot them yet go as fast as you want they keep up and kill you,
Get the icons fixed above fist then lets make sure they stay out front of you to start , tailing behind shhe give chase
but easilty spottable and targetable by lookinh in the rear view. Also its time to add Spy  VS Spy gadgets to the player
ships Not al will be available at first they wi be game awardded uphrades
 - Cloaking mode
     - not usable if you have a live ai still agressively chasing you.
         - Drops if you fire a single shot
         - Drops if you trigger an explosive target box
         - Drops if you hit a wall at turbo speed and leave sparks
        - Limited use 3 tims per Cloak Boost Pack, to be found i game Staches, each oe granting 3 cloaks.
        - Not usable at all until your ship is upgraded to have a cloaking device at a Space Station Garage, bought with
            game earned coin and not until reach level 3. shows n Garage shop as locked if not level 3 or above
 - Smoke bomb
    - Limited use, lasts 10 seconds and leaves entre tunnel behind you unable to see at all , lasts as far as you travel
            in 10 seconds. Will cause AI to loose track of you and return to patrol .
            - Recharges found in Cache and bought at Garage. Coes 3 uses per pack
 - Nanobot slick
    - works like a oil slick leaves a traiil behind for 5 seconds. Ay thip running int tem is attacked by swarm of nano
          bots  that cause the ship to slide out of control intowals losing direction just like an oil slick
        - Foun in caches ad bought in Garages, 3 use per pack
- EMT Bomb
  -- totally disables al machinery in its wake goes off 2 secones fter deployed. will also disable player  if they arent
     moving when deployed and ahead when it goes off. Leaves visible in air partciles effect of where its active so player
         is free to stop turn , stay outside the effect zne and shoot and kill the now disabled AI
  - Use 1 per charge  not usalbe till level 5 , found only in rare caches generally during quests obtained at the
      smuggles guild at space stations or bought if available at the same smugglers guilds
- Developer God Mode
  Switchwhen enable have full unlimite use of all above weaponry. ot fo in game player use just testing developer mode


 Cursor is no more these are now back i n your lap

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
- - Add batch texture/sprite when target texture assets are added.

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
