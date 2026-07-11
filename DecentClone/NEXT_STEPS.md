# Astral Drift — Project Notes

**Updated:** 2026-07-11
**Location:** `DecentClone/index.html`
**Status:** Playable 6DOF tunnel shooter and builder with combat, chambers, and the first Galaga-style arcade stage. Independent side project (not related to the trading bot).

---

## What Works Today (v0.4+)

### Flight
- Native canvas 2.5D renderer (Engine Bypass — no Three.js runtime dependency).
- Full 6DOF cockpit controls: W/S/A/D/R/F thrust, Q/E roll, arrows pitch/yaw, mouse steer, C turret look, 1–6 snap views, Shift boost.
- HUD controls: `Ctrl+H` toggles full help/compact vitals; `Alt+M` hides or restores the entire HUD so the left panel cannot intercept mouse steering.
- Tunnel collision: wall containment, scrape damping, boost scrape behavior, segment handoff at junctions.
- Lasers (V / RMB / gamepad).
- Gamepad scaffold (needs hardware testing on your controllers).

### Map / Builder Tools (press **M** for 3D map, **B** for builder cursor)
- Segment builder: T straight, I/K/J/L bends, O branch, U undo, Del delete, G prune strays.
- **Directed tunnel join:** LMB source A → Ctrl+LMB target B → optional Shift+Ctrl+LMB bend C → **Y** builds curved connector.
- **3D endpoint editing:** XY / YZ / ZX edit planes via orientation cube; drag B/C on plane; click join line for manual XYZ dialog.
- **Portal gateways:** LMB entry → **8** portal mode → Ctrl+LMB exit → **Y** links (no tunnel tube). Violet ring = entry, blue ring = exit. Fly into ring to teleport (bidirectional). **Del** removes selected portal.
- **Doorway rooms:** portals can be marked as doors into builder-created rooms for loot, quest items, traps, enemies, and guard barracks.
- **Spherical chambers:** **Make Chamber** creates a fully textured 360-degree room with free flight in every direction, including vertical `R/F` movement.
- **Complex junctions:** eight-way intersections can be entered through any connected outlet at full speed without collision or routing errors.
- Save/load named maps (`Ctrl+Shift+S` / `Ctrl+Shift+L`), import/export JSON through the map-library dialog, and autosave to localStorage.

### Still Missing Or Incomplete

- Missions, upgrade pickups/caches, and the complete 90-level tunnel → arcade → space campaign are not implemented.
- Galaga stage 1 is playable; Galaga stages 2–10, Pac-Man stages 1–10, and Defender stages 1–10 remain.
- Full enemy combat, shields, hull damage, death/game-over, restart, scoring, top-10 name entry, portal transit VFX, and portal audio are implemented.
- Builder docs in `game_concept_zero_gravity_astral_shooter.md` still valid for vision; mechanics section below is authoritative for current build.

---

## Portal Workflow (Quick Reference)

**Important:** the **B key** toggles builder mode — it is **not** point B. Point B is always **Ctrl+LMB**.

1. **M** — open 3D map  
2. **LMB** — select tunnel endpoint (portal entry **A**)  
3. **Ctrl+LMB** — set exit location **B** (use cube XY/YZ/ZX + drag for depth)  
4. **Shift+Y** — create portal gateway (easiest — works immediately)  
   - Or press **8** first to enter PORTAL mode (purple banner), then **Y**  
5. **M** — return to flight; fly into the **violet disc** to teleport  

- **Y** alone = curved **tunnel tube** (default)  
- **Shift+Y** = **portal** (no tube, dashed violet link)  
- **8** = toggle PORTAL / TUNNEL mode (optional; does not clear point B)  

Esc cancels portal mode before linking. **Del** removes a selected portal.

---

## Current Keyboard And Mouse Controls

### Shared / Play Mode

- `Ctrl+H`: toggle full help versus compact vitals HUD.
- `Alt+M`: hide or restore the entire HUD panel.
- `W/S`, `A/D`, `R/F`: forward/reverse, lateral strafe, and vertical strafe.
- Arrow keys: pitch/yaw. `Q/E`: roll. `Shift`: boost.
- `;`: toggle AutoCruise/AutoBoost; reverse with `S` cancels it.
- Hold `LMB`: mouse steering. `V` or `RMB`: fire. Hold `C`: turret/free look.
- `1–6`: snap views. `H`: cycle HUD-map plane.
- `K`: reset cockpit controls/orientation. `0`: recover the ship to the tunnel.
- `B`: toggle builder cursor. `M`: toggle full 3D map.
- `Ctrl+Shift+R`: developer repair. `Ctrl+Shift+G`: developer-toggle the current Galaga stage.
- `R` after death: continue using a remaining life or restart after game over.

### Builder / 3D Map

- `T`: straight tunnel. `I/K/J/L`: bends. `Q/E`: rotate bend plane. `[`/`]`: change bend angle. `O`/`Shift+O`: branch/opposite branch.
- `U`: undo segment or route edit. `Del`/`Backspace`: delete selected segment/range. `G`: prune disconnected segments. `C`: cycle selected pipe kind.
- `Y`: build A→B tunnel/route. `Shift+Y`: create portal. `8`: portal/tunnel mode. `7`: sentry mode.
- `N`: route mode. `Shift+N`: pause/resume route drawing. `Esc`: cancel the active mode or clear selections, route draft, and orbit anchor.
- `Alt+N`: open the corkscrew/helix generator. Select endpoint A first; optionally select B for compatible fit-to-endpoint routes. The tool creates a paused editable N-route preview, and `Y` builds it.
- `Ctrl+Shift+S`: save named map. `Ctrl+Shift+L`: open map library.
- `0`: frame the whole tunnel. `9`: focus anchor/B/ship. `Space`: release snapped plane for free orbit.
- `,` (comma): show or hide the active-plane grid.
- `.` (period): toggle 50-unit grid snapping; holding `Shift` while dragging temporarily snaps to the grid.
- `\\` (backslash): lock or unlock the active XY/YZ/ZX edit plane. Forward slash `/` has no current binding.
- `Z/X` or mouse wheel: zoom.
- Orientation cube: the cube rotates with the map camera. Click a face for front/back/left/right/top/bottom orthographic views; click a beveled edge or corner for a 45-degree diagonal view. Face clicks select and lock the corresponding XY/YZ/XZ plane; diagonal clicks preserve the current edit plane. The separate `XY`, `YZ`, and `XZ` buttons beneath the cube change/lock only the work plane without moving the camera.
- XYZ gizmo: solid labeled axes lie in the selected edit plane. The dashed axis labeled `⟂` is perpendicular to that plane; all axes remain true world X/Y/Z directions as the camera rotates.
- When an axis points nearly into the camera, its screen projection is too short for stable along-line dragging. The gizmo automatically switches that axis to controlled vertical-mouse depth movement and limits accidental extreme jumps; the HUD reports `depth drag: vertical mouse`. Direct dragging of spline C handles also rejects near-parallel camera/plane intersections and stays bounded around the C point's position at drag start.

### Corkscrew / Helix Route Generator

Press `Alt+N` in map or builder mode. The generator supports:

- Tunnel outside-to-outside diameter or centerline-path diameter.
- Starting and ending diameter for tapered corkscrews.
- Starting and ending rise/fall per turn for variable pitch.
- Positive climb or negative descent.
- Fractional turn counts such as `0.5`, `2`, or `4.4`.
- Clockwise/counterclockwise rotation.
- World X/Y/Z axis or the normal of the current edit plane.
- Start-angle offset and 4–48 editable route points per turn.
- Smooth tangent alignment to a selected tunnel endpoint A.
- Optional S/reverse helix with handedness reversal halfway.
- Optional fit to selected B for whole-turn routes or S/reverse routes.

The tool does not generate bank/roll because tunnels have no fixed up/down and the ship controls its own roll. It creates an ordinary paused N-route preview; adjust any node/C handle, then press `Y` to build normal tunnel geometry.
- Map camera: arrows orbit; `W/S`, `A/D`, `P` or `R`/`F` pan; `Alt+drag` or middle-drag orbits around the current pivot.
- Selection: `LMB` sets A; `Ctrl+LMB` sets B; `Ctrl+Shift+LMB` sets C; `Alt+Shift+LMB` selects a tunnel range or sets a free orbit anchor on empty space.
- `Shift+LMB` multi-selects targets/tunnel pieces. `V` edits selected tunnel style or selected target batch.
- `Alt+LMB` or double-`RMB` snaps the camera to a tunnel. `Ctrl+Alt+LMB` sets an object as a tethered orbit anchor.
- In sentry mode, `Ctrl+LMB` places a sentry and `Shift+drag` moves an existing sentry spawn.

`Ctrl+Shift+K` is not a current binding and must not be documented as “new map.”

---


## Build Mode (Next Small Steps)

Texture-manifest loading, per-segment wall textures, default wall texture selection, and per-sentry ship/weapon-effect selection are implemented.

Add tunnel run range editing:
- Select point A on an existing tunnel path, then point B farther along the connected tunnel.
- Highlight the whole connected run between A and B as one selected range.
- Actions on that selected range:
  - Delete the whole tunnel run as one operation. **Done.**
  - Apply one wall texture / rib color to the whole tunnel run as one operation. **Done.**
  - Move/refit the selected run with a middle C bend and XYZ gizmo. **Implemented but incomplete: modifying a tunnel section still leaves artifact tunnel pieces behind.**
  - Later optional tools: copy, cut, move, duplicate, resize radius, or convert normal tunnel pieces to branch-marked pieces.
- UI idea: range mode in builder tools with visible A/B handles, selected segment count, and approximate path length.

Target-box multi-select, batch editing, destructive/normal toggles, and batch deletion are implemented. Optional batch label prefix/sequence and texture/sprite assignment remain.

Add CAD-style 3D map navigation and transform tools:
- Orbit camera around a picked anchor point:
  - Click a tunnel point / endpoint / waypoint / object as the orbit anchor.
  - Mouse drag rotates the camera around that fixed point, instead of rotating/panning the whole world in a hard-to-track way.
  - Keep zoom distance adjustable while tethered to the picked anchor.
- XYZ transform gizmos and numeric coordinate editing are implemented for the principal route, join, portal, target, sentry, and tunnel-range edit points. Axis consistency and existing-tunnel stability still need polish.

## Near-Term Gameplay (Next Small Steps)

Priority: expand the playable progression while keeping the editor fun.


Completed gameplay foundations: portal VFX/audio and one-way portals; shield meter and low-shield warning; shootable targets; sentry AI/pathfinding; scoring; engine/boost/laser/scrape audio; tunnel-ring polish; portal shimmer; and wall-hit sparks.

Next gameplay work:

1. Galaga stages 2–10 and challenge-wave progression.
2. Pac-Man stages 1–10.
3. Defender stages 1–10.
4. Space levels 1–30: exploration, station repairs, item buying, and quests.
5. Upgrade pickups/caches and mission objectives in the core tunnel game.
6. Tunnel levels 1–30 and the full 90-level campaign sequence: Tunnel 1 → Galaga 1 → Space 1 → Tunnel 2 → Pac-Man 1 → Space 2 → Tunnel 3 → Defender 1 → Space 3, then repeat the arcade rotation.

---

## Medium-Term

- Arcade-remix bonus stages (Pac maze, Galaga wave, etc. — reinterpreted from cockpit, not cloned assets).
- Open-space breather zones between tunnel runs.
- In-game builder expansions: enemy spawn markers, cache placement, sign/text props.
- Procedural director that rearranges authored tunnel pieces + portals into surprise layouts.
- Enemy archetypes: sentry, patrol, swarm, sniper, hunter.
- Physics biomes: gravity wells, fluid drag, rotating habitat sections.
- WebXR / Three.js renderer layer (keep this canvas build as the feel lab).

---

## Architecture Notes

Single-file prototype is intentional for fast iteration. Map data shape:

- `segments[]` — tunnel tubes (from/to, basis vectors, radius, kind)
- `portals[]` — `{ id, entry, exit, bidirectional }` gateway pairs
- Saved via localStorage + named map library + JSON export

When splitting into modules later:

- **game logic** — movement, weapons, portals, collision, shields  
- **input** — keyboard, mouse, gamepad, future VR  
- **renderer** — canvas prototype → WebGL/WebXR  

---

## Priority Reminder

Keep this as a low-cost creative side project. Preserve ideas in this file, ship small playable slices, and avoid burning big budget before trading/combine work is stable. The prototype is already fun to fly and design in — next wins are game feedback (teleport juice, targets, shields, sound).



// Conceptual Pixel Loop for Brushed Metal
for (let i = 0; i < pixels.length; i += 4) {
    let nx = normals[i]; 
    let ny = normals[i+1] + Math.sin(y * 0.1) * 0.1; // Simulated horizontal brush streaks
    let nz = normals[i+2];

    // Dot product for diffuse lighting
    let dot = nx*lx + ny*ly + nz*lz; 
    
    // High-power specular reflection
    let reflection = Math.pow(Math.max(0, dot), 64) * 255; 
    
    pixels[i]     = 180 + reflection; // Red
    pixels[i + 1] = 180 + reflection; // Green
    pixels[i + 2] = 185 + reflection; // Blue (slight blue tint for steel)
}
A

const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function startEngine() {
    let osc = audioCtx.createOscillator();
    let filter = audioCtx.createBiquadFilter();
    let gain = audioCtx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(45, audioCtx.currentTime); // Deep hum

    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(150, audioCtx.currentTime); // Muffle the buzz

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);
    
    osc.start();
    
    // To change RPM dynamically in your game loop:
    // osc.frequency.setValueAtTime(45 + currentSpeed * 2, audioCtx.currentTime);
}
function playLaser() {
    let osc = audioCtx.createOscillator();
    let gain = audioCtx.createGain();

    osc.type = 'sawtooth';
    let now = audioCtx.currentTime;

    // Pitch Envelope (Fast drop)
    osc.frequency.setValueAtTime(1500, now);
    osc.frequency.exponentialRampToValueAtTime(40, now + 0.3);

    // Volume Envelope (Quick decay)
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);

    osc.connect(gain);
    gain.connect(audioCtx.destination);

    osc.start(now);
    osc.stop(now + 0.3);
}

// 1. Generate a 1-second reusable White Noise Buffer
const bufferSize = audioCtx.sampleRate;
const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
const output = noiseBuffer.getChannelData(0);
for (let i = 0; i < bufferSize; i++) {
    output[i] = Math.random() * 2 - 1;
}

function playCollision() {
    let noiseSource = audioCtx.createBufferSource();
    noiseSource.buffer = noiseBuffer;

    let filter = audioCtx.createBiquadFilter();
    let gain = audioCtx.createGain();

    // Lowpass filter makes it sound "heavy" like metal/rock impact
    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(300, audioCtx.currentTime);

    // Exploding volume envelope
    let now = audioCtx.currentTime;
    gain.gain.setValueAtTime(0.5, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

    noiseSource.connect(filter);
    filter.connect(gain);
    gain.connect(audioCtx.destination);

    noiseSource.start(now);
    noiseSource.stop(now + 0.4);
}


// 1. Initialize Global Audio Context
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
const listener = audioCtx.listener;

// Set the player's head position at the center of the universe (0,0,0)
if (listener.positionX) {
    listener.positionX.setValueAtTime(0, audioCtx.currentTime);
    listener.positionY.setValueAtTime(0, audioCtx.currentTime);
    listener.positionZ.setValueAtTime(0, audioCtx.currentTime);
}

// 2. Create a Spatial 3D Laser Generator
function shoot3DLaser(startX, startY, startZ, velocityX, velocityY, velocityZ) {
    let osc = audioCtx.createOscillator();
    let panner = audioCtx.createPanner();
    let gain = audioCtx.createGain();

    // Configure 3D HRTF Spatialization for Headphone Immersion
    panner.panningModel = 'HRTF'; // Human Head-Related Transfer Function
    panner.distanceModel = 'exponential';
    panner.refDistance = 1;       // Distance where volume starts dropping
    panner.maxDistance = 10000;   // Maximum audible distance
    panner.rolloffFactor = 1.5;   // How fast the sound fades out

    // Set initial 3D position
    panner.positionX.setValueAtTime(startX, audioCtx.currentTime);
    panner.positionY.setValueAtTime(startY, audioCtx.currentTime);
    panner.positionZ.setValueAtTime(startZ, audioCtx.currentTime);

    // Audio routing
    osc.connect(panner);
    panner.connect(gain);
    gain.connect(audioCtx.destination);

    // Laser Pitch Pitch Envelope
    let now = audioCtx.currentTime;
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(1200, now);
    osc.frequency.exponentialRampToValueAtTime(80, now + 0.4);

    gain.gain.setValueAtTime(0.6, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

    osc.start(now);
    osc.stop(now + 0.4);

    // 3. Dynamic Tracking Loop for Doppler & Position
    let laserX = startX;
    let laserY = startY;
    let laserZ = startZ;
    
    function updateFrame() {
        if (audioCtx.currentTime > now + 0.4) return; // Stop tracking when sound ends

        // Move the laser through 3D space over time
        laserX += velocityX;
        laserY += velocityY;
        laserZ += velocityZ;

        // Update the 3D panner position natively
        panner.positionX.setValueAtTime(laserX, audioCtx.currentTime);
        panner.positionY.setValueAtTime(laserY, audioCtx.currentTime);
        panner.positionZ.setValueAtTime(laserZ, audioCtx.currentTime);

        // [Optional] Calculate distance to listener for Doppler pitch modifications
        let distance = Math.sqrt(laserX*laserX + laserY*laserY + laserZ*laserZ);
        
        requestAnimationFrame(updateFrame);
    }
    requestAnimationFrame(updateFrame);
}

## Chamber And Doorway Room Status — Verified 2026-07-11

- **Make Chamber** creates a full 360-degree spherical room.
- Chamber textures correctly cover the ceiling, walls, and floor.
- Chambers are freely flyable in every direction; `R/F` vertical movement is no longer pinned or blocked by containment drag.
- Door-marked portals can connect tunnels to chamber rooms.
- These rooms are ready to host quest items, loot, traps, hostile encounters, and guard barracks.

