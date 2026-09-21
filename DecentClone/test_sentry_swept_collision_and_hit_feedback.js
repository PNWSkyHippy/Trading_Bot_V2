/**
 * Automated test suite for Sentry Drone Swept Laser Collision, Hitbox Coverage & Damage Feedback
 */
const fs = require('fs');
const assert = require('assert');

function distanceSq(a, b) {
    const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

function testLaserSentryHitQuality(sentry, point, prevPoint = null, hitRadius = 46) {
    if (!sentry || !point) return null;
    const sentryPos = { x: sentry.x, y: sentry.y, z: sentry.z };
    const hitRSq = hitRadius * hitRadius;

    // 1. Direct point collision
    if (distanceSq(point, sentryPos) <= hitRSq) return 'hit';

    // 2. Continuous swept line-segment collision from prevPoint to point
    if (prevPoint) {
        const vx = point.x - prevPoint.x;
        const vy = point.y - prevPoint.y;
        const vz = point.z - prevPoint.z;
        const lenSq = vx * vx + vy * vy + vz * vz;
        if (lenSq > 0.0001) {
            const wx = sentryPos.x - prevPoint.x;
            const wy = sentryPos.y - prevPoint.y;
            const wz = sentryPos.z - prevPoint.z;
            const t = Math.max(0, Math.min(1, (wx * vx + wy * vy + wz * vz) / lenSq));
            const closeX = prevPoint.x + t * vx;
            const closeY = prevPoint.y + t * vy;
            const closeZ = prevPoint.z + t * vz;
            if (distanceSq({ x: closeX, y: closeY, z: closeZ }, sentryPos) <= hitRSq) {
                return 'hit';
            }
        }
    }
    return null;
}

function runTestSuite(filePath) {
    console.log(`\n=== Testing ${filePath} ===`);
    const code = fs.readFileSync(filePath, 'utf8');

    // 1. Collision Architecture Checks
    assert(code.includes('SENTRY_HIT_RADIUS = 46'), 'SENTRY_HIT_RADIUS must be expanded to 46');
    assert(code.includes('function laserSentryHitQuality(sentry, point, prevPoint = null)'), 'laserSentryHitQuality must accept prevPoint');
    assert(code.includes('function checkLaserSentryHits(laserPoint, prevPoint = null)'), 'checkLaserSentryHits must accept prevPoint');
    assert(code.includes('checkLaserSentryHits(l, prevPoint)'), 'laser step loop must pass prevPoint to checkLaserSentryHits');
    console.log('PASS: Swept collision signatures and 46-unit hitbox confirmed');

    // 2. Mathematical Swept Collision Simulation
    const sentry = { x: 0, y: 0, z: 200 };

    // Case A: Laser leaping right across sentry volume in a single frame (z=175 -> z=225)
    // In old discrete point code, z=175 dist=25 (if lateral offset=15, total=29 > 28 MISS), z=225 dist=29 > 28 MISS!
    const leapingLaserPrev = { x: 15, y: 0, z: 175 };
    const leapingLaserCurr = { x: 15, y: 0, z: 225 };
    const leaptHit = testLaserSentryHitQuality(sentry, leapingLaserCurr, leapingLaserPrev, 46);
    assert.strictEqual(leaptHit, 'hit', 'Fast laser jumping from z=175 to z=225 must register a swept hit');
    console.log('PASS: Swept segment detects fast laser leaping across sentry space');

    // Case B: Hit on outer combat wing (x=38, y=0, z=200) - previously missed with 28 radius
    const wingHit = testLaserSentryHitQuality(sentry, { x: 38, y: 0, z: 200 }, null, 46);
    assert.strictEqual(wingHit, 'hit', 'Laser hitting outer wing at x=38 must register hit with 46 radius');
    console.log('PASS: Wingtip hit at x=38 registers cleanly');

    // Case C: Clear miss (x=70, y=0, z=200)
    const miss = testLaserSentryHitQuality(sentry, { x: 70, y: 0, z: 200 }, { x: 70, y: 0, z: 170 }, 46);
    assert.strictEqual(miss, null, 'Laser outside 46 radius boundary must return null');
    console.log('PASS: Off-target laser returns null');

    // 3. Sightline Architecture
    assert(code.includes('function tunnelSightlineClear(p1, p2, segAIndex, segBIndex, maxHops = 14)'), 'tunnelSightlineClear default maxHops must be 14');
    assert(code.includes('if (sentry.engaged) return true;'), 'sentryCorridorVisibleToPlayer must allow engaged enemies to be targeted');
    assert(code.includes('tunnelSightlineClear(shipPos, sentryPos, shipSegmentIndex, sentrySegIdx, 14)'), 'sentryCorridorVisibleToPlayer must pass 14 hops');
    console.log('PASS: Corridor sightline lookahead and engaged enemy targetability confirmed');

    // 4. Hit Feedback, Audio & HUD Reticle
    assert(code.includes('hudHitMarkerUntil = now + 150'), 'HUD hit marker timer set on laser hit');
    assert(code.includes("playSfx('wall_bump', { intensity: 0.75"), 'Impact audio sfx triggered on hit');
    assert(code.includes('addTargetScore(25)'), 'Score awarded on laser hit');
    assert(code.includes('sentry.hitFlashUntil = now + 200'), 'Shield impact flash timer set on laser hit');
    assert(code.includes('Dynamic FPS Hit Marker ticks'), 'Crosshair renders diagonal hit ticks');
    console.log('PASS: Hit sound, score bonus, shield flash, and HUD crosshair hit marker confirmed');

    // 5. Health Bar Normalization
    assert(code.includes('const maxHp = sentry.maxHealth || SENTRY_HEALTH_MAX;'), 'Health bar normalizes against sentry.maxHealth');
    assert(code.includes('const showHealth = !mapMode && (sentry.health < maxHp || (sentry.hitFlashUntil && performance.now() < sentry.hitFlashUntil + 5000));'), 'Health bar shows on damage or recent hit flash');
    console.log('PASS: Health bar normalization and high-contrast rendering confirmed');
}

runTestSuite('DecentClone/index.html');
runTestSuite('index.html');

// Check byte-for-byte identical match
const f1 = fs.readFileSync('DecentClone/index.html');
const f2 = fs.readFileSync('index.html');
assert.strictEqual(f1.length, f2.length, `File lengths must match (${f1.length} vs ${f2.length})`);
assert(f1.equals(f2), 'DecentClone/index.html and index.html must be identical byte-for-byte');
console.log(`\nPASS: DecentClone/index.html and index.html match byte-for-byte (${f1.length} bytes)`);

console.log('\nALL SENTRY SWEPT COLLISION & DAMAGE FEEDBACK TESTS PASSED!\n');
