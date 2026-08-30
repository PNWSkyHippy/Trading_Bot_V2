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
        if (ch === '"' || ch === "'" || ch === '`') {
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
    builder: { length: 100 },
    TUNNEL_SECTION_JOIN_OVERLAP: 18,
    TUNNEL_SEGMENT_JOIN_OVERLAP: 48,
    segmentIsChamber: () => false,
    segmentIsRectRoom: () => false,
    segmentIsRoundJunction: () => false,
    segmentUsesDistanceWallMapping: seg => !!seg.distanceMapped,
    textureUsesSectionMapping: entry => entry?.mapping === 'section',
    getWallTextureEntry: id => id === 'section' ? { mapping: 'section' } : null,
    isOpenSegmentEnd: (seg, end) => !!seg[end + 'Open'],
    segmentEndHasHardTubeTurn: () => true,
    roundJunctionEndpointRenderTrim: () => null
};
vm.createContext(context);
vm.runInContext(extractFunction('getSegmentPanelZExtent'), context);

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

console.log('segment join seam policy passed: ordinary section overlap retained; connector-backed distance run trimmed');
