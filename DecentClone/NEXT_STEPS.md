# Astral Drift — Project Notes

**Updated:** 2026-06-21  
**Location:** `Ron/Coding Projects/DecentClone/index.html`  
**Status:** Playable flight prototype with in-game map editor. Independent side project (not related to the trading bot).

---

## What Works Today (v0.4+)

### Flight
- Native canvas 2.5D renderer (Engine Bypass — no Three.js runtime dependency).
- Full 6DOF cockpit controls: W/S/A/D/R/F thrust, Q/E roll, arrows pitch/yaw, mouse steer, C turret look, 1–6 snap views, Shift boost.
- Tunnel collision: wall containment, scrape damping, boost scrape behavior, segment handoff at junctions.
- Lasers (V / RMB / gamepad).
- Gamepad scaffold (needs hardware testing on your controllers).

### Map / Builder Tools (press **M** for 3D map, **B** for builder cursor)
- Segment builder: T straight, I/K/J/L bends, O branch, U undo, Del delete, G prune strays.
- **Directed tunnel join:** LMB source A → Ctrl+LMB target B → optional Shift+Ctrl+LMB bend C → **Y** builds curved connector.
- **3D endpoint editing:** XY / YZ / ZX edit planes via orientation cube; drag B/C on plane; click join line for manual XYZ dialog.
- **Portal gateways:** LMB entry → **8** portal mode → Ctrl+LMB exit → **Y** links (no tunnel tube). Violet ring = entry, blue ring = exit. Fly into ring to teleport (bidirectional). **Del** removes selected portal.
- Save/load named maps (P / Shift+R), import/export JSON, autosave to localStorage.

### Not Yet Game-Like
- No shield HUD, enemy AI, pickups, scoring, missions, or audio. actually full enemy combat is in with shield daamge tracked once shields down
  you take hull damage, once hull 0 you die, game over message , high sccore chance if top 10 edit nakme, restart
  
- Portals teleport instantly — no transit VFX yet. Actually there is a delay a transoporting graphic and a sound teoeports are done
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


## Build Mode (Next Small Steps)
Builder mode add a library of textures based on asset type, AI Ships, Wall Textures, Effects
when in buildmode click and set the wall texture of any given tunnel segment and the radio button 
to make this the current default if build a new section till you override it 
Add to code whatever is neded to read the maps texture file mapping as it renders each section.

Add to AI build mode the abilit to choose a ship type and a paticle weaon effect from the libraries 
and assing to that specific AI as well as default going forward option

Add tunnel run range editing:
- Select point A on an existing tunnel path, then point B farther along the connected tunnel.
- Highlight the whole connected run between A and B as one selected range.
- Actions on that selected range:
  - Delete the whole tunnel run as one operation.
  - Apply one wall texture / rib color to the whole tunnel run as one operation.
  - Later optional tools: copy, cut, move, duplicate, resize radius, or convert normal tunnel pieces to branch-marked pieces.
- UI idea: range mode in builder tools with visible A/B handles, selected segment count, and approximate path length.

Add target-box multi-select editing:
- Shift-click or drag-select multiple target boxes in map/builder mode.
- Batch edit the selected row/cluster as one operation.
- Main use case: flip a whole row of boxes to destructive red gate targets without opening each one.
- Batch fields: explosive/destructive toggle, label prefix, respawn seconds, score value, color/type.

Add CAD-style 3D map navigation and transform tools:
- Orbit camera around a picked anchor point:
  - Click a tunnel point / endpoint / waypoint / object as the orbit anchor.
  - Mouse drag rotates the camera around that fixed point, instead of rotating/panning the whole world in a hard-to-track way.
  - Keep zoom distance adjustable while tethered to the picked anchor.
- Add an XYZ transform gizmo for editable points:
  - When moving tunnel endpoints, join point B, bend point C, portal endpoints, target boxes, or sentry spawns, show X/Y/Z axis handles at the selected point.
  - Drag red/green/blue handles to constrain movement to X, Y, or Z.
  - Keep current plane/grid workflow as a quick mode, but use the gizmo when precision matters.
  - Later: add numeric XYZ input beside the gizmo for CAD-style exact placement.

## Near-Term Gameplay (Next Small Steps)

Priority: make it feel like a game while keeping the editor fun.
Add to render ode to lookup the proper textures to render when encountered


1. **Portal polish**
   - Brief flash / streak VFX on transit
   - Soft whoosh sound placeholder DONE
   - Optional one-way portals done

2. **Shield + HUD**
   - Shield meter (wall scrapes already track intensity) done
   - Low-shield warning color

3. **Shootable target → enemy pipeline**
   - Existing cache/box targets: add destroy on laser hit done
   - Simple sentry drone at fixed point (no pathfinding yet) DONE PAthfinding DONE as well
   - Score or pickup counter

4. **First audio pass**
   - Engine hum, boost, laser, wall scrape, portal transit done

5. **Visual richness (cheap wins)**
   - Tunnel ring cadence improvements done
   - Portal shimmer animation done
   - Spark particles on wall hit (reuse wallHit intensity) done

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

## Claude Handoff - 2026-07-05 Chamber/Boost State

Current repo/server state: Astral Drift lives in `DecentClone/index.html` on `main`, served by `astral-drift.service` as a static `python3 -m http.server 8127`. Recent chamber commits attempted to make detached capped rooms behave like spherical chambers, but the user reports the room is still not solved: floor/ceiling/walls in the chamber still lack useful texture, `R/F` up/down feels pinned to the floor, and trying to go up feels like collision containment/drag is slowing the ship. The latest unverified containment tweak makes chamber containment non-drag/free-flight-ish by clearing `wallHit` and only clamping beyond `radius * 1.35`, but user has not validated it yet.

Known recent code areas to inspect first:
- Chamber detection/helpers: `segmentIsChamber`, `chamberProfileRadius`, `chamberCenterPoint`, `chamberDistanceState`.
- Flight containment: `containShipInTunnel()` chamber branch. Suspect: nearest segment/containment still chooses or behaves like tunnel in the test room, or room radius/center from saved map is not what the renderer/collision expects.
- Movement: `updateFlightPhysics()` now makes Shift imply forward thrust so Shift alone should boost forward; inside chambers it also tries to make `R/F` use `-seg.down` as lift.
- Rendering: WebGL chamber path now uses `buildChamberSphereGpuMesh()` and `mat4ChamberModel()`, but user still reports no texture on chamber ceiling/walls, so verify whether the browser is actually in `webgl`, `vector`, or `jpg` texture mode and whether sphere mesh is visible from inside.
- Door/portal reach: `portalVisualPoint()` and `shipWithinPortalActivateRange()` were made chamber-aware, but user reported the exit portal was too high to activate before the latest reach changes were validated.

Most likely next debug move: add a temporary HUD/status line while inside a chamber showing selected segment index, `segmentIsChamber`, chamber radius, distance from center, `shipSegmentIndex`, `TUNNEL_TEXTURE_MODE`, and whether wallHit is active. That will quickly prove whether the ship is actually in the chamber branch or still being treated like a tunnel/wall scrape.

