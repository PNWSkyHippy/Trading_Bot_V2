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

- [~] **AD-B01 — Introduce a fixed simulation timestep.** Movement, projectiles, Galaga actors,
  particles, and sentry-beam lifetimes now use `frameScale`, so the old wholly frame-dependent claim
  is stale. The current frame cap can still discard long stalls and the code mixes elapsed-time and
  scaled-frame clocks. Use an accumulator with bounded catch-up steps; interpolate only rendering.
- [ ] **AD-B02 — Use one monotonic simulation clock.** Convert remaining combat cooldowns, regen,
  state deadlines, and animation lifetimes from mixed `Date.now()`, `performance.now()`, and implicit
  frames to explicit milliseconds or simulation seconds.
- [ ] **AD-B03 — Make collision subdivision distance-based.** Current substeps derive from
  `frameScale`, not actual world distance traveled. Subdivide using velocity/distance and tunnel
  radius, then add swept tests for thin target/portal geometry.
- [ ] **AD-B04 — Pause cleanly on hidden tabs and focus loss.** Stop accumulating simulation time,
  clear transient input, and reset the clock on resume so returning to the tab cannot jump the ship.
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
