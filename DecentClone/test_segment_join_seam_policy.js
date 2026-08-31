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
        if (!quote && ch === '/' && html[i + 1] === '/') {
            i = html.indexOf('\n', i + 2);
            if (i < 0) throw new Error(name + ' comment end is missing');
            continue;
        }
        if (!quote && ch === '/' && html[i + 1] === '*') {
            i = html.indexOf('*/', i + 2);
            if (i < 0) throw new Error(name + ' comment end is missing');
            i++;
            continue;
        }
        if (quote) {
            if (escaped) escaped = false;
            else if (ch === '\\') escaped = true;
            else if (ch === quote) quote = null;
            continue;
        }
        if (ch === '"' || ch === "'") {
            quote = ch;
        } else if (ch === '{') {
            depth++;
        } else if (ch === '}' && --depth === 0) {
            return html.slice(start, i + 1);
        }
    }
    throw new Error(name + ' end is missing');
}

const context = {
    builder: { length: 100, radius: 140, segments: [] },
    TUNNEL_SECTION_JOIN_OVERLAP: 18,
    TUNNEL_SEGMENT_JOIN_OVERLAP: 48,
    TUNNEL_TEXTURE_PANEL_OVERLAP: 1.024,
    TUNNEL_WEBGL_MESH_CACHE_VERSION: 'seam-policy-test',
    segmentIsChamber: () => false,
    segmentIsRectRoom: () => false,
    segmentIsRoundJunction: () => false,
    segmentUsesDistanceWallMapping: seg => !!seg.distanceMapped,
    textureUsesSectionMapping: entry => entry?.mapping === 'section',
    getWallTextureEntry: id => id === 'section' ? { mapping: 'section' } : null,
    isOpenSegmentEnd: (seg, end) => !!seg[end + 'Open'],
    segmentEndHasHardTubeTurn: () => true,
    roundJunctionEndpointRenderTrim: () => null,
    distanceSq: (a, b) => {
        const x = a.x - b.x;
        const y = a.y - b.y;
        const z = a.z - b.z;
        return x * x + y * y + z * z;
    },
    normalize: value => {
        const magnitude = Math.hypot(value.x, value.y, value.z) || 1;
        return { x: value.x / magnitude, y: value.y / magnitude, z: value.z / magnitude };
    },
    scaleVec: (value, amount) => ({ x: value.x * amount, y: value.y * amount, z: value.z * amount }),
    addVec: (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z }),
    lerpVec: (a, b, t) => ({
        x: a.x + (b.x - a.x) * t,
        y: a.y + (b.y - a.y) * t,
        z: a.z + (b.z - a.z) * t
    })
};
vm.createContext(context);
vm.runInContext(extractFunction('getSegmentPanelZExtent'), context);
vm.runInContext(extractFunction('interpolateBendConnectorRadial'), context);
vm.runInContext(extractFunction('textureRunPathConnection'), context);

const uploads = new Map();
let boundBuffer = null;
context.tunnelWebGL = {
    meshCache: new Map(),
    gl: {
        ARRAY_BUFFER: 1,
        ELEMENT_ARRAY_BUFFER: 2,
        STATIC_DRAW: 3,
        createBuffer: () => ({}),
        bindBuffer: (_target, buffer) => { boundBuffer = buffer; },
        bufferData: (_target, data) => {
            if (data && data.BYTES_PER_ELEMENT === 4) uploads.set(boundBuffer, Array.from(data));
        }
    }
};
context.trimCylinderMeshCache = () => {};
vm.runInContext(extractFunction('buildDistanceBendConnectorGpuMesh'), context);

const section = context.getSegmentPanelZExtent({ length: 100, wallTextureId: 'section' });
if (section.zStart !== -18 || section.zEnd !== 118) {
    throw new Error(`ordinary section hard turn lost its sealing overlap: ${section.zStart}..${section.zEnd}`);
}
if (section.trimHardFrom || section.trimHardTo) {
    throw new Error('ordinary section texture was trimmed despite having no bend connector');
}

const distance = context.getSegmentPanelZExtent({ length: 100, distanceMapped: true });
if (distance.zStart !== 0 || distance.zEnd !== 100 || !distance.trimHardFrom || !distance.trimHardTo) {
    throw new Error('distance-mapped hard turn no longer reserves its connector span');
}

const open = context.getSegmentPanelZExtent({
    length: 100,
    wallTextureId: 'section',
    fromOpen: true,
    toOpen: true
});
if (open.zStart !== 0 || open.zEnd !== 100) {
    throw new Error('open section endpoint gained sealing geometry outside its authored span');
}

const rounded = context.interpolateBendConnectorRadial(
    { x: 100, y: 0, z: 0 },
    { x: 0, y: 100, z: 0 },
    0.5,
    100
);
if (Math.abs(Math.hypot(rounded.x, rounded.y, rounded.z) - 100) > 0.0001) {
    throw new Error('smoothed bend connector pinched below the tunnel radius');
}
if (!html.includes('distanceBendSmooth1') || !html.includes('const bendRows = 8')) {
    throw new Error('multi-ring hard-bend connector is missing');
}

function makeBendSegment(from, to, right, down) {
    return {
        from,
        to,
        radius: 140,
        right,
        down,
        forward: {
            x: to.x - from.x,
            y: to.y - from.y,
            z: to.z - from.z
        }
    };
}

function approximatelyEqual(actual, expected, label, tolerance = 0.0001) {
    if (Math.abs(actual - expected) > tolerance) {
        throw new Error(`${label}: expected ${expected}, got ${actual}`);
    }
}

function assertPoint(point, expected, label) {
    approximatelyEqual(point.x, expected.x, `${label}.x`);
    approximatelyEqual(point.y, expected.y, `${label}.y`);
    approximatelyEqual(point.z, expected.z, `${label}.z`);
}

const pointA = { x: 0, y: 0, z: 100 };
const pointB = { x: 80, y: 0, z: 100 };
const bendA = makeBendSegment({ x: 0, y: 0, z: 0 }, pointA, { x: 1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 });
const bendB = makeBendSegment(pointB, { x: 280, y: 0, z: 100 }, { x: 0, y: 0, z: -1 }, { x: 0, y: 1, z: 0 });
context.builder.segments = [bendA, bendB];
const connection = context.textureRunPathConnection(0, 1);
if (connection.error || connection.aEnd !== 'to' || connection.bEnd !== 'from') {
    throw new Error(`80-unit endpoint drift should be accepted, got ${connection.error || JSON.stringify(connection)}`);
}

const driftedInfo = {
    a: { index: 0, seg: bendA },
    b: { index: 1, seg: bendB },
    connection,
    joint: context.lerpVec(pointA, pointB, 0.5)
};
const driftedMesh = context.buildDistanceBendConnectorGpuMesh(driftedInfo, 16);
const driftedVertices = uploads.get(driftedMesh.vertexBuffer);
if (!driftedVertices) throw new Error('fake WebGL did not capture the connector vertex upload');

const radialSegments = 16;
const rowWidth = radialSegments + 1;
const radius = 140 * context.TUNNEL_TEXTURE_PANEL_OVERLAP;
function vertex(vertices, rowIndex, radialIndex) {
    const offset = (rowIndex * rowWidth + radialIndex) * 3;
    return { x: vertices[offset], y: vertices[offset + 1], z: vertices[offset + 2] };
}
function midpoint(a, b) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, z: (a.z + b.z) / 2 };
}

let priorCenterX = -Infinity;
for (let rowIndex = 0; rowIndex <= 8; rowIndex++) {
    const t = rowIndex / 8;
    const expectedCenter = context.lerpVec(pointA, pointB, t);
    const ringCenter = midpoint(vertex(driftedVertices, rowIndex, 0), vertex(driftedVertices, rowIndex, 8));
    assertPoint(ringCenter, expectedCenter, `drifted ring ${rowIndex} center`);
    if (ringCenter.x < priorCenterX - 0.0001) throw new Error('drifted connector centers moved backward');
    priorCenterX = ringCenter.x;
    for (let radialIndex = 0; radialIndex <= radialSegments; radialIndex++) {
        const point = vertex(driftedVertices, rowIndex, radialIndex);
        approximatelyEqual(Math.hypot(
            point.x - expectedCenter.x,
            point.y - expectedCenter.y,
            point.z - expectedCenter.z
        ), radius, `drifted ring ${rowIndex} radius ${radialIndex}`);
    }
}

const firstEndpoint = midpoint(vertex(driftedVertices, 0, 0), vertex(driftedVertices, 0, 8));
const lastEndpoint = midpoint(vertex(driftedVertices, 8, 0), vertex(driftedVertices, 8, 8));
assertPoint(firstEndpoint, pointA, 'drifted first endpoint');
assertPoint(lastEndpoint, pointB, 'drifted last endpoint');

const zeroDriftB = makeBendSegment(pointA, { x: 200, y: 0, z: 100 }, { x: 0, y: 0, z: -1 }, { x: 0, y: 1, z: 0 });
const zeroDriftInfo = {
    a: { index: 2, seg: bendA },
    b: { index: 3, seg: zeroDriftB },
    connection: { aEnd: 'to', bEnd: 'from' },
    joint: pointA
};
const zeroDriftMesh = context.buildDistanceBendConnectorGpuMesh(zeroDriftInfo, 16);
const zeroDriftVertices = uploads.get(zeroDriftMesh.vertexBuffer);
for (let rowIndex = 0; rowIndex <= 8; rowIndex++) {
    const ringCenter = midpoint(vertex(zeroDriftVertices, rowIndex, 0), vertex(zeroDriftVertices, rowIndex, 8));
    assertPoint(ringCenter, pointA, `zero-drift ring ${rowIndex} center`);
}

const cacheShiftA = makeBendSegment({ x: -20, y: 0, z: 0 }, { x: -20, y: 0, z: 100 }, { x: 1, y: 0, z: 0 }, { x: 0, y: 1, z: 0 });
const cacheShiftB = makeBendSegment({ x: 100, y: 0, z: 100 }, { x: 300, y: 0, z: 100 }, { x: 0, y: 0, z: -1 }, { x: 0, y: 1, z: 0 });
const shiftedMesh = context.buildDistanceBendConnectorGpuMesh({
    a: { index: 0, seg: cacheShiftA },
    b: { index: 1, seg: cacheShiftB },
    connection: { aEnd: 'to', bEnd: 'from' },
    joint: driftedInfo.joint
}, 16);
if (shiftedMesh === driftedMesh) {
    throw new Error('connector cache reused a midpoint-matched mesh after its endpoints changed');
}

const reframedA = makeBendSegment(
    { x: 0, y: 0, z: 0 },
    pointA,
    { x: 0, y: 1, z: 0 },
    { x: -1, y: 0, z: 0 }
);
const reframedMesh = context.buildDistanceBendConnectorGpuMesh({
    a: { index: 0, seg: reframedA },
    b: { index: 1, seg: bendB },
    connection,
    joint: driftedInfo.joint
}, 16);
if (reframedMesh === driftedMesh) {
    throw new Error('connector cache reused a mesh after an endpoint frame changed');
}

console.log('segment join seam policy passed: ordinary overlap retained; connector-backed run trimmed; bend endpoints, radius, and cache identity preserved');
