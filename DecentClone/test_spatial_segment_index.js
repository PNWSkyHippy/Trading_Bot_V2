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

const context = {
    TUNNEL_SPATIAL_CELL_SIZE: 1200,
    TUNNEL_SPATIAL_MAX_CELLS_PER_SEGMENT: 192,
    tunnelSpatialIndex: { stale: true, cells: new Map(), global: new Set() },
    builder: { radius: 120, segments: [] },
    segmentIsRectRoom: () => false,
    segmentIsChamber: () => false,
    rectRoomDimensions: () => ({ halfWidth: 100, halfHeight: 100, length: 200 }),
    segmentLocalToWorld: (_seg, x, y, z) => ({ x, y, z }),
    chamberCenterPoint: seg => seg.from
};
vm.createContext(context);

for (const name of [
    'tunnelSpatialCellKey',
    'segmentSpatialBounds',
    'rebuildTunnelSpatialIndex',
    'getSpatialSegmentIndicesNearPoint'
]) {
    vm.runInContext(extractFunction(name), context);
}

context.builder.segments = Array.from({ length: 1001 }, (_, index) => ({
    from: { x: index * 240, y: 0, z: 0 },
    to: { x: index * 240 + 180, y: 0, z: 0 },
    radius: 80
}));
context.rebuildTunnelSpatialIndex();

const nearLast = context.getSpatialSegmentIndicesNearPoint({ x: 1000 * 240 + 80, y: 0, z: 0 });
if (!nearLast || !nearLast.has(1000)) throw new Error('the nearby final segment was not indexed');
if (nearLast.has(0)) throw new Error('a distant segment leaked into the local candidate set');
if (nearLast.size >= 20) throw new Error('local candidate set is too broad: ' + nearLast.size);

context.builder.segments.push({
    from: { x: -200000, y: 0, z: 0 },
    to: { x: 200000, y: 0, z: 0 },
    radius: 80
});
context.tunnelSpatialIndex.stale = true;
const withGlobal = context.getSpatialSegmentIndicesNearPoint({ x: 1000 * 240 + 80, y: 0, z: 0 });
if (!withGlobal.has(1001)) throw new Error('oversized segment was not retained in the global safety set');

console.log('spatial segment index regression passed: 1001-segment local query is bounded and oversized geometry stays queryable');
