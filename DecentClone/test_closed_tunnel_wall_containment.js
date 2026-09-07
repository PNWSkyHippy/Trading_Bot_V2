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

const seg = {
    from: { x: 0, y: 0, z: 0 },
    forward: { x: 0, y: 0, z: 1 },
    radius: 100,
    length: 200,
    capStart: false,
    capEnd: false,
    openEnd: false
};

const context = {
    builder: { radius: 100, segments: [seg] },
    gulletPhase: { active: false },
    TUNNEL_SAFE_MARGIN: 12,
    TUNNEL_OPEN_SPACE_DETACH: 1.42,
    posX: 200,
    posY: 0,
    posZ: 100,
    shipSegmentIndex: 0,
    shipForward: { x: 0, y: 0, z: 1 },
    lastThrustVector: { x: 0, y: 0, z: 1 },
    wallHit: {
        active: false,
        intensity: 0,
        stuckCount: 0,
        lastRadius: 0,
        lockUntil: 0,
        lockedSegmentIndex: null
    },
    performance: { now: () => 1000 },
    console: { warn: () => {} },
    containShipInExactGulletRooms: () => false,
    nearestTunnelPoint: () => ({
        index: 0,
        seg,
        dist2: context.posX ** 2 + context.posY ** 2
    }),
    pointInJunctionBubble: () => null,
    pointWithinBubbleJointFootprint: () => false,
    tunnelSegmentsConnected: () => false,
    shipSegmentLocal: ship => {
        const localZ = ship.z;
        return {
            localZ,
            radialDist: Math.hypot(ship.x, ship.y),
            onAxis: { x: 0, y: 0, z: localZ },
            length: seg.length,
            forward: seg.forward
        };
    },
    segmentIsRoundJunction: () => false,
    segmentIsRectRoom: () => false,
    segmentIsChamber: () => false,
    isOpenSegmentEnd: (candidate, end) => candidate.openEnd && end === 'to',
    getBranchFlightContext: () => ({
        containRelax: 0,
        allowVerticalPitch: false,
        verticalSegment: false
    }),
    radialContainmentNormal: ship => ({ x: ship.x < 0 ? -1 : 1, y: 0, z: 0 }),
    dot: (a, b) => a.x * b.x + a.y * b.y + a.z * b.z,
    addVec: (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }),
    scaleVec: (a, amount) => ({ x: a.x * amount, y: a.y * amount, z: a.z * amount }),
    forceCockpitBasisFromNose: () => {},
    repairBasis: () => {},
    syncViewToShip: () => {}
};

vm.createContext(context);
vm.runInContext(extractFunction('shipMayExitTunnelMouth'), context);
vm.runInContext(extractFunction('containShipInTunnel'), context);

// A ship far outside a fully closed ordinary tube used to trigger the generic
// open-space detach before the hard escape correction below it could run.
context.containShipInTunnel();
if (!(context.posX > 0 && context.posX < seg.radius)) {
    throw new Error('closed ordinary tube did not push an over-radius ship back inside');
}

// Authored mouth exit remains the explicit release path and must not be clamped.
seg.openEnd = true;
context.posX = 0;
context.posY = 0;
context.posZ = seg.length + 20;
context.wallHit.active = true;
context.containShipInTunnel();
if (context.posZ !== seg.length + 20 || context.wallHit.active) {
    throw new Error('explicit open-mouth exit was no longer released');
}

const containmentSource = extractFunction('containShipInTunnel');
if (containmentSource.includes('TUNNEL_OPEN_SPACE_DETACH') ||
    containmentSource.includes('shipInsideAnyTunnelTube')) {
    throw new Error('closed-tube containment still has a radial open-space detach');
}
if (containmentSource.indexOf('shipMayExitTunnelMouth') < 0 ||
    containmentSource.indexOf('shipMayExitTunnelMouth') > containmentSource.indexOf('const candidateSegmentIndex')) {
    throw new Error('explicit mouth release no longer precedes ordinary containment');
}

console.log('closed tunnel containment passed: radial escape is corrected and authored mouth exit remains open');
