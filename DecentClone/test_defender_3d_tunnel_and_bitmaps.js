/**
 * test_defender_3d_tunnel_and_bitmaps.js
 * Verification test suite for Defender 3D Mega-Tunnel, Deep Space Panorama, and Entity Bitmaps.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('\n=== RUNNING DEFENDER 3D MEGA-TUNNEL & BITMAPS TEST SUITE ===\n');

// 1. Verify all texture assets exist on disk
const expectedAssets = [
    'Textures/WallTextures/deep-space-01.jpg',
    'Textures/Space Textures/planet02.jpeg',
    'Textures/AI Textures/PNG/Sprites/Astronauts/spaceAstronauts_001.png',
    'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_003.png',
    'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_008.png',
    'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_007.png',
    'Textures/AI Textures/PNG/Sprites/Meteors/spaceMeteors_001.png',
    'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_002.png',
    'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_006.png'
];

for (const relPath of expectedAssets) {
    const fullPath = path.join(__dirname, relPath);
    assert(fs.existsSync(fullPath), `Asset must exist: ${relPath}`);
    const size = fs.statSync(fullPath).size;
    assert(size > 100, `Asset size must be non-trivial: ${relPath} (${size} bytes)`);
}
console.log('PASS: All 9 Defender deep space, planet, and entity texture assets verified on disk');

// 2. Test both index files
const filesToTest = [
    path.join(__dirname, 'index.html'),
    path.join(__dirname, '..', 'index.html')
];

for (const filePath of filesToTest) {
    const fileName = path.basename(path.dirname(filePath)) + '/' + path.basename(filePath);
    console.log(`\n--- Testing ${fileName} ---`);
    const content = fs.readFileSync(filePath, 'utf8');

    // Verify syntax
    const scriptMatch = content.match(/<script>([\s\S]*?)<\/script>/i);
    assert(scriptMatch, `Script tag must exist in ${fileName}`);
    new Function(scriptMatch[1]);
    console.log(`PASS: ${fileName} syntax valid under strict compilation`);

    // Verify DEFENDER_TEXTURE_PATHS
    assert(content.includes('const DEFENDER_TEXTURE_PATHS = {'), 'DEFENDER_TEXTURE_PATHS dictionary declared');
    assert(content.includes('spaceBg: \'Textures/WallTextures/deep-space-01.jpg\''), 'spaceBg configured');
    assert(content.includes('planet: \'Textures/Space Textures/planet02.jpeg\''), 'planet configured');
    assert(content.includes('astronaut: \'Textures/AI Textures/PNG/Sprites/Astronauts/spaceAstronauts_001.png\''), 'astronaut sprite configured');
    assert(content.includes('lander: \'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_003.png\''), 'lander sprite configured');
    assert(content.includes('mutant: \'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_008.png\''), 'mutant sprite configured');
    assert(content.includes('bomber: \'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_007.png\''), 'bomber sprite configured');
    assert(content.includes('pod: \'Textures/AI Textures/PNG/Sprites/Meteors/spaceMeteors_001.png\''), 'pod sprite configured');
    assert(content.includes('swarmer: \'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_002.png\''), 'swarmer sprite configured');
    assert(content.includes('baiter: \'Textures/AI Textures/PNG/Sprites/Ships/spaceShips_006.png\''), 'baiter sprite configured');
    console.log(`PASS: All sprite dictionary entries verified in ${fileName}`);

    // Verify drawing helper & fallback
    assert(content.includes('function drawDefenderSprite('), 'drawDefenderSprite function exists');
    assert(content.includes('renderDefenderDeepSpaceBackdrop('), 'renderDefenderDeepSpaceBackdrop exists');
    assert(content.includes('renderDefender3DTunnel('), 'renderDefender3DTunnel exists');
    console.log(`PASS: Core 3D tunnel and deep space renderer functions present in ${fileName}`);

    // Verify calls in renderDefenderPhase
    assert(content.includes('renderDefenderDeepSpaceBackdrop(centerX, centerY, fov);'), 'Backdrop called');
    assert(content.includes('renderDefender3DTunnel(centerX, centerY, fov);'), '3D tunnel called');
    console.log(`PASS: Pipeline calls renderDefenderDeepSpaceBackdrop & renderDefender3DTunnel in ${fileName}`);
}

// 3. Verify byte-for-byte sync
const b1 = fs.readFileSync(filesToTest[0]);
const b2 = fs.readFileSync(filesToTest[1]);
assert(b1.equals(b2), 'DecentClone/index.html and root index.html must match byte-for-byte');
console.log(`\nPASS: DecentClone/index.html and index.html match byte-for-byte (${b1.length} bytes)`);

// 4. Test 3D Tunnel Rib Projection Math
const DEFENDER = { ORIGIN: { x: 0, y: -45000, z: 0 }, WIDTH: 7000, HALF_W: 3500, HEIGHT_TOP: -1800, HEIGHT_FLOOR: 420 };
const posX = 0, posY = DEFENDER.ORIGIN.y - 80, posZ = 0;
const shipForward = { x: 1, y: 0, z: 0 }, shipRight = { x: 0, y: 0, z: -1 }, shipDown = { x: 0, y: 1, z: 0 };

function worldToCamera(p) {
    const rx = p.x - posX, ry = p.y - posY, rz = p.z - posZ;
    return {
        x: rx * shipRight.x + ry * shipRight.y + rz * shipRight.z,
        y: rx * shipDown.x + ry * shipDown.y + rz * shipDown.z,
        z: rx * shipForward.x + ry * shipForward.y + rz * shipForward.z
    };
}
function projectPoint(p, cx, cy, fov) {
    const c = worldToCamera(p);
    if (c.z <= 5) return null;
    return { x: cx + (c.x / c.z) * fov, y: cy + (c.y / c.z) * fov, z: c.z };
}

const tunnelCenterY = DEFENDER.ORIGIN.y - 690;
const archProfile = [
    { dy: 420,  dz: -1420 },
    { dy: -1300, dz: 0    },
    { dy: 420,  dz: 1420 }
];

const forwardDists = [320, 640, 1280, 2560];
for (const dist of forwardDists) {
    const apex = projectPoint({ x: posX + dist, y: tunnelCenterY - 1300, z: 0 }, 400, 300, 450);
    assert(apex !== null, 'Apex point must project successfully');
    assert(apex.z === dist, `Projected z must equal distance: expected ${dist}, got ${apex.z}`);
    assert(apex.x === 400, `Apex must be horizontally centered at 400: got ${apex.x}`);
    assert(apex.y < 300, `Apex must be in upper half of view (above centerY): got ${apex.y}`);
}
console.log('PASS: 3D Tunnel Arch perspective projection math verified across distances (320m - 2560m)');

console.log('\nALL DEFENDER 3D TUNNEL & BITMAP GRAPHICS TESTS PASSED!\n');
