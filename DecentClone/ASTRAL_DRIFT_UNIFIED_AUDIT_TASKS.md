# Astral Drift unified audit task list

Updated: 2026-07-14 (Pacific Time)

Scope: `DecentClone/index.html` and the supporting map/texture assets it loads.

Sources merged:

- Full-code audit supplied in `d51e3d45-632a-4d2d-9bd7-a0fee1ff91f4/pasted-text.txt`.
- Performance/playability/realism/comfort/logic/async audit supplied in `8fa0c5f5-4303-45c0-ac12-f5710e054abf/pasted-text.txt`.
- Direct cross-check against the current source after the audits were written.

This is the canonical backlog for these two audits. Source line numbers are deliberately not
copied here because `index.html` changes frequently. Search for the named function or symbol.

## Status legend

- `[ ]` confirmed work remains.
- `[~]` partially addressed; the narrower remaining work is stated.
- `[?]` plausible proposal that needs profiling, design, or reproduction before editing.
- `[x]` already addressed or disproved in the current source.

## Work rules

1. Only one agent edits `index.html` at a time. Independent read-only reviews may overlap.
2. Complete and validate one batch before starting the next.
3. Preserve the intentionally mode-specific key bindings; a shared letter is not automatically
   a conflict when play, map, builder, and Galaga modes are mutually exclusive.
4. Performance changes require before/after measurements on a large textured map and in TRON mode.
5. Map mutations must continue invalidating the geometry/topology/render caches.
6. Do not include generated maps, browser storage, database/WAL files, or unrelated repository
   changes in a commit.

## Batch A — confirmed correctness and immediate hot-path defects

These changes are small enough to review together and should be completed first.

- [~] **AD-A01 — Restore correct tunnel GPU mesh length and caching.**
  Implemented with a shared unit-length cylinder mesh and exact per-section forward scaling; the
  forced `400.0` span/`150` detail and cache bypass are removed. A browser visual smoke test remains.
  Acceptance: short and long segments reach their real endpoints, textures still cover a section
  once, door-frame textures stay aligned, and repeated frames stop creating buffers.

- [~] **AD-A02 — End Galaga state when the ship is destroyed.**
  Cleanup now ends the bonus state without restoring its saved position, and all three Galaga damage
  paths stop the current tick after fatal cleanup. Browser tests of remaining-life respawn and final-
  life restart while Galaga is active remain.

- [x] **AD-A03 — Run sentry regeneration once per simulation tick.**
  The duplicate pre-gate call is removed. Regeneration intentionally pauses during game-over, map
  view, and portal transit, matching the other combat updates.

- [x] **AD-A04 — Prevent modifier shortcuts from becoming restored flight controls.**
  `physicalKeysHeld` records the letter before Ctrl/Alt/Meta chord handling. Clearing/restoring input
  can resurrect a shortcut letter such as S, R, M, or H as a held gameplay key. Do not register
  command-chord letters or dialog typing as physical flight state. Preserve Shift as a real boost key.

- [x] **AD-A05 — Stop an unrecoverable render exception from looping forever.**
  The render catch displays an error but unconditionally schedules the next frame, producing a hot
  exception loop. Latch the fatal state, stop scheduling, and offer an explicit restart/reload path.
  A WebGL context-loss path should remain separately recoverable in Batch E.

- [x] **AD-A06 — Return/await map-export completion.**
  `exportCurrentTunnelMap()` and `exportNamedTunnelMap()` discard the `exportMapJson()` promise.
  Make the wrappers async or return the promise so callers can report clipboard failure accurately.

- [x] **AD-A07 — Remove duplicate gamepad polling and cache telemetry DOM nodes.**
  `updateFlightPhysics()` reads the controller, then rendering reads it again only for its name.
  Poll once per frame. Cache `pos-val`, `gamepad-val`, and `view-mode-val` instead of resolving them
  through `getElementById()` every frame. Throttle text-only telemetry to a readable cadence.

- [x] **AD-A08 — Remove hot-loop debug residue and mixed fire clock.**
  Gate/remove periodic roll logging, replace global `window.lastShot` and `Date.now()` with a local
  monotonic `performance.now()` timestamp, and remove the unused `autoost` variable.

## Batch B — deterministic timing, collision, and pause behavior

- [~] **AD-B01 — Introduce a fixed simulation timestep.** Implemented: `sim-timing.js` adds a
  DOM-free `advanceAccumulator()` (fixed `SIMULATION_STEP_SEC = 1/60`, frame time clamped to
  `SIMULATION_MAX_FRAME_SEC = 0.25s`, catch-up capped at `SIMULATION_MAX_CATCHUP_STEPS = 8` with
  backlog dropped beyond the cap, plus a `1e-9`s epsilon so float dust from rates that don't divide
  evenly against 1/60 — e.g. 144Hz — can't cost or gain a whole step). `renderEngineLoop()` now
  calls the extracted, unit-tested `AstralSimTiming.frameSteps()` (wraps `advanceAccumulator()` with
  the suspend check) instead of inlining that branch, and runs `tickSimulation()` a variable number
  of times per rendered frame instead of scaling one call by `frameScale`. Simulation and rendering
  are separated (`tickLasers`/`renderLasers`, `updateParticles`/`renderParticles`,
  `updatePortalTransit()` storing `portalTransit.elapsedMs` once for the two render-only readers).
  Regression-tested in `sim-timing.test.js`: 30/60/144Hz each produce **exactly** 120 steps over 2s
  (hard equality, not approximate), and a 5s stall capped at exactly 8 steps with the accumulator
  zeroed, followed by a next-frame check proving the dropped backlog is not inherited (next frame
  runs exactly 1 step). **Fixed in review:** `renderEngineLoop()`'s first-call initialization seeded
  `accumulatorSec` with a whole `SIMULATION_STEP_SEC` instead of `0`. Since that same first call
  always measures a `rawFrameDt` of exactly 0 (`lastSpatialAt` is set to `spatialNow` on the same
  call that seeds the accumulator), the seeded step fired for free before any real time had elapsed
  — an application-style startup (zero-delta first render, then 120 real frames at a steady 60Hz)
  produced 121 steps instead of 120. Now seeded at `0`; a dedicated regression test models exactly
  that startup sequence and asserts exactly 120. Remaining: render-side interpolation between the
  last two simulated states
  was not implemented, so motion is a series of fixed 60Hz steps rather than smoothed on very high
  refresh-rate displays. A browser smoke test (steady 60fps play, a deliberate stall/breakpoint, and
  a high-refresh-rate display if available) remains.

- [x] **AD-B02 — Use one monotonic simulation clock.** A pause-aware `simClockMs` (index.html, next
  to `simulationSuspended`) advances only inside `tickSimulation()`, by exactly one fixed step per
  call — never by wall-clock time. Every gameplay deadline/cooldown/regen timer that was previously
  measured against `performance.now()` now reads `simClockMs` instead (35 call sites converted; full
  inventory of all 65 original `performance.now()` sites below). `tickShieldRegen()`'s own
  `lastShieldTickAt`-based wall-clock delta was removed entirely (it's called exactly once per fixed
  step, so `dt` is just the fixed step). `tickSentries()`'s independent wall-clock delta was likewise
  replaced by `frameScale * SIMULATION_STEP_SEC`. `Date.now()` remains only for random ID generation
  (map/target/sentry/portal IDs) — not a timing concern, left untouched.

  **Converted (gameplay deadlines, now on `simClockMs`) — 35 sites:** shield regen tick;
  Galaga `stateUntil` (intro + results), `nextSpecialAt`, `nextDiveAt`, boss tractor `readyAt` and
  its render-side progress read (`renderGalagaPhase`'s telegraph-cone `progress`, which reads
  `t.readyAt` and must stay on the same clock or the visual would desync from the actual deadline
  while paused), and the single `now` at the top of `tickGalagaPhase()` (every internal Galaga
  deadline check reads that one local, so converting it converts all of them); portal transit
  `startTime`, `updatePortalTransit()`'s elapsed/phase calc (now stores `portalTransit.elapsedMs`
  once, consumed by `getPortalTransitFovStretch()`/`renderPortalTransitVfx()` instead of each
  re-deriving it — two `performance.now()` call sites were removed entirely, not converted, by this
  refactor), portal re-trigger cooldown (`lastPortalTransit.at`, including the click-handler read in
  `tryActivatePortalOnClick()` — safe because `simClockMs` just holds whatever it was as of the most
  recent tick regardless of when the click fires); wall-hit `last`/`lockUntil`/`levelLockUntil`/
  `cockpitResetCooldownUntil`/`pushStreak` timing and the two reads that gate auto-level
  (`recentlyScrapedWall`, `wallLevelLockActive`) in `updateFlightPhysics()`; branch-junction entry
  grace (`branchJunctionEnteredAt`/`junctionAge`); target `destroyedAt` + `tickTargetRegen()`; sentry
  `destroyedAt` + `tickSentryRegen()`; sentry `lastSeenAt` (laser hit + AI tick), `lastFireAt`,
  `lingerUntil`, beam `createdAt`; laser fire cooldown (`shotNow`/`lastShotAt`).

  **Intentionally left on `performance.now()`/`Date.now()` — 28 + 6 sites, classified:**
  - *Audio*: spatial listener velocity sampling (`lastListenerSampleAt`) — doppler/panning smoothing
    against real device audio timing, not gameplay state.
  - *Cosmetic HUD flash* (8 sites: `shieldFlashUntil`, `shieldHitFlashUntil`, `hullFlashUntil`, set
    in `applyShieldWallDrain`/`applyShieldExplosiveDamage`/`applySentryDamageToPlayer`/
    `galagaApplyPlayerHit`, read in `updateShieldHud`/`updateHullHud`): purely a CSS box-shadow pulse
    duration on a HUD bar. Setter and reader are both consistently wall-clock (not a mix), gate no
    subsequent gameplay decision, and rendering itself is throttled/paused with the tab anyway.
  - *Render-only decorative animation phase* (5 sites): Galaga tractor-beam cone wobble and catch-ring
    pulse (`time`, `pulse` in `renderGalagaPhase` — distinct from the `progress` read next to them,
    which *was* converted), wall-texture scroll phase (`computeWallMotionState`), movement-streak
    phase (`renderMovementStreaks`), builder cursor marker pulse. All purely cosmetic wiggle with no
    gameplay deadline behind them.
  - *Input/UI timing* (12 sites): physical-key hold-grace and mobile thrust-latch bookkeeping
    (`lastKeyDown`, `restorePhysicalControlState`, `getLatchedMove`/`latchedMoveUntil`,
    `isKeyActive`'s grace check), builder-command repeat-debounce (`lastBuilderAt`/
    `lastBuilderCommandAt`), map/builder double-click gesture detection (`mapMouse.lastRmb`). These
    measure real human input duration/gesture timing, not simulation state; input is already cleared
    on suspend (`clearKeyboardState()`), so nothing here can silently advance a cooldown while paused.
  - *Render-loop timing plumbing* (2 sites): `renderEngineLoop`'s own `spatialNow`/`lastSpatialAt`
    wall-clock sample that the accumulator is built from, and the matching reset in
    `resumeSimulationOnFocusVisible()`. These must stay on real wall-clock time by construction —
    converting them would be circular (they're what `simClockMs` derives its step count *from*).
  - *ID generation* (6 `Date.now()` sites): map/target/sentry/portal ID salting
    (`` `${Date.now()}-${Math.random()...}` `` style). Not a timing concern at all.

- [~] **AD-B03 — Make collision subdivision distance-based.** Ship movement substeps and laser
  substeps are computed from actual per-tick travel distance vs.
  `AstralSimTiming.COLLISION_MAX_STEP_DISTANCE` (20 units, chosen below the smallest hit-test radius
  in the file, moved into `sim-timing.js` so the test below reads the same constant index.html uses
  rather than a second copy that could drift) via `distanceSubsteps()`, capped at 8 substeps, instead
  of `Math.ceil(frameScale)`. Regression-tested for boundary crossing, extreme-distance cap, and
  non-positive-distance safety, **plus** a test that computes the actual greatest reachable per-tick
  displacement in `updateFlightPhysics()`: keyboard and gamepad input stack additively (not
  exclusively) on each axis, so `forwardAmount`/`strafeAmount`/`liftAmount` each max out at 2 (±1
  keyboard + ±1 gamepad), against `currentSpeed`/`strafeSpeed` maxed at 14/7 (full boost, no wall
  drag) — `hypot(2*14, 2*7, 2*7)` ≈ 34.29 units/tick. That resolves to **2 substeps**, well under the
  8-substep cap (documented in the test: cap is not reached, ~21% of the cap's distance budget).
  Remaining: true swept tests (ray/capsule vs. thin target/portal geometry) were not implemented --
  substep count reduces tunneling risk but does not eliminate it the way a full sweep would. A
  browser smoke test with boost through a tightly-packed target/sentry cluster remains.

- [x] **AD-B04 — Pause cleanly on hidden tabs and focus loss.** `simulationSuspended` now stops the
  accumulator from advancing (`AstralSimTiming.frameSteps()` returns `{steps: 0, accumulatorSec: 0}`
  whenever suspended, unconditionally) while the tab is hidden or the window is blurred; on
  focus/visibility return, `resumeSimulationOnFocusVisible()` resets both the accumulator and
  `renderEngineLoop.lastSpatialAt` before simulation resumes, so no catch-up burst can occur.
  Combined with AD-B02 (every gameplay deadline now reads `simClockMs`, which only advances inside
  `tickSimulation()`), zero simulation steps for the whole suspension window is sufficient to prove
  portal transit cannot finish, Galaga states/attacks cannot expire or advance, targets/sentries
  cannot regenerate, weapon/sentry cooldowns cannot advance, and wall locks cannot expire while
  suspended — `tickSimulation()` is the only place any of that state changes. Regression-tested in
  `sim-timing.test.js`: 5 simulated seconds of suspension (300 frames at 60Hz) produce exactly 0
  steps and the accumulator stays at exactly 0 throughout; a representative post-resume frame then
  runs exactly 1 step, contrasted against a sanity check showing what a multi-step burst would look
  like without the reset. Existing transient-input clearing (`clearKeyboardState()`) and
  `updateEngineHum(0, false, 0)` on suspend are preserved/added.

  **Fixed in review (two issues):**
  1. `simulationSuspended` was hardcoded to `false` at declaration. A page opened already
     hidden/unfocused (background tab, unfocused window) never fires a `blur`/`visibilitychange`
     event to react to — those only fire on a *transition*, not on matching the initial state — so it
     would incorrectly start simulating despite never having been visible/focused. Now seeded from
     `document.visibilityState !== 'visible' || !document.hasFocus()`. Not independently testable in
     this Node harness (no DOM to read those properties from), but the mechanism it feeds — zero
     steps from frame 1 when starting suspended, with no dependency on a prior transition — is
     tested.
  2. The resume comment overclaimed that resetting `lastSpatialAt`/`accumulatorSec` "guarantees the
     next frame advances by exactly one step." It doesn't — it guarantees no catch-up burst; the
     actual step count on the literal next `requestAnimationFrame` still depends on real browser
     scheduling, which this fix cannot control. Comment corrected to state only what's actually
     guaranteed.

  A browser smoke test (switch tabs / alt-tab mid-flight during an active portal transit or Galaga
  phase, return, confirm no jump and no skipped state; separately, open the page in an already
  backgrounded/unfocused tab and confirm no simulation progress before it's first foregrounded)
  remains.
- [ ] **AD-B05 — Add a real pause/settings state.** It must pause simulation without corrupting map,
  Galaga, portal, input, audio, or save state.

## Batch C — measured render and geometry performance

- [ ] **AD-C01 — Consolidate visible-segment discovery.** Profile the separate visibility,
  WebGL draw-list, overlays, targets, sentries, and portal passes. Produce one per-frame visible set
  (with distance/depth data) for consumers rather than rescanning/sorting all segments.
- [ ] **AD-C02 — Add a spatial index.** Use a uniform grid, BVH, or similar structure for nearest-
  tunnel, containment, portal, target, sentry, and visibility queries. Rebuild incrementally or on a
  geometry revision, not per query.
- [ ] **AD-C03 — Cache topology and junction work by geometry revision.** Avoid repeated endpoint
  comparisons and branch-mouth reconstruction. Verify every builder mutation invalidates the cache.
- [ ] **AD-C04 — Cull/decimate the HUD map.** Do not draw the entire discovered map every frame at
  every zoom. Preserve the planned exploration/fog-of-war behavior.
- [ ] **AD-C05 — Remove avoidable hot-loop allocation.** Reuse draw lists, sets, scratch vectors,
  matrices, and job arrays after profiling identifies the highest garbage-collection sources.
- [ ] **AD-C06 — Move expensive procedural asset generation off the frame path.** Cache rock meshes
  and consider a worker/OffscreenCanvas only if measurements justify it.
- [ ] **AD-C07 — Make canvas/WebGL resize DPR-aware and dynamic.** Avoid reallocating buffers when
  CSS size and device-pixel ratio have not changed. Add an optional resolution scale for slower GPUs.
- [?] **AD-C08 — Audit door-texture GPU lifecycle.** Verify replacement and map reload delete or
  reuse WebGL textures; add counters before changing ownership.
- [?] **AD-C09 — Replace expensive math only where profiling proves useful.** `Math.hypot`, random
  sorting, and similar micro-optimizations are lower priority than scans, buffer uploads, and DOM work.

## Batch D — input consistency and generated help

- [ ] **AD-D01 — Define a declarative binding registry.** Store action, modes, chord, description,
  repeat policy, and visibility in one source. Drive dispatch and help from it incrementally rather
  than attempting a one-shot input rewrite.
- [ ] **AD-D02 — Generate full and compact help from the registry.** Include ordinary flight,
  minimap, grid/plane, route/spline, target-box, portal, sentry, chamber, helix, visual-mode, save/load,
  and ship-relocation controls. Keep developer/debug commands in a separate section.
- [ ] **AD-D03 — Clarify ambiguous wording.** In particular: route means N/spline construction;
  Shift+LMB edits/selects target boxes; Alt+Shift range-select is mode/context dependent; `.` toggles
  snap; `\\` locks the active plane; Space releases a snapped map camera to orbit; RMB opens context
  actions; portal wording must distinguish paired travel from a room doorway.
- [ ] **AD-D04 — Make repeat suppression action-based.** Verify comma, period, backslash, Space, V,
  and destructive builder operations do not repeat unintentionally while movement remains continuous.
- [ ] **AD-D05 — Reduce sticky-input grace/latch behavior.** Re-evaluate the desktop hold grace and
  long mobile latches after fixed-timestep input is stable. Add visible stuck-input recovery.
- [ ] **AD-D06 — Prefer `KeyboardEvent.code` for physical controls.** Keep text/name inputs based on
  `key`, and add remapping as a later user-facing layer.
- [ ] **AD-D07 — Consolidate global keyboard listeners.** Keep one authoritative handler path and
  explicitly test browser shortcuts, dialog focus, Alt menu behavior, fullscreen, and pointer lock.
- [ ] **AD-D08 — Add controller discovery and remapping UI.** Show axis/button activity and dead-zone
  calibration; do not require source edits for different controllers.

## Batch E — startup, storage, and browser lifecycle

- [ ] **AD-E01 — Render a loading shell before map bootstrap.** Add fetch timeouts and a visible
  fallback/retry for data-folder map and manifest loading rather than presenting a blank canvas.
- [ ] **AD-E02 — Make manifest loading observable.** Replace swallowed fire-and-forget failures with
  a state/result visible in the status UI and console once.
- [ ] **AD-E03 — Protect localStorage writes against stale snapshots.** Version named-map/player
  records, detect cross-tab updates through the `storage` event, and resolve conflicts deliberately.
- [ ] **AD-E04 — Make generated map IDs collision-resistant.** Use `crypto.randomUUID()` where
  available and retain import compatibility with old IDs.
- [ ] **AD-E05 — Track audio unlock as one promise/state machine.** Prevent overlapping resume calls
  and show muted/blocked status without repeated exceptions.
- [ ] **AD-E06 — Handle WebGL context loss/restoration.** Pause WebGL drawing, retain CPU-side map
  state, rebuild shaders/buffers/textures on restore, and allow the 2D/TRON fallback if restore fails.
- [ ] **AD-E07 — Define cache policy for game assets.** Version immutable art while fetching maps and
  manifests with an intentional freshness policy; do not apply `no-store` indiscriminately.
- [?] **AD-E08 — Evaluate IndexedDB for large user maps/assets.** Keep export/import as the portable
  recovery path; migrate only after measuring localStorage size and write costs.

## Batch F — map-data integrity and builder safety

- [ ] **AD-F01 — Introduce stable IDs and explicit connectivity.** Replace long-lived references to
  mutable array indexes with segment/point/portal/sentry IDs. Provide a versioned migration for old maps.
- [ ] **AD-F02 — Make multi-step geometry edits transactional.** Build and validate a candidate map,
  then commit it atomically; on failure restore segments, routes, selections, portals, sentries, caches,
  and dirty state together.
- [ ] **AD-F03 — Validate imports and saves structurally.** Check finite coordinates/radii, sane
  counts, valid references, portal pairs, sentry routes, texture IDs, and schema version before apply.
- [ ] **AD-F04 — Replace silent catches around important persistence.** Cosmetic preference failures
  may remain best-effort; map saves, imports, migrations, and identity changes must surface errors.
- [ ] **AD-F05 — Resolve the known ABC tunnel-edit artifact.** Reproduce with a small map, identify
  stale child geometry/topology/cache references, and add a deterministic regression fixture.
- [ ] **AD-F06 — Audit C-point 3D drag scale.** Prevent near-parallel ray/plane intersections from
  moving a spline control point thousands of units; clamp or fall back with a visible warning.

## Batch G — maintainability and automated regression coverage

- [ ] **AD-G01 — Split the monolith behind stable module boundaries.** Suggested order: math/types,
  input, persistence/schema, builder commands, simulation, Galaga, WebGL renderer, 2D renderer, HUD.
  Do this after Batch A and the first timing tests, not before.
- [ ] **AD-G02 — Separate simulation from rendering.** Rendering must consume state without mutating
  gameplay; this is prerequisite for deterministic replay and headless tests.
- [ ] **AD-G03 — Centralize tunable constants.** Group flight, collision, combat, Galaga difficulty,
  render quality, and input thresholds with units and documented ranges.
- [ ] **AD-G04 — Add pure-function tests.** Cover vector/basis math, spline sampling, containment,
  map migration/validation, serializer round-trips, input chord resolution, and Galaga state transitions.
- [ ] **AD-G05 — Add browser smoke tests.** Cover startup fallback, save/load/export, map edits,
  ship relocation, portal travel, Galaga death/respawn, context loss, and fatal-loop handling.
- [ ] **AD-G06 — Add a developer performance overlay.** Frame time percentiles, simulation steps,
  visible/total segments, draw calls, GPU mesh builds/cache hits, query counts, and spatial-index rebuilds.

## Batch H — playability, comfort, and future game systems

These are product features, not audit defects. Design and schedule them independently after the
correctness/performance foundation is stable.

- [ ] First-run flight and builder tutorials with contextual reminders.
- [ ] Settings for sensitivity, pitch inversion, FOV, motion/flash reduction, audio, HUD scale,
  reticle color/thickness, graphics quality, and controller remapping.
- [ ] Better damage direction, lock-on, collision, objective, branch, and low-hull feedback.
- [ ] Optional inertia/damping flight model; preserve an accessible arcade preset.
- [ ] Deterministic replay/ghost recording for bug reports and time trials.
- [ ] Builder undo/redo command history and crash-recovery journal.
- [ ] Exploration map reveal/fog of war rather than exposing the complete tunnel network.
- [ ] Level-loop progression: 30 tunnel levels, 30 space/exploration levels, and ten levels each of
  the original Galaga-like, maze-chase, and defender-like bonus games in the planned interleaving.
- [ ] Additional original bonus mode inspired by light-cycle territory/trail play, with map-specific
  boosts and hazards, after original art/mechanics avoid clone-level similarity.

## Corrected or non-actionable audit claims

- [x] Movement, lasers, Galaga entities, particles, and sentry beams have already received
  frame-rate scaling. A fixed timestep remains worthwhile, but the original blanket claim that all
  of them are raw frame-count motion is no longer current.
- [x] The source currently uses no `setTimeout()` or `setInterval()` game loops; the animation loop
  is `requestAnimationFrame()` based.
- [x] Sequential awaited bootstrap is not itself an async race. Its remaining problem is startup
  latency/failure handling (AD-E01), not concurrency corruption.
- [x] The duplicate window/document listeners are guarded by `astralDriftHandled`; consolidation is
  maintainability work (AD-D07), not currently proven double execution.
- [x] Shared key letters across mutually exclusive modes are not automatically defects. Only
  reachable ambiguity or wrong mode dispatch should be fixed.
- [x] `docs/CommandNotes.txt` documents the trading bot, not Astral Drift. Do not add game controls
  there; the generated in-game help and DecentClone design docs are the correct targets.

## Recommended ownership and sequence

1. **Codex: Batch A**, one reviewed commit after focused tests.
2. **Codex or one CLI agent: Batch B**, with a small timing test harness before changing behavior.
3. **One profiling-focused agent: Batch C**, beginning with measurements, not speculative rewrites.
4. **One input/docs agent: Batch D** after the timing foundation is stable.
5. Batches E and F can proceed independently only when they do not edit the same parts of
   `index.html`; otherwise serialize them.
6. Batch G is a staged refactor and should not be mixed with feature work from Batch H.

For cross-agent work, pass this file as the sole backlog and assign explicit task IDs. Require the
agent to stop after its assigned IDs, show tests and the exact diff, and avoid staging/committing until
reviewed. This prevents both audits from being reinterpreted differently on every handoff.

## CLI agent start prompt

Use this prefix when the local checkout may be behind or dirty:

> Work only on the assigned Astral Drift task IDs. First run `git fetch origin`. Do not base edits on
> the current local branch unless `DecentClone/index.html` matches `origin/main`. If it differs or the
> worktree is dirty, create a clean detached worktree from `origin/main` and work there. Do not create
> a branch. Do not edit, stage, commit, or push unrelated files. Read
> `DecentClone/ASTRAL_DRIFT_UNIFIED_AUDIT_TASKS.md`, implement only the assigned IDs, run
> `DecentClone/ScriptCheck.ps1` from the `DecentClone` directory, show the exact diff and test output,
> then stop without staging, committing, or pushing.
