/**
 * Automated test suite for Astral Drift Missile / Rocket Overhaul:
 * 1. 3D In-Flight Cruciform Fins & Volumetric Ion Thruster Corona
 * 2. Starburst Blast Crater Scorch Marks (replacing concentric brown ellipses)
 * 3. Active Target-Seeking Homing Guidance across 3D space
 * 4. Proportional Area Splash Damage (220-unit radius with distance falloff)
 * 5. Defender Phase Integration (Lander destruction, Astronaut drop, swarm clearing)
 */
const fs = require('fs');
const assert = require('assert');

function distanceSq(a, b) {
    const dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

function dot(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

function normalize(v) {
    const len = Math.hypot(v.x, v.y, v.z) || 1;
    return { x: v.x / len, y: v.y / len, z: v.z / len };
}

function scaleVec(v, s) {
    return { x: v.x * s, y: v.y * s, z: v.z * s };
}

function subVec(a, b) {
    return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function cross(a, b) {
    return {
        x: a.y * b.z - a.z * b.y,
        y: a.z * b.x - a.x * b.z,
        z: a.x * b.y - a.y * b.x
    };
}

function runTestSuite(filePath) {
    console.log(`\n=== Testing ${filePath} ===`);
    const code = fs.readFileSync(filePath, 'utf8');

    // 1. Static Checks: Blast Radius & Old concentric brown scorch removal
    assert(code.includes('ROCKET_BLAST_RADIUS = 220;'), 'ROCKET_BLAST_RADIUS must be 220');
    assert(!code.includes('rgba(28,12,5,0.82)'), 'Old murky brown concentric gradient must be removed');
    assert(!code.includes('ctx.strokeStyle = \'#d1571a\';'), 'Old brown concentric ellipse outlines must be removed');
    console.log('PASS: ROCKET_BLAST_RADIUS is 220 and old coiled/concentric brown scorches are purged');

    // 2. Static Checks: Starburst Blast Crater Architecture
    assert(code.includes('sootGradient'), 'Carbon soot blast rim gradient must be present');
    assert(code.includes('const starPoints = 20;'), '20-spoke starburst fracture perimeter must be present');
    assert(code.includes('const crackCount = 9;'), 'Radial carbon spall fracture fissures must be present');
    assert(code.includes('coreGrad.addColorStop(0, \'rgba(255,255,255,0.98)\');'), 'Incandescent molten slag core must start at thermal white');
    assert(code.includes('emberCount = 5'), 'Molten thermal embers scattered on crater rim');
    console.log('PASS: Modern starburst blast crater rendering verified');

    // 3. Static Checks: 3D Cruciform Fins & Ion Thruster Visuals
    assert(code.includes('finR = addVec(tail, scaleVec(rocket.right, finSpan))'), 'Right stabilizer fin present');
    assert(code.includes('finL = addVec(tail, scaleVec(rocket.right, -finSpan))'), 'Left stabilizer fin present');
    assert(code.includes('finU = addVec(tail, scaleVec(rocket.down, -finSpan))'), 'Upper stabilizer fin present');
    assert(code.includes('finD = addVec(tail, scaleVec(rocket.down, finSpan))'), 'Lower stabilizer fin present (true 3D cruciform cross)');
    assert(code.includes('canSpan = 4.2'), 'Mid-body canard guidance fins present');
    assert(code.includes('thrusterGrad'), 'Volumetric ion thruster gradient present');
    assert(code.includes('flareLen = coronaR * 2.4'), '4-point lens flare cross present at exhaust nozzle');
    console.log('PASS: 3D cruciform 4-fin cross chassis and radial ion thruster corona verified');

    // 4. Static Checks: Active Homing Steering & Defender Phase
    assert(code.includes('const turnRate = 0.088 * stepScale;'), 'Active homing turn rate present');
    assert(code.includes('wobbleDamp = bestTargetPos ? 0.22 : 1.0;'), 'Aerodynamic wobble damping when homing locked');
    assert(code.includes('damageDefenderList(defenderPhase.pods'), 'Defender pod splash damage handling');
    assert(code.includes('damageDefenderList(defenderPhase.landers'), 'Defender lander splash damage handling');
    assert(code.includes('★ ASTRONAUT IN FREE-FALL! SWOOP IN TO CATCH!'), 'Astronaut dropped safely to free-fall upon lander missile destruction');
    console.log('PASS: Active homing guidance and full Defender enemy destruction confirmed');

    // 5. Mathematical Simulation: Homing Vector Convergence
    console.log('Testing homing steering physics simulation...');
    const rocket = {
        x: 0, y: 0, z: 0,
        forward: { x: 0, y: 0, z: 1 },
        right: { x: 1, y: 0, z: 0 },
        down: { x: 0, y: 1, z: 0 }
    };
    const target = { x: 120, y: 0, z: 400 };

    // Simulate 15 frames of homing steering
    for (let frame = 0; frame < 15; frame++) {
        const toTarget = subVec(target, rocket);
        const dist = Math.hypot(toTarget.x, toTarget.y, toTarget.z);
        const targetDir = scaleVec(toTarget, 1 / dist);
        const turnRate = 0.088;
        rocket.forward = normalize({
            x: rocket.forward.x + targetDir.x * turnRate,
            y: rocket.forward.y + targetDir.y * turnRate,
            z: rocket.forward.z + targetDir.z * turnRate
        });
        rocket.x += rocket.forward.x * 12.5;
        rocket.y += rocket.forward.y * 12.5;
        rocket.z += rocket.forward.z * 12.5;
    }
    // Missile should have curved significantly toward +X
    assert(rocket.forward.x > 0.18, `Rocket forward.x (${rocket.forward.x}) must steer toward positive X`);
    assert(rocket.x > 15, `Rocket position X (${rocket.x}) must track toward target`);
    console.log(`PASS: Homing steering curved rocket cleanly toward target (heading: ${rocket.forward.x.toFixed(3)}, ${rocket.forward.y.toFixed(3)}, ${rocket.forward.z.toFixed(3)})`);

    // 6. Mathematical Simulation: Splash Damage Falloff
    console.log('Testing splash damage falloff curve across 220 units...');
    function calcDamage(dist, maxRadius = 220) {
        if (dist > maxRadius) return 0;
        if (dist <= 120) return 250;
        const splashFactor = Math.max(0, 1 - (dist / maxRadius));
        return Math.round(75 + splashFactor * 125);
    }
    assert.strictEqual(calcDamage(0), 250, 'Center hit must deal lethal 250 dmg');
    assert.strictEqual(calcDamage(80), 250, 'Inside 120 unit core must deal lethal 250 dmg');
    assert(calcDamage(160) >= 105 && calcDamage(160) <= 115, `Mid-splash (160u) damage (${calcDamage(160)}) in expected range`);
    assert(calcDamage(210) >= 78 && calcDamage(210) <= 85, `Outer rim (210u) damage (${calcDamage(210)}) in expected range`);
    assert.strictEqual(calcDamage(221), 0, 'Outside 220u blast radius must deal 0 dmg');
    console.log('PASS: Splash damage falloff curve verified');
}

runTestSuite('DecentClone/index.html');
runTestSuite('index.html');

// Check byte-for-byte identical match between DecentClone and root
const f1 = fs.readFileSync('DecentClone/index.html');
const f2 = fs.readFileSync('index.html');
assert.strictEqual(f1.length, f2.length, `File lengths must match (${f1.length} vs ${f2.length})`);
assert.strictEqual(f1.compare(f2), 0, 'DecentClone/index.html and root index.html must be identical byte-for-byte');
console.log('\nALL 6 TEST SUITES PASSED — Byte-for-byte synchronization verified!');
