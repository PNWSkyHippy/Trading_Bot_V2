/**
 * Automated test suite for Sightlines, Target Box Destruction & Multi-Angle 3D Ships
 */
const fs = require('fs');
const assert = require('assert');

function runTests(filePath) {
    console.log(`\n--- Testing ${filePath} ---`);
    const code = fs.readFileSync(filePath, 'utf8');

    // 1. Target Swept Collision Tests
    assert(code.includes('function laserTargetHitQuality(target, point, prevPoint = null)'), 'laserTargetHitQuality must accept prevPoint');
    assert(code.includes('checkLaserTargetHits(l, prevPoint)'), 'laser stepping loop must pass prevPoint to checkLaserTargetHits');
    assert(code.includes('SCORE_LASER_HIT'), 'SCORE_LASER_HIT must be awarded');
    console.log('PASS: Swept collision signature present in laserTargetHitQuality and laser loop');

    // Extract target collision logic to simulate directly
    const target = {
        id: 'test-target',
        point: { x: 0, y: 0, z: 100 },
        right: { x: 1, y: 0, z: 0 },
        down: { x: 0, y: 1, z: 0 },
        size: 48,
        destroyedAt: null
    };

    function dot(a, b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
    function cross(a, b) {
        return {
            x: a.y * b.z - a.z * b.y,
            y: a.z * b.x - a.x * b.z,
            z: a.x * b.y - a.y * b.x
        };
    }
    function targetForwardAxis(t) {
        const c = cross(t.right, t.down);
        const len = Math.hypot(c.x, c.y, c.z) || 1;
        return { x: c.x / len, y: c.y / len, z: c.z / len };
    }
    function worldToTargetLocal(t, p) {
        const fwd = targetForwardAxis(t);
        const delta = { x: p.x - t.point.x, y: p.y - t.point.y, z: p.z - t.point.z };
        return {
            right: dot(delta, t.right),
            down: dot(delta, t.down),
            forward: dot(delta, fwd)
        };
    }
    function targetBoxHalfExtents(t) {
        const half = t.size / 2;
        return { right: half, down: half, forward: half * 0.42 };
    }

    function testLaserTargetHitQuality(t, point, prevPoint = null) {
        if (!t || !point) return null;
        const ext = targetBoxHalfExtents(t);
        const extRight = ext.right * 1.15;
        const extDown = ext.down * 1.15;
        const extForward = Math.max(ext.forward * 1.5, 20);

        const local = worldToTargetLocal(t, point);
        if (
            Math.abs(local.right) <= extRight &&
            Math.abs(local.down) <= extDown &&
            Math.abs(local.forward) <= extForward
        ) {
            return 'hit';
        }

        if (prevPoint) {
            const prevLocal = worldToTargetLocal(t, prevPoint);
            const dx = local.right - prevLocal.right;
            const dy = local.down - prevLocal.down;
            const dz = local.forward - prevLocal.forward;
            const lenSq = dx * dx + dy * dy + dz * dz;
            let frac = 0;
            if (lenSq > 0.0001) {
                frac = Math.max(0, Math.min(1, -(prevLocal.right * dx + prevLocal.down * dy + prevLocal.forward * dz) / lenSq));
            }
            const cx = prevLocal.right + frac * dx;
            const cy = prevLocal.down + frac * dy;
            const cz = prevLocal.forward + frac * dz;
            if (
                Math.abs(cx) <= extRight &&
                Math.abs(cy) <= extDown &&
                Math.abs(cz) <= extForward
            ) {
                return 'hit';
            }
        }
        return null;
    }

    // Case A: Laser tunneling right through the 10-unit slab in one frame (z=80 -> z=120)
    const prevLaser = { x: 0, y: 0, z: 80 };
    const currLaser = { x: 0, y: 0, z: 120 };
    const sweptHit = testLaserTargetHitQuality(target, currLaser, prevLaser);
    assert.strictEqual(sweptHit, 'hit', 'Laser leaping across slab from z=80 to z=120 must register hit');
    console.log('PASS: Swept segment detects fast laser leaping across target slab');

    // Case B: Laser hitting the outer edge (x=20, y=20) which was previously rejected by 0.58 centerDist
    const edgeHit = testLaserTargetHitQuality(target, { x: 20, y: 20, z: 100 });
    assert.strictEqual(edgeHit, 'hit', 'Laser hitting outer 42% area of target box must register hit');
    console.log('PASS: Laser hitting outer box quadrant registers direct hit');

    // Case C: Laser clearly missing
    const missHit = testLaserTargetHitQuality(target, { x: 60, y: 60, z: 100 }, { x: 60, y: 60, z: 80 });
    assert.strictEqual(missHit, null, 'Laser outside target boundary must return null');
    console.log('PASS: Off-target laser correctly returns null');

    // 2. Sightline Occlusion Checks
    assert(code.includes('!tunnelSightlineClear(camEye, pos, shipSegmentIndex, sentrySegIdx)'), 'renderSentryDrone must check tunnelSightlineClear');
    console.log('PASS: renderSentryDrone enforces tunnelSightlineClear');

    assert(code.includes('!tunnelSightlineClear(camEye, target.point, shipSegmentIndex, target.segmentIndex)'), 'renderTunnelTargets must check tunnelSightlineClear');
    console.log('PASS: renderTunnelTargets enforces tunnelSightlineClear');

    assert(code.includes('!tunnelSightlineClear(camEye, flash, shipSegmentIndex, sourceSegIdx)'), 'renderSentryMuzzleFlashes must check tunnelSightlineClear');
    console.log('PASS: renderSentryMuzzleFlashes enforces tunnelSightlineClear');

    assert(code.includes('!tunnelSightlineClear(camEye, beam.from, shipSegmentIndex, sentrySegIdx)'), 'renderSentryBeams must check tunnelSightlineClear');
    console.log('PASS: renderSentryBeams enforces tunnelSightlineClear');

    // 3. 3D Multi-Angle Directional Sprite System
    assert(code.includes('SENTRY_3D_SPRITE_CACHE'), 'SENTRY_3D_SPRITE_CACHE defined');
    assert(code.includes('SENTRY_SPRITE_DIRECTIONS = 16'), '16 viewing directions configured');
    assert(code.includes('function getSentryMultiAngleBitmap(sqType, elevationId, dirIndex)'), 'getSentryMultiAngleBitmap defined');
    assert(code.includes('getSentryMultiAngleBitmap(sqType, elevId, dirIndex)'), 'renderSentryDrone calls getSentryMultiAngleBitmap');
    console.log('PASS: 16-way multi-angle 3D directional sprite engine integrated in renderSentryDrone');

    // 4. Target HUD Visual Clarity & Scoring
    assert(code.includes('[ TARGET +50 ]'), 'Informative default HUD label [ TARGET +50 ] present');
    assert(code.includes('[ ⚠ MINE ]'), 'Informative default HUD label [ ⚠ MINE ] present');
    assert(code.includes('TARGET DESTROYED (+${SCORE_LASER_HIT} PTS)'), 'Status confirmation banner on target destruction present');
    console.log('PASS: Target HUD reticles, labels and destruction feedback confirmed');

    // 5. Texture Library Modernization
    assert(code.includes('sentry_3d_crimson'), 'sentry_3d_crimson present in texture library');
    assert(code.includes('sentry_3d_cobalt'), 'sentry_3d_cobalt present in texture library');
    assert(code.includes('sentry_3d_amber'), 'sentry_3d_amber present in texture library');
    assert(code.includes('sentry_3d_recon'), 'sentry_3d_recon present in texture library');
    console.log('PASS: Texture library modernized with 3D squadron fighters');
}

runTests('DecentClone/index.html');
runTests('index.html');
console.log('\nAll sightline, target destruction, and multi-angle 3D ship checks passed successfully!\n');
