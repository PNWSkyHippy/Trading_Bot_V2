const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');

function extractFunction(name) {
    const start = html.indexOf('function ' + name + '(');
    if (start < 0) throw new Error(name + ' is missing');
    const brace = html.indexOf('{', start);
    let depth = 0;
    let quote = null;
    let escaped = false;
    for (let i = brace; i < html.length; i++) {
        const ch = html[i];
        if (quote) {
            if (escaped) escaped = false;
            else if (ch === '\\') escaped = true;
            else if (ch === quote) quote = null;
            continue;
        }
        if (ch === '"' || ch === "'" || ch === '`') quote = ch;
        else if (ch === '{') depth++;
        else if (ch === '}' && --depth === 0) return html.slice(start, i + 1);
    }
    throw new Error(name + ' end is missing');
}

function room(from, forward, right, down, length, width, height) {
    return {
        gulletArena: true,
        rectRoom: true,
        from,
        forward,
        right,
        down,
        length,
        roomWidth: width,
        roomHeight: height
    };
}

const cube = room(
    { x: 0, y: 0, z: 0 },
    { x: 0, y: 0, z: 1 },
    { x: 1, y: 0, z: 0 },
    { x: 0, y: 1, z: 0 },
    100, 200, 200
);
const sideHall = room(
    { x: 100, y: 0, z: 50 },
    { x: 1, y: 0, z: 0 },
    { x: 0, y: 0, z: -1 },
    { x: 0, y: 1, z: 0 },
    100, 80, 80
);
const floorShaft = room(
    { x: 50, y: 100, z: 50 },
    { x: 0, y: 1, z: 0 },
    { x: 1, y: 0, z: 0 },
    { x: 0, y: 0, z: 1 },
    100, 80, 80
);

const context = {
    gulletPhase: { active: true },
    builder: { segments: [cube, sideHall, floorShaft] },
    shipSegmentIndex: 0,
    TUNNEL_SAFE_MARGIN: 12,
    posX: 0,
    posY: 0,
    posZ: 0,
    wallHit: { active: false, intensity: 0, stuckCount: 0 },
    performance: { now: () => 1000 },
    segmentIsRectRoom: seg => !!seg.rectRoom,
    rectRoomDistanceState(point, seg) {
        const rel = {
            x: point.x - seg.from.x,
            y: point.y - seg.from.y,
            z: point.z - seg.from.z
        };
        const local = {
            x: rel.x * seg.right.x + rel.y * seg.right.y + rel.z * seg.right.z,
            y: rel.x * seg.down.x + rel.y * seg.down.y + rel.z * seg.down.z,
            z: rel.x * seg.forward.x + rel.y * seg.forward.y + rel.z * seg.forward.z
        };
        return {
            local,
            halfWidth: seg.roomWidth / 2,
            halfHeight: seg.roomHeight / 2,
            length: seg.length
        };
    },
    segmentLocalToWorld(seg, x, y, z) {
        return {
            x: seg.from.x + seg.right.x * x + seg.down.x * y + seg.forward.x * z,
            y: seg.from.y + seg.right.y * x + seg.down.y * y + seg.forward.y * z,
            z: seg.from.z + seg.right.z * x + seg.down.z * y + seg.forward.z * z
        };
    }
};
vm.createContext(context);
vm.runInContext(extractFunction('containShipInExactGulletRooms'), context);

if (!context.containShipInExactGulletRooms({ x: 120, y: 0, z: 50 })) {
    throw new Error('open side-hall junction was not handled');
}
if (context.shipSegmentIndex !== 1 || context.posX !== 0 || context.posY !== 0 || context.posZ !== 0) {
    throw new Error('valid side-hall entry was clamped or assigned to the wrong room');
}

context.shipSegmentIndex = 0;
if (!context.containShipInExactGulletRooms({ x: 50, y: 120, z: 50 })) {
    throw new Error('aligned floor shaft was not admitted');
}
if (context.shipSegmentIndex !== 2) throw new Error('floor shaft did not own its open volume');

context.shipSegmentIndex = 0;
context.posX = 999;
context.posY = 999;
context.posZ = 999;
context.containShipInExactGulletRooms({ x: 95, y: 120, z: 50 });
if (context.posX > 78 || context.posZ < 22 || context.posZ > 78) {
    throw new Error('floor escape outside the shaft opening was not clamped');
}

const powerDurations = [...html.matchAll(/POWER_MS:\s*(\d+)/g)].map(match => Number(match[1]));
if (powerDurations.length < 2 || powerDurations.some(value => value !== 30000)) {
    throw new Error('all Gullet surge durations must be exactly 30 seconds');
}
for (const marker of [
    'BLUE JELLIES KILLABLE',
    'RED-EYED JELLIES LETHAL',
    "ctx.fillText('KILLABLE'",
    'const TUNNEL_BRANCH_INDICATORS_ENABLED = false',
    'if (!TUNNEL_BRANCH_INDICATORS_ENABLED) return;'
]) {
    if (!html.includes(marker)) throw new Error('missing Gullet/indicator clarity marker: ' + marker);
}

console.log('Gullet exact-room containment passed: side and shaft entries open; off-shaft floor escape clamped; surge 30s; states explicit; octagons disabled');
