'use strict';
// Deterministic regression tests for AD-B01/AD-B02/AD-B03/AD-B04 timing helpers.
// Plain Node, no dependencies: `node DecentClone/tests/sim-timing.test.js`
const assert = require('assert');
const path = require('path');
const AstralSimTiming = require(path.join(__dirname, '..', 'sim-timing.js'));
const {
    advanceAccumulator,
    frameSteps,
    distanceSubsteps,
    SIMULATION_STEP_SEC,
    SIMULATION_MAX_CATCHUP_STEPS,
    COLLISION_MAX_STEP_DISTANCE
} = AstralSimTiming;

// Exact integer frame counts for a 2-second window at each rate, rather than
// an "elapsed < duration" floating-point loop -- accumulating a float
// duration counter across many frames is itself a source of drift and can
// silently run one frame short/long, which would undermine a test whose
// whole point is exactness.
const DURATION_SEC = 2;
const FRAME_COUNTS = { 30: 60, 60: 120, 144: 288 };

function stepsOverExactFrames(hz, frameCount) {
    const dt = 1 / hz;
    let acc = 0;
    let steps = 0;
    for (let i = 0; i < frameCount; i++) {
        const result = advanceAccumulator(acc, dt);
        acc = result.accumulatorSec;
        steps += result.steps;
    }
    return steps;
}

// 1. Frame-rate independence, exact: 2 seconds of real time must produce
// exactly 120 fixed steps (SIMULATION_STEP_SEC = 1/60) whether it's sliced
// into 60, 120, or 288 frames. This is the actual defect AD-B01 exists to
// fix (behavior used to change across refresh rates) -- and it's a hard
// equality, not an approximation, because float dust from an accumulator
// that never exactly divides (e.g. 1/144 against 1/60) is exactly the kind
// of bug this feature has to not have.
{
    for (const hz of [30, 60, 144]) {
        const steps = stepsOverExactFrames(hz, FRAME_COUNTS[hz]);
        assert.strictEqual(steps, 120, `expected exactly 120 steps at ${hz}Hz over ${DURATION_SEC}s, got ${steps}`);
    }
    console.log('PASS: 30/60/144Hz each produce EXACTLY 120 simulation steps over 2s (60/120/288 frames respectively)');
}

// 2. Application-style startup, exact: renderEngineLoop() seeds
// accumulatorSec to 0 (not SIMULATION_STEP_SEC) on its first call, because
// that first call always measures a 0 rawFrameDt (lastSpatialAt is set to
// spatialNow on the same call that seeds it). Seeding with a whole step
// instead of 0 was a real bug caught in review: it fired one unearned
// simulation step before any real time had elapsed, so a zero-delta first
// render followed by exactly 120 real frames at a steady 60Hz produced 121
// steps instead of 120. This test models that exact startup sequence.
{
    let acc = 0; // correct seed
    let steps = 0;

    // First render call: rawFrameDt is always 0 here (see above).
    const first = advanceAccumulator(acc, 0);
    acc = first.accumulatorSec;
    steps += first.steps;
    assert.strictEqual(first.steps, 0, `expected 0 steps on the zero-delta first render, got ${first.steps} (a seeded/preloaded accumulator would leak a step here)`);

    // Then 120 real frames at a steady 60Hz.
    for (let i = 0; i < 120; i++) {
        const result = advanceAccumulator(acc, 1 / 60);
        acc = result.accumulatorSec;
        steps += result.steps;
    }
    assert.strictEqual(steps, 120, `expected exactly 120 steps for zero-delta-first-render + 120 frames at 60Hz, got ${steps}`);
    console.log('PASS: application-style startup (zero-delta first render + 120 frames at 60Hz) produces EXACTLY 120 steps, not 121 -- confirms the accumulator is not pre-seeded with an unearned step');
}

// 3. A long stall is clamped and cannot demand an unbounded catch-up burst,
// AND the frame immediately after the stall must not inherit the dropped
// backlog -- i.e. dropping backlog at the cap must actually zero the
// accumulator, not just report a step count while quietly keeping leftover
// time around to dump into the next frame.
{
    const stalled = advanceAccumulator(0, 5); // 5 second stall
    assert.strictEqual(stalled.steps, SIMULATION_MAX_CATCHUP_STEPS, `expected the stall to be capped at exactly ${SIMULATION_MAX_CATCHUP_STEPS} steps, got ${stalled.steps}`);
    assert.strictEqual(stalled.accumulatorSec, 0, 'dropped backlog must leave the accumulator at exactly 0, not a leftover fraction');

    const nextNormalFrame = advanceAccumulator(stalled.accumulatorSec, 1 / 60);
    assert.strictEqual(nextNormalFrame.steps, 1, `expected exactly 1 step on the frame right after the stall, got ${nextNormalFrame.steps} (a value > 1 would mean the dropped backlog was secretly retained)`);
    console.log(`PASS: 5s stall capped at exactly ${stalled.steps} steps with accumulator zeroed; the very next normal-sized frame runs exactly 1 step, proving no discarded backlog carried over`);
}

// 4. AD-B04 proof (suspended mid-session): while suspended, no number of
// elapsed real seconds -- tested here at 60Hz framing for a full 5 simulated
// seconds of hidden/unfocused time -- produces a single simulation step.
// Since every gameplay deadline in index.html (portal transit, Galaga
// phase/attack timers, target and sentry regeneration, weapon/sentry
// cooldowns, wall locks) reads simClockMs, and simClockMs is only ever
// advanced inside tickSimulation(), and tickSimulation() only ever runs
// `advance.steps` times per frame, zero steps for the entire suspension
// window is sufficient to prove none of those systems can progress, expire,
// or complete while suspended.
{
    let acc = 0;
    let totalSteps = 0;
    const suspendedFrames = 5 * 60; // 5 seconds at a 60Hz render rate
    for (let i = 0; i < suspendedFrames; i++) {
        const result = frameSteps(acc, 1 / 60, true);
        acc = result.accumulatorSec;
        totalSteps += result.steps;
    }
    assert.strictEqual(totalSteps, 0, `expected 0 simulation steps across 5 suspended seconds, got ${totalSteps}`);
    assert.strictEqual(acc, 0, 'a suspended accumulator must stay at 0, not silently bank time for later');

    // Resume: what the accumulator reset actually guarantees is "no catch-up
    // burst", not a specific step count on the literal next
    // requestAnimationFrame (that depends on real browser scheduling, which
    // this pure-function test cannot observe). Modeled here with a
    // representative normal-sized frame delta (1/60s) to show the contrast
    // with the alternative of *not* resetting, which would instead report a
    // multi-step burst covering the whole suspended duration.
    const resumedWithReset = frameSteps(0, 1 / 60, false);
    assert.strictEqual(resumedWithReset.steps, 1, `expected exactly 1 step for a normal-sized frame right after a reset resume, got ${resumedWithReset.steps}`);
    // Sanity check / contrast: if the 5 suspended seconds had instead been
    // left sitting in the accumulator (no reset), the next frame would burst
    // multiple catch-up steps instead of the single step above.
    const resumedWithoutReset = advanceAccumulator(5, 1 / 60);
    assert.ok(resumedWithoutReset.steps > 1, 'sanity check: without the reset, a burst covering the suspended duration would occur');
    console.log('PASS: 5 simulated seconds of suspension produce exactly 0 simulation steps (portal transit/Galaga/regen/cooldowns/wall-locks all frozen); a representative post-resume frame runs exactly 1 step (not a multi-second burst) once the accumulator has been reset');
}

// 5. AD-B04 proof (suspended from page load): a page opened already
// hidden/unfocused gets no blur/visibilitychange transition event to react
// to -- those only fire on a *state change*, not on matching the initial
// state. index.html now seeds simulationSuspended from
// `document.visibilityState !== 'visible' || !document.hasFocus()` instead
// of a hardcoded false specifically so this case is covered from the very
// first frame, before any event has fired. This is not independently
// testable here (no DOM in this Node harness to read
// document.visibilityState/hasFocus() from), but the mechanism it feeds --
// "suspended produces zero steps starting on frame 1, with no dependency on
// a prior transition" -- is directly testable and is what actually matters:
// if the seed is correct, frame 1 already sees suspended=true.
{
    const frame1 = frameSteps(0, 0, true);
    assert.strictEqual(frame1.steps, 0, 'expected 0 steps on the very first frame when starting already suspended');
    assert.strictEqual(frame1.accumulatorSec, 0, 'expected accumulator to stay 0 on the very first frame when starting already suspended');
    console.log('PASS: starting already suspended (page loaded hidden/unfocused) produces 0 steps from frame 1, with no dependency on a prior blur/visibilitychange transition');
}

// 6. distanceSubsteps: short distance needs only one substep.
{
    assert.strictEqual(distanceSubsteps(10, 20), 1);
    console.log('PASS: distance below max-step returns 1 substep');
}

// 7. distanceSubsteps: exactly at the boundary vs. just over it.
{
    assert.strictEqual(distanceSubsteps(20, 20), 1);
    assert.strictEqual(distanceSubsteps(20.001, 20), 2);
    console.log('PASS: crossing the max-step boundary forces an additional substep');
}

// 8. distanceSubsteps: extreme distance (e.g. a future speed-tuning change)
// is capped, not unbounded -- this is the AD-B03 requirement that substep
// count track actual distance rather than a frame-count assumption.
{
    assert.strictEqual(distanceSubsteps(10000, 20, 8), 8);
    console.log('PASS: extreme per-tick distance is capped at maxSubsteps, not unbounded');
}

// 9. distanceSubsteps: non-positive distance never divides by zero or
// returns fewer than 1 substep.
{
    assert.strictEqual(distanceSubsteps(0, 20), 1);
    assert.strictEqual(distanceSubsteps(-5, 20), 1);
    console.log('PASS: non-positive distance safely returns 1 substep');
}

// 10. AD-B03 proof: the greatest combined ship displacement actually
// reachable in one fixed tick in index.html's updateFlightPhysics(), and
// whether it reaches the 8-substep cap.
//
// From index.html (updateFlightPhysics):
//   forwardAmount = keyForward + gamepad.forward   (each in [-1, 1] --
//     keyboard is a boolean +-1, gamepad.forward = rightTrigger - leftTrigger
//     with each trigger in [0, 1] per the Gamepad API and buttonValue())
//   strafeAmount  = keyStrafe  + gamepad.strafe    (same reasoning, dualStick
//     leftX after applyDeadzone(), which rescales but never exceeds +-1)
//   liftAmount    = keyLift    + gamepad.lift      (same)
//   currentSpeed  = (boosting ? 14 : 4) * wallDrag   -- max 14 (wallDrag<=1)
//   strafeSpeed   = (boosting ? 7  : 3) * wallDrag   -- max 7
// Keyboard and gamepad are additive, not exclusive (both can be held at
// once), so each of forwardAmount/strafeAmount/liftAmount maxes out at 2.
// tickDistance = hypot(forwardAmount*currentSpeed, strafeAmount*strafeSpeed,
//   liftAmount*strafeSpeed) * frameScale, with frameScale always exactly 1
// under the fixed step (AD-B01).
{
    const maxForwardComponent = 2 * 14;
    const maxStrafeComponent = 2 * 7;
    const maxLiftComponent = 2 * 7;
    const maxTickDistance = Math.hypot(maxForwardComponent, maxStrafeComponent, maxLiftComponent);
    const steps = distanceSubsteps(maxTickDistance, COLLISION_MAX_STEP_DISTANCE, 8);

    assert.ok(steps < 8, `expected the real maximum reachable per-tick distance to stay under the 8-substep cap, got ${steps} steps for ${maxTickDistance.toFixed(2)} units`);
    assert.strictEqual(steps, 2);
    const marginUnits = 8 * COLLISION_MAX_STEP_DISTANCE - maxTickDistance;
    console.log(`PASS: max reachable per-tick displacement (keyboard+gamepad stacked, full boost, no wall drag) is ${maxTickDistance.toFixed(2)} units -> ${steps} substeps. The 8-substep cap is NOT reached; margin to the cap is ${marginUnits.toFixed(1)} units (would need ~${(maxTickDistance / (8 * COLLISION_MAX_STEP_DISTANCE) * 100).toFixed(0)}% of the cap's distance budget).`);
}

console.log('\nAll sim-timing tests passed.');
