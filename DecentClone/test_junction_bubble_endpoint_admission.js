const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');

function extractFunction(name) {
    const start = html.indexOf('function ' + name + '(');
    if (start < 0) throw new Error(name + ' is missing');
    const match = html.slice(start).match(new RegExp('^function ' + name + '\\([\\s\\S]*?\\n        \\}'));
    if (!match) throw new Error(name + ' end is missing');
    return match[0];
}

function distanceSq(a, b) {
    return (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2;
}

function tube(from, to, options = {}) {
    return {
        from,
        to,
        length: Math.hypot(to.x - from.x, to.y - from.y, to.z - from.z),
        radius: 100,
        forward: options.forward || { x: 0, y: 0, z: 1 },
        capStart: !!options.capStart,
        capEnd: !!options.capEnd,
        autoJoinLocked: !!options.autoJoinLocked
    };
}

const context = {
    TUNNEL_SAFE_MARGIN: 12,
    builder: { radius: 100, segments: [] },
    junctionBubbleCache: { stale: true, bubbles: [] },
    segmentIsChamber: () => false,
    segmentIsRectRoom: () => false,
    segmentIsRoundJunction: seg => !!seg.roundJunction,
    junctionFaceStates: seg => seg.faceStates || {},
    junctionFaceCenter: (_seg, face) => ({ x: 20, y: 0, z: face === 'right' ? 0 : 1000 }),
    tunnelSegmentsConnected: (a, b) => {
        const thresholdSq = Math.pow(Math.max(a.radius || 100, b.radius || 100) * 0.72, 2);
        return [a.from, a.to].some(pa => [b.from, b.to].some(pb => distanceSq(pa, pb) <= thresholdSq));
    },
    distanceSq,
    shipSegmentLocal: (ship, seg) => {
        const delta = {
            x: seg.to.x - seg.from.x,
            y: seg.to.y - seg.from.y,
            z: seg.to.z - seg.from.z
        };
        const length = seg.length;
        const forward = { x: delta.x / length, y: delta.y / length, z: delta.z / length };
        const rel = { x: ship.x - seg.from.x, y: ship.y - seg.from.y, z: ship.z - seg.from.z };
        const localZ = rel.x * forward.x + rel.y * forward.y + rel.z * forward.z;
        const onAxis = {
            x: seg.from.x + forward.x * localZ,
            y: seg.from.y + forward.y * localZ,
            z: seg.from.z + forward.z * localZ
        };
        return { localZ, length, radialDist: Math.sqrt(distanceSq(ship, onAxis)) };
    },
    dot: (a, b) => a.x * b.x + a.y * b.y + a.z * b.z,
    Math,
    Set,
    Array
};
vm.createContext(context);
for (const name of [
    'junctionBubbleMemberIsOpen',
    'junctionBubbleMembersCanConnect',
    'getJunctionBubbles',
    'pointInJunctionBubble',
    'pointWithinSegmentFootprint',
    'pointTouchesSegmentCap',
    'pointWithinBubbleJointFootprint'
]) {
    vm.runInContext(extractFunction(name), context);
}

function rebuild(segments) {
    context.builder.segments = segments;
    context.junctionBubbleCache = { stale: true, bubbles: [] };
    return context.getJunctionBubbles();
}

const sealedA = tube({ x: 0, y: 0, z: -100 }, { x: 0, y: 0, z: 0 }, { capEnd: true });
const sealedB = tube({ x: 20, y: 0, z: 0 }, { x: 20, y: 0, z: 100 }, { capStart: true });
if (rebuild([sealedA, sealedB]).length !== 0) {
    throw new Error('capped nearby endpoints created a free-flight bubble');
}
if (context.pointInJunctionBubble({ x: 10, y: 0, z: 0 }) !== null) {
    throw new Error('capped nearby endpoints still bypass normal cap containment');
}

const openA = tube({ x: 0, y: 0, z: -100 }, { x: 0, y: 0, z: 0 }, { forward: { x: 0, y: 0, z: 1 } });
const openB = tube({ x: 20, y: 0, z: 0 }, { x: 120, y: 0, z: 0 }, { forward: { x: 1, y: 0, z: 0 } });
const openBubbles = rebuild([openA, openB]);
if (openBubbles.length !== 1 || openBubbles[0].segs.join(',') !== '0,1') {
    throw new Error('uncapped connected turn lost its junction bubble');
}
if (Math.abs(openBubbles[0].r - 112) > 0.0001) {
    throw new Error('uncapped corner bubble no longer retains its existing radius');
}

const shortCappedA = tube(
    { x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 42 },
    { capEnd: true, forward: { x: 0, y: 0, z: 1 } }
);
const shortOpenB = tube(
    { x: 20, y: 0, z: 0 }, { x: 120, y: 0, z: 0 },
    { forward: { x: 1, y: 0, z: 0 } }
);
const overlappingBubbles = rebuild([shortCappedA, shortOpenB]);
const cappedEndPoint = { x: 0, y: 0, z: 42 };
if (overlappingBubbles.length !== 1 || !context.pointInJunctionBubble(cappedEndPoint)) {
    throw new Error('test setup did not create the accepted open-corner bubble overlapping its other cap');
}
if (context.pointWithinBubbleJointFootprint(cappedEndPoint, overlappingBubbles[0])) {
    throw new Error('an accepted bubble bypassed the opposite capped end of a short member');
}

const lockedSealedA = tube(
    { x: 0, y: 0, z: -100 }, { x: 0, y: 0, z: 0 },
    { capEnd: true, autoJoinLocked: true }
);
const lockedSealedB = tube(
    { x: 20, y: 0, z: 0 }, { x: 20, y: 0, z: 100 },
    { capStart: true, autoJoinLocked: true }
);
if (rebuild([lockedSealedA, lockedSealedB]).length !== 0) {
    throw new Error('autoJoinLocked revived a sealed junction bubble');
}

const lockedOpenA = tube(
    { x: 0, y: 0, z: -100 }, { x: 0, y: 0, z: 0 },
    { autoJoinLocked: true, forward: { x: 0, y: 0, z: 1 } }
);
const lockedOpenB = tube(
    { x: 20, y: 0, z: 0 }, { x: 120, y: 0, z: 0 },
    { autoJoinLocked: true, forward: { x: 1, y: 0, z: 0 } }
);
if (rebuild([lockedOpenA, lockedOpenB]).length !== 1) {
    throw new Error('autoJoinLocked incorrectly denied an authored open joint');
}

const faceMember = {
    p: { x: 20, y: 0, z: 0 }, r: 100, i: 0,
    seg: {
        from: { x: 0, y: 0, z: 0 }, to: { x: 20, y: 0, z: 0 },
        radius: 100, faceStates: { right: false }
    },
    kind: 'face', face: 'right'
};
const endpointMember = {
    p: { x: 20, y: 0, z: 0 }, r: 100, i: 1,
    seg: openB, kind: 'endpoint', end: 'from'
};
if (context.junctionBubbleMembersCanConnect(faceMember, endpointMember)) {
    throw new Error('closed junction face admitted a bubble member');
}
faceMember.seg.faceStates.right = true;
if (!context.junctionBubbleMembersCanConnect(faceMember, endpointMember)) {
    throw new Error('declared-open junction face did not admit a connected member');
}

console.log('junction bubble admission regression passed: sealed endpoints and closed faces denied; open joins retained');
