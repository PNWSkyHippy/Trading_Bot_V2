const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');
const inlineScripts = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)];
for (const script of inlineScripts) new Function(script[1]);

function extractFunction(name) {
    const start = html.indexOf('function ' + name + '(');
    if (start < 0) throw new Error(name + ' is missing');
    const match = html.slice(start).match(
        new RegExp('^function ' + name + '\\([\\s\\S]*?\\n        \\}')
    );
    if (!match) throw new Error(name + ' end is missing');
    return match[0];
}

function normalize(value) {
    const length = Math.hypot(value.x, value.y, value.z) || 1;
    return { x: value.x / length, y: value.y / length, z: value.z / length };
}

function cross(a, b) {
    return {
        x: a.y * b.z - a.z * b.y,
        y: a.z * b.x - a.x * b.z,
        z: a.x * b.y - a.y * b.x
    };
}

function dot(a, b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

function rotateVector(value, axis, angle) {
    const n = normalize(axis);
    const c = Math.cos(angle);
    const s = Math.sin(angle);
    const projection = dot(value, n);
    const perpendicular = cross(n, value);
    return {
        x: value.x * c + perpendicular.x * s + n.x * projection * (1 - c),
        y: value.y * c + perpendicular.y * s + n.y * projection * (1 - c),
        z: value.z * c + perpendicular.z * s + n.z * projection * (1 - c)
    };
}

const context = {
    MAP_IMPORT_MAX_SEGMENTS: 2000,
    WALL_TEXTURE_MAPPING_DISTANCE: 'distance-run',
    WALL_TEXTURE_DISTANCE_DEFAULT_SPAN: 1200,
    WALL_TEXTURE_DISTANCE_MIN_SPAN: 60,
    WALL_TEXTURE_DISTANCE_MAX_SPAN: 50000,
    TUNNEL_HARD_TURN_MAX_DOT: 0.35,
    TUNNEL_SECTION_JOIN_OVERLAP: 18,
    TUNNEL_SEGMENT_JOIN_OVERLAP: 48,
    RECT_ROOM_FACES: ['start', 'end', 'right', 'left', 'floor', 'ceiling'],
    builder: {
        radius: 120,
        right: { x: 1, y: 0, z: 0 },
        down: { x: 0, y: 1, z: 0 },
        segments: []
    },
    copyVec: value => ({ x: value.x, y: value.y, z: value.z }),
    normalize,
    cross,
    dot,
    rotateVector,
    scaleVec: (value, amount) => ({
        x: value.x * amount,
        y: value.y * amount,
        z: value.z * amount
    }),
    subVec: (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z }),
    distanceSq: (a, b) =>
        (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2,
    segmentIsChamber: seg => !!seg.chamber,
    segmentIsJunctionCube: seg => !!seg.junctionCube,
    segmentIsRectRoom: seg => !!seg.rectRoom,
    isOpenSegmentEnd: () => false,
    textureUsesSectionMapping: () => false,
    getWebGLTextureForSegment: () => null,
    getWallTextureEntry: () => null,
    segmentRadiusAt: seg => seg.radius || 120
};
vm.createContext(context);

for (const name of [
    'clearSegmentDistanceWallMapping',
    'sanitizeSegmentDistanceWallMapping',
    'segmentUsesDistanceWallMapping',
    'textureRunPathConnection',
    'orientDistanceTextureRunPath',
    'transportTextureRunReference',
    'planDistanceTextureRun',
    'applyDistanceTextureRunPlan',
    'rectRoomFaceStates',
    'setRectRoomFaceOpen',
    'segmentIsJunctionCube',
    'segmentEndHasHardTubeTurn',
    'getSegmentPanelZExtent',
    'splitSegmentAtPoint',
    'splitLongAutogenSegment'
]) {
    vm.runInContext(extractFunction(name), context);
}

function segment(from, to, overrides = {}) {
    const forward = normalize({
        x: to.x - from.x,
        y: to.y - from.y,
        z: to.z - from.z
    });
    let right = normalize(overrides.right || { x: 1, y: 0, z: 0 });
    if (Math.abs(dot(right, forward)) > 0.99) right = { x: 0, y: 0, z: 1 };
    right = normalize({
        x: right.x - forward.x * dot(right, forward),
        y: right.y - forward.y * dot(right, forward),
        z: right.z - forward.z * dot(right, forward)
    });
    const down = normalize(cross(forward, right));
    return {
        from: { ...from },
        to: { ...to },
        length: Math.sqrt(context.distanceSq(from, to)),
        radius: 120,
        forward,
        right,
        down,
        ...overrides
    };
}

function straightSegments(count, length = 180) {
    return Array.from({ length: count }, (_, index) =>
        segment(
            { x: 0, y: 0, z: index * length },
            { x: 0, y: 0, z: (index + 1) * length }
        )
    );
}

context.builder.segments = straightSegments(7);
let plan = context.planDistanceTextureRun(
    context.builder.segments.map((_, index) => index),
    ['deep_space_01'],
    { targetSpan: 1200, boundaryMode: 'nearest-joint' }
);
if (plan.error) throw new Error(plan.error);
if (plan.chunks.length !== 1 || Math.round(plan.chunks[0].length) !== 1260) {
    throw new Error('seven 180u segments did not fit one image across 1260u');
}
if (Math.abs(plan.assignments[3].vStart - 3 / 7) > 1e-9) {
    throw new Error('straight-run cumulative V coordinate is wrong');
}

context.builder.segments = straightSegments(14);
plan = context.planDistanceTextureRun(
    context.builder.segments.map((_, index) => index),
    ['deep_space_01', 'deep_space_02', 'deep_space_03'],
    { targetSpan: 1200, boundaryMode: 'nearest-joint' }
);
if (plan.chunks.length !== 2 || plan.chunks.some(chunk => Math.round(chunk.length) !== 1260)) {
    throw new Error('2520u run did not distribute into two balanced snapped chunks');
}
if (plan.assignments[6].textureId !== 'deep_space_01' ||
    plan.assignments[7].textureId !== 'deep_space_02') {
    throw new Error('image boundary was not snapped between segments 7 and 8');
}
if (!context.applyDistanceTextureRunPlan(plan, {
    runId: 'round-trip-run',
    packId: 'deep-space'
})) {
    throw new Error('valid distance-run plan was not applied');
}
const storedMapping = JSON.parse(JSON.stringify(context.builder.segments[7]));
if (!context.sanitizeSegmentDistanceWallMapping(storedMapping) ||
    storedMapping.wallTextureRunId !== 'round-trip-run' ||
    storedMapping.wallTexturePackId !== 'deep-space' ||
    !context.segmentUsesDistanceWallMapping(storedMapping)) {
    throw new Error('applied texture-run mapping did not survive JSON round trip');
}

context.builder.segments = straightSegments(11);
plan = context.planDistanceTextureRun(
    context.builder.segments.map((_, index) => index),
    ['deep_space_01', 'deep_space_02'],
    { targetSpan: 1200, boundaryMode: 'nearest-joint' }
);
if (plan.chunks.length !== 2 ||
    Math.min(...plan.chunks.map(chunk => chunk.length)) < 800) {
    throw new Error('short remainder was not redistributed across image chunks');
}

const uPoints = [
    { x: 0, y: 0, z: 0 },
    { x: 0, y: 0, z: 180 },
    { x: 180, y: 0, z: 180 },
    { x: 180, y: 0, z: 0 },
    { x: 180, y: 0, z: -180 }
];
context.builder.segments = uPoints.slice(0, -1).map((point, index) =>
    segment(point, uPoints[index + 1], {
        right: index === 0 ? { x: 1, y: 0, z: 0 } : { x: 0, y: 0, z: -1 }
    })
);
plan = context.planDistanceTextureRun([0, 1, 2, 3], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
if (plan.error || plan.assignments.some(item => !Number.isFinite(item.uOffset))) {
    throw new Error('U-shaped route did not preserve finite circumferential phase');
}

context.builder.segments = [
    segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 180 }),
    segment({ x: 0, y: 0, z: 180 }, { x: 180, y: 0, z: 180 })
];
plan = context.planDistanceTextureRun([0, 1], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
context.applyDistanceTextureRunPlan(plan, { runId: 'right-angle-run' });
const rightAngleExtent = context.getSegmentPanelZExtent(context.builder.segments[0]);
if (!rightAngleExtent.trimHardTo ||
    rightAngleExtent.zEnd !== context.builder.segments[0].length) {
    throw new Error('mapped 90-degree tube joint retained its occluding axial sleeve');
}

context.builder.segments = straightSegments(2);
plan = context.planDistanceTextureRun([0, 1], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
context.applyDistanceTextureRunPlan(plan, { runId: 'straight-overlap-run' });
const straightExtent = context.getSegmentPanelZExtent(context.builder.segments[0]);
if (straightExtent.trimHardTo ||
    straightExtent.zEnd !== context.builder.segments[0].length + 18) {
    throw new Error('straight mapped joint lost its crack-hiding overlap');
}

const sixPortJunction = {
    rectRoom: true,
    junctionCube: true,
    capStart: true,
    capEnd: true,
    roomOpenRight: false,
    roomOpenLeft: false,
    roomOpenFloor: false,
    roomOpenCeiling: false
};
for (const face of context.RECT_ROOM_FACES) {
    if (!context.setRectRoomFaceOpen(sixPortJunction, face, true)) {
        throw new Error('six-port junction could not open face: ' + face);
    }
}
const sixPortStates = context.rectRoomFaceStates(sixPortJunction);
if (Object.values(sixPortStates).some(open => !open) ||
    !context.segmentIsJunctionCube(sixPortJunction)) {
    throw new Error('six-port junction did not expose six independent open states');
}
context.setRectRoomFaceOpen(sixPortJunction, 'ceiling', false);
if (context.rectRoomFaceStates(sixPortJunction).ceiling ||
    !sixPortJunction.roomOpenFloor) {
    throw new Error('closing one junction port changed another port');
}

context.builder.segments = [
    segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 180 }),
    segment(
        { x: 0, y: 0, z: 360 },
        { x: 0, y: 0, z: 180 },
        { right: { x: 0, y: 1, z: 0 } }
    )
];
plan = context.planDistanceTextureRun([0, 1], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
if (plan.error || plan.assignments[1].direction !== -1 ||
    plan.assignments[1].vStart <= plan.assignments[1].vEnd ||
    Math.abs(plan.assignments[1].uOffset - 0.25) > 1e-9) {
    throw new Error('reversed stored segment did not reverse V and preserve U handedness');
}

context.builder.segments = [
    segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 600 }),
    segment(
        { x: 0, y: 0, z: 600 },
        { x: 0, y: 0, z: 1800 },
        { rectRoom: true, kind: 'rect-room', roomWidth: 500, roomHeight: 400 }
    )
];
plan = context.planDistanceTextureRun([0, 1], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
if (plan.error || plan.assignments.length !== 2) {
    throw new Error('tube-to-rect start/end transition was not accepted');
}

context.builder.segments = [
    segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 600 }),
    segment(
        { x: -600, y: 0, z: 900 },
        { x: 600, y: 0, z: 900 },
        { rectRoom: true, kind: 'rect-room', roomWidth: 500, roomHeight: 400 }
    )
];
plan = context.planDistanceTextureRun([0, 1], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
if (!plan.error || !plan.error.includes('side face')) {
    throw new Error('ambiguous room side-face transition was not rejected');
}

context.builder.segments = [
    segment(
        { x: 0, y: 0, z: 0 },
        { x: 0, y: 0, z: 180 },
        { rectRoom: true, junctionCube: true }
    )
];
plan = context.planDistanceTextureRun([0], ['deep_space_01'], {
    targetSpan: 1200,
    boundaryMode: 'fit-selection'
});
if (!plan.error || !plan.error.includes('junction cubes')) {
    throw new Error('junction cube was not treated as a texture-run boundary');
}

const malicious = {
    wallMappingMode: 'distance-run',
    wallTextureRunId: 'bad',
    wallTextureRunOrder: Infinity,
    wallTextureVStart: -100,
    wallTextureVEnd: 100,
    wallTextureTargetSpan: Infinity,
    wallTextureActualSpan: -5
};
if (context.sanitizeSegmentDistanceWallMapping(malicious) ||
    malicious.wallMappingMode !== undefined) {
    throw new Error('invalid imported distance mapping was not cleared');
}
const clampedDegenerate = {
    wallMappingMode: 'distance-run',
    wallTextureRunId: 'bad-after-clamp',
    wallTextureRunOrder: 0,
    wallTextureVStart: -0.0005,
    wallTextureVEnd: 0,
    wallTextureTargetSpan: 1200,
    wallTextureActualSpan: 1200
};
if (context.sanitizeSegmentDistanceWallMapping(clampedDegenerate) ||
    clampedDegenerate.wallMappingMode !== undefined) {
    throw new Error('mapping that collapses after import clamping was not cleared');
}

context.makeSegmentBetween = (from, to, right, down, kind) =>
    segment(from, to, { right, down, kind });
context.builder.segments = [
    {
        ...segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 180 }),
        wallTextureId: 'deep_space_01',
        ribColor: '#00ffff',
        wallMappingMode: 'distance-run',
        wallTextureRunId: 'split-run',
        wallTextureRunOrder: 0,
        wallTextureRunDirection: 1,
        wallTextureVStart: 0,
        wallTextureVEnd: 0.5,
        wallTextureUOffset: 0.125,
        wallTextureTargetSpan: 1200,
        wallTextureActualSpan: 1260,
        wallTextureBoundaryMode: 'nearest-joint',
        wallTexturePackId: 'deep-space'
    }
];
if (!context.splitSegmentAtPoint(0, { x: 0, y: 0, z: 90 })) {
    throw new Error('distance-mapped segment did not split');
}
if (context.builder.segments.length !== 2 ||
    context.builder.segments[0].wallTextureId !== 'deep_space_01' ||
    Math.abs(context.builder.segments[0].wallTextureVEnd - 0.25) > 1e-9 ||
    Math.abs(context.builder.segments[1].wallTextureVStart - 0.25) > 1e-9 ||
    context.builder.segments[1].wallTextureRunOrder !== 1) {
    throw new Error('split did not preserve and interpolate texture-run style');
}

context.mapAutogenMaxSegmentLength = () => 400;
context.mapAutogenTargetLength = () => 300;
context.appendAutogenSpan = (from, to, right, down, radius, out) => {
    for (let index = 0; index < 3; index++) {
        out.push(segment(
            { x: 0, y: 0, z: index * 300 },
            { x: 0, y: 0, z: (index + 1) * 300 },
            { generated: true, kind: 'join-curve', radius, right, down }
        ));
    }
};
const longJoin = {
    ...segment({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 900 }),
    generated: true,
    kind: 'join-curve',
    wallTextureId: 'deep_space_02',
    ribColor: '#12abcd',
    capStart: true,
    entranceFrameId: 'portal-blue',
    entranceFrameEnd: 'start',
    wallMappingMode: 'distance-run',
    wallTextureRunId: 'autogen-run',
    wallTextureRunOrder: 4,
    wallTextureRunDirection: 1,
    wallTextureVStart: 0.1,
    wallTextureVEnd: 1,
    wallTextureUOffset: 0.25,
    wallTextureTargetSpan: 1200,
    wallTextureActualSpan: 1200,
    wallTextureBoundaryMode: 'nearest-joint',
    wallTexturePackId: 'deep-space'
};
const laterRunSegment = {
    ...segment({ x: 0, y: 0, z: 900 }, { x: 0, y: 0, z: 1200 }),
    wallTextureRunId: 'autogen-run',
    wallTextureRunOrder: 5
};
context.builder.segments = [longJoin, laterRunSegment];
const repairedPieces = context.splitLongAutogenSegment(longJoin);
if (repairedPieces.length !== 3 ||
    repairedPieces.some(piece => !context.segmentUsesDistanceWallMapping(piece)) ||
    repairedPieces[0].wallTextureId !== 'deep_space_02' ||
    repairedPieces[0].entranceFrameId !== 'portal-blue' ||
    Math.abs(repairedPieces[1].wallTextureVStart - 0.4) > 1e-9 ||
    Math.abs(repairedPieces[2].wallTextureVEnd - 1) > 1e-9 ||
    repairedPieces[2].wallTextureRunOrder !== 6 ||
    laterRunSegment.wallTextureRunOrder !== 7) {
    throw new Error('autogenerated cleanup split did not preserve style, V continuity, and run order');
}

if (!html.includes('vTexCoord.x * uTileScale.x + uUOffset') ||
    !html.includes('vTexCoord.y * uTileScale.y + uOffset')) {
    throw new Error('distance-capable shader transform is missing');
}
if (!html.includes('distanceMapping\n                        ? distanceUScale') ||
    !html.includes("Number(seg.wallTextureRunDirection) < 0 ? -1 : 1")) {
    throw new Error('reverse-travel U reflection is not wired into the renderer');
}
for (const field of [
    'wallTextureRunId',
    'wallTextureVStart',
    'wallTextureVEnd',
    'wallTextureUOffset',
    'wallTextureTargetSpan'
]) {
    if (!html.includes(field + ': segmentUsesDistanceWallMapping(seg)')) {
        throw new Error('serialized texture-run field is missing: ' + field);
    }
}
if (!html.includes('Promote Section to Six-Port Junction') ||
    !html.includes("['start', 'Back', roomCapStartCheck]") ||
    !html.includes("['end', 'Forward', roomCapEndCheck]") ||
    !html.includes('junctionCube: seg.rectRoom ? !!seg.junctionCube : undefined')) {
    throw new Error('six-port promotion, forward/back controls, or persistence wiring is missing');
}

console.log(
    'distance texture-run regression passed: snapped spans, U-bends, reverse travel, ' +
    'tube/rect boundaries, sanitizer, split inheritance, shader, and serialization verified'
);
