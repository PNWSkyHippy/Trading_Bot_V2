const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');

function extractFunction(name) {
    const start = html.indexOf(`function ${name}(`);
    if (start < 0) throw new Error(`${name} is missing`);
    const match = html.slice(start).match(new RegExp(`^function ${name}\\([\\s\\S]*?\\n        \\}`));
    if (!match) throw new Error(`${name} end is missing`);
    return match[0];
}

const confirmed = [];
const context = {
    builder: { radius: 100, segments: [] },
    mapMouse: { anchor: null, selection: { clear() {} } },
    keyboardStatus: { innerText: '' },
    distanceSq: (a, b) => (
        (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2
    ),
    tunnelSegmentsConnected: () => false,
    applyMapGeometryChange: () => {},
    frameMapCameraOnTunnel: () => {},
    window: {
        confirm(message) {
            confirmed.push(message);
            return true;
        }
    }
};
vm.createContext(context);
vm.runInContext(extractFunction('segmentGeometryEndpointsTouch'), context);
vm.runInContext(extractFunction('pruneDisconnectedSegments'), context);

function segment(fromX, toX) {
    return {
        from: { x: fromX, y: 0, z: 0 },
        to: { x: toX, y: 0, z: 0 }
    };
}

// A normal authored chain must not be offered as 548 independent fragments.
context.builder.segments = [segment(0, 100), segment(100, 200), segment(200, 300)];
context.pruneDisconnectedSegments();
if (context.builder.segments.length !== 3) {
    throw new Error('connected authored chain was pruned');
}
if (confirmed.length !== 0) {
    throw new Error('connected authored chain unexpectedly showed a prune confirmation');
}

// One genuinely detached stray remains eligible for removal.
context.builder.segments = [segment(0, 100), segment(100, 200), segment(1000, 1100)];
context.pruneDisconnectedSegments();
if (context.builder.segments.length !== 2) {
    throw new Error('detached stray was not pruned');
}
if (!confirmed[0]?.includes('Keep: 2/3 segment(s)')) {
    throw new Error('prune confirmation did not describe the actual connected component');
}

console.log('disconnected-prune regression passed: connected authored chain retained; detached stray removed');
