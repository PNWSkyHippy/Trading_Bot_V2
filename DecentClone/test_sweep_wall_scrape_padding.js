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

const seg = { radius: 100 };
const context = {
    builder: { radius: 100 },
    shipSegmentIndex: 0,
    posX: 40,
    posY: 0,
    posZ: 0,
    wallHit: { active: false },
    TUNNEL_WEBGL_INTERIOR_NEAR_PAD: 6,
    segmentsWithinTopologyHops: (from, to) => from === to,
    shipSegmentLocal: () => ({ radialDist: Math.abs(context.posX) })
};

vm.createContext(context);
vm.runInContext(extractFunction('webglSegmentNeedsScrapeBoost'), context);
vm.runInContext(extractFunction('sweepTubeRadius'), context);

if (context.sweepTubeRadius(seg, 0) !== 100) {
    throw new Error('sweep radius expanded away from a lateral scrape');
}

context.posX = 90;
if (context.sweepTubeRadius(seg, 0) !== 106) {
    throw new Error('active swept segment did not receive the six-unit near-wall padding');
}
if (context.sweepTubeRadius(seg, 1) !== 100) {
    throw new Error('near-wall padding leaked to a non-owned sweep segment');
}

const sweepRenderer = extractFunction('renderSweepTubesWebGL');
if (!sweepRenderer.includes('sweepTubeRadius(seg, entry.index)')) {
    throw new Error('dynamic sweep radius is missing from the mesh-cache identity');
}

console.log('sweep wall scrape padding passed: active sweep mesh expands only near its own lateral wall');
