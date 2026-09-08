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
    let lineComment = false;
    let blockComment = false;
    for (let i = brace; i < html.length; i++) {
        const ch = html[i];
        const next = html[i + 1];
        if (lineComment) {
            if (ch === '\n') lineComment = false;
            continue;
        }
        if (blockComment) {
            if (ch === '*' && next === '/') {
                blockComment = false;
                i++;
            }
            continue;
        }
        if (quote) {
            if (escaped) escaped = false;
            else if (ch === '\\') escaped = true;
            else if (ch === quote) quote = null;
            continue;
        }
        if (ch === '/' && next === '/') {
            lineComment = true;
            i++;
            continue;
        }
        if (ch === '/' && next === '*') {
            blockComment = true;
            i++;
            continue;
        }
        if (ch === '"' || ch === "'" || ch === '`') quote = ch;
        else if (ch === '{') depth++;
        else if (ch === '}' && --depth === 0) return html.slice(start, i + 1);
    }
    throw new Error(name + ' end is missing');
}

const incomingTube = { radius: 100, length: 100, capStart: false, capEnd: false };
const junctionBox = {
    rectRoom: true,
    radius: 100,
    length: 200,
    capStart: false,
    capEnd: false
};

const context = {
    builder: { radius: 100, segments: [incomingTube, junctionBox] },
    gulletPhase: { active: false },
    TUNNEL_SAFE_MARGIN: 12,
    posX: 0,
    posY: 95,
    posZ: 120,
    shipSegmentIndex: 0,
    shipForward: { x: 0, y: 0, z: 1 },
    lastThrustVector: { x: 0, y: 1, z: 0 },
    wallHit: {
        active: true,
        intensity: 1,
        stuckCount: 1,
        lastRadius: 100,
        lockUntil: 0,
        lockedSegmentIndex: null
    },
    performance: { now: () => 1000 },
    console: { warn: () => {} },
    containShipInExactGulletRooms: () => false,
    nearestTunnelPoint: () => ({ index: 1, seg: junctionBox, dist2: 0 }),
    pointInJunctionBubble: () => null,
    pointWithinBubbleJointFootprint: () => false,
    tunnelSegmentsConnected: () => true,
    segmentIsRectRoom: seg => !!seg.rectRoom,
    segmentIsChamber: () => false,
    segmentIsRoundJunction: () => false,
    segmentIsJunctionCube: () => false,
    rectRoomDistanceState: point => ({
        local: { x: point.x, y: point.y, z: point.z },
        halfWidth: 100,
        halfHeight: 100,
        outsideDist: 0
    }),
    shipSegmentLocal: point => ({
        localZ: point.z,
        radialDist: Math.hypot(point.x, point.y),
        onAxis: { x: 0, y: 0, z: point.z },
        length: point.z === 120 ? 100 : 100,
        forward: { x: 0, y: 0, z: 1 }
    }),
    isOpenSegmentEnd: () => true,
    getBranchFlightContext: () => ({ containRelax: 0, allowVerticalPitch: false, verticalSegment: false }),
    segmentLocalToWorld: (seg, x, y, z) => ({ x, y, z }),
    applyShieldWallDrain: () => {},
    dot: (a, b) => a.x * b.x + a.y * b.y + a.z * b.z,
    addVec: (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }),
    scaleVec: (a, amount) => ({ x: a.x * amount, y: a.y * amount, z: a.z * amount }),
    radialContainmentNormal: () => ({ x: 0, y: 1, z: 0 }),
    forceCockpitBasisFromNose: () => {},
    repairBasis: () => {},
    syncViewToShip: () => {}
};

vm.createContext(context);
vm.runInContext(extractFunction('shipMayExitTunnelMouth'), context);
vm.runInContext(extractFunction('containShipInTunnel'), context);
context.containShipInTunnel();

if (context.shipSegmentIndex !== 1) {
    throw new Error('scraped incoming tube retained ownership after entering a rectangular junction');
}
if (context.posY !== 88) {
    throw new Error('rectangular junction floor did not clamp the 90-degree scrape handoff');
}

const source = extractFunction('containShipInTunnel');
if (!source.includes('nearestRectContainsShip') ||
    source.indexOf('nearestRectContainsShip') > source.indexOf('tunnelSegmentsConnected(priorSeg, nearest.seg)')) {
    throw new Error('rectangular ownership guard is missing or ordered after prior-tube retention');
}

console.log('rect junction scrape handoff passed: a contained box owns collision before the old tube can release');
