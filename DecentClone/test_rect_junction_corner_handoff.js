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

const rect = {
    rectRoom: true,
    length: 100,
    roomWidth: 100,
    roomHeight: 80
};

const context = {
    TUNNEL_SAFE_MARGIN: 12,
    builder: { radius: 50, segments: [rect] },
    segmentIsRectRoom: seg => !!seg?.rectRoom,
    segmentIsChamber: () => false,
    rectRoomDistanceState: point => {
        const halfWidth = 50;
        const halfHeight = 40;
        const local = { x: point.x, y: point.y, z: point.z };
        const outsideX = Math.max(0, Math.abs(local.x) - halfWidth);
        const outsideY = Math.max(0, Math.abs(local.y) - halfHeight);
        const outsideZ = local.z < 0 ? -local.z : Math.max(0, local.z - 100);
        return {
            local,
            halfWidth,
            halfHeight,
            outsideDist: Math.hypot(outsideX, outsideY, outsideZ)
        };
    },
    shipSegmentLocal: point => ({ radialDist: Math.hypot(point.x, point.y) })
};
vm.createContext(context);
vm.runInContext(extractFunction('pointWithinSegmentFootprint'), context);
vm.runInContext(extractFunction('pointWithinBubbleJointFootprint'), context);

const cornerBubble = { r: 80, segs: [0] };
const straightBubble = { r: 24, segs: [0] };

if (!context.pointWithinBubbleJointFootprint({ x: 0, y: 0, z: 145 }, cornerBubble)) {
    throw new Error('a centered hard-corner handoff was rejected outside the finite box');
}
if (context.pointWithinBubbleJointFootprint({ x: 80, y: 0, z: 105 }, cornerBubble)) {
    throw new Error('the corner bubble allowed escape through a rectangular side wall');
}
if (context.pointWithinBubbleJointFootprint({ x: 0, y: 70, z: 105 }, cornerBubble)) {
    throw new Error('the corner bubble allowed escape through a rectangular floor or ceiling');
}
if (context.pointWithinBubbleJointFootprint({ x: 0, y: 0, z: 145 }, straightBubble)) {
    throw new Error('a straight tight bubble gained the relaxed corner-only axial handoff');
}

for (const expected of [
    'JELLY_SIZE: 232',
    'MAW_SIZE: 344',
    'JELLY_SIZE: 176',
    'MAW_SIZE: 280'
]) {
    if (!html.includes(expected)) throw new Error('missing requested doubled Gullet size: ' + expected);
}

console.log('rect junction corner handoff regression passed: open turn admitted; side/floor escapes denied; Gullet sizes doubled');
