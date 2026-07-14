/*
 * Pure, DOM-free simulation timing helpers for Astral Drift.
 *
 * Kept in its own file (rather than inline in index.html) specifically so it
 * can be loaded both by the browser (<script src="sim-timing.js">) and by a
 * plain Node test runner with no build step and no DOM/WebGL dependencies.
 */
(function (root, factory) {
    var api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.AstralSimTiming = api;
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // One fixed simulation step. Everything gameplay-relevant (movement,
    // lasers, sentries, particles, Galaga) advances in units of this step,
    // not in units of however long the last rendered frame happened to take.
    var SIMULATION_STEP_SEC = 1 / 60;

    // A single rendered frame can never demand more than this much simulated
    // time, no matter how long it actually took (tab switch, breakpoint,
    // dropped frame). This is what keeps a stall from becoming a lag spiral.
    var SIMULATION_MAX_FRAME_SEC = 0.25;

    // Upper bound on how many fixed steps one rendered frame may run to
    // catch up. If a stall is long enough that even this isn't enough,
    // simulation time is intentionally dropped (falls behind) rather than
    // bursting an unbounded number of steps into a single frame.
    var SIMULATION_MAX_CATCHUP_STEPS = 8;

    // Smallest reliable hit-test radius in the game (sentries/fighters are
    // ~28-30 units). No single collision substep may cover more distance
    // than this, or it can step clean over a target in one tick (AD-B03).
    var COLLISION_MAX_STEP_DISTANCE = 20;

    // Repeated float addition/subtraction of the same step size can leave a
    // few ULPs of dust in the accumulator (e.g. 1/144 has no exact binary
    // fraction relationship to 1/60). Without this tolerance that dust can
    // occasionally cost or gain a whole step over many frames -- e.g. 288
    // frames at 144Hz over 2 seconds landing on 119 or 121 fixed steps
    // instead of exactly 120. The tolerance is many orders of magnitude
    // below one actual simulation step, so it never masks a real dropped
    // frame, only float noise.
    var ACCUMULATOR_EPSILON_SEC = 1e-9;

    /**
     * Advance a fixed-step accumulator by one rendered frame's wall-clock
     * delta. Returns how many fixed simulation steps should run this frame
     * and the accumulator's new value.
     *
     * @param {number} accumulatorSec - leftover simulated time from previous frames
     * @param {number} frameDtSec - wall-clock time since the previous rendered frame
     * @param {{stepSec?: number, maxFrameSec?: number, maxCatchupSteps?: number}} [options]
     */
    function advanceAccumulator(accumulatorSec, frameDtSec, options) {
        var stepSec = (options && options.stepSec) || SIMULATION_STEP_SEC;
        var maxFrameSec = (options && options.maxFrameSec) || SIMULATION_MAX_FRAME_SEC;
        var maxSteps = (options && options.maxCatchupSteps) || SIMULATION_MAX_CATCHUP_STEPS;

        var clampedDt = Math.max(0, Math.min(maxFrameSec, frameDtSec));
        var acc = (accumulatorSec || 0) + clampedDt;

        var steps = 0;
        while (acc >= stepSec - ACCUMULATOR_EPSILON_SEC && steps < maxSteps) {
            acc -= stepSec;
            steps += 1;
        }
        // Hit the catch-up cap: drop the remaining backlog instead of letting
        // it balloon and dump a burst of steps into some later frame. The
        // very next frame must not inherit this backlog.
        if (steps >= maxSteps && acc >= stepSec - ACCUMULATOR_EPSILON_SEC) {
            acc = 0;
        }
        // Never report a negative accumulator (possible by a few ULPs after
        // the epsilon-tolerant subtraction above).
        if (acc < 0) acc = 0;
        return { steps: steps, accumulatorSec: acc };
    }

    /**
     * One rendered frame's worth of the suspend/advance decision used by
     * renderEngineLoop(). Extracted as a pure function specifically so
     * "suspended for N seconds runs zero simulation steps" is a real,
     * testable claim (AD-B04) rather than something only checkable by
     * reading the loop.
     */
    function frameSteps(accumulatorSec, frameDtSec, suspended, options) {
        if (suspended) {
            return { steps: 0, accumulatorSec: 0 };
        }
        return advanceAccumulator(accumulatorSec, frameDtSec, options);
    }

    /**
     * How many equal substeps a single fixed simulation tick should be split
     * into so that no substep covers more than maxStepDistance. Distance
     * based (not frame-time based), so it stays correct once dt is fixed and
     * automatically compensates if speed tuning changes later.
     */
    function distanceSubsteps(distancePerTick, maxStepDistance, maxSubsteps) {
        var cap = maxSubsteps || 8;
        if (!(distancePerTick > 0) || !(maxStepDistance > 0)) return 1;
        return Math.max(1, Math.min(cap, Math.ceil(distancePerTick / maxStepDistance)));
    }

    return {
        SIMULATION_STEP_SEC: SIMULATION_STEP_SEC,
        SIMULATION_MAX_FRAME_SEC: SIMULATION_MAX_FRAME_SEC,
        SIMULATION_MAX_CATCHUP_STEPS: SIMULATION_MAX_CATCHUP_STEPS,
        COLLISION_MAX_STEP_DISTANCE: COLLISION_MAX_STEP_DISTANCE,
        advanceAccumulator: advanceAccumulator,
        frameSteps: frameSteps,
        distanceSubsteps: distanceSubsteps
    };
});
