const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');

function extractFunction(name) {
    const start = html.indexOf('function ' + name + '(');
    if (start < 0) throw new Error(name + ' is missing');
    const brace = html.indexOf('{', start);
    let depth = 0;
    for (let i = brace; i < html.length; i++) {
        if (html[i] === '{') depth++;
        if (html[i] === '}' && --depth === 0) return html.slice(start, i + 1);
    }
    throw new Error(name + ' is incomplete');
}

const uploads = new Map();
let boundBuffer = null;
const context = {
    TUNNEL_WEBGL_RADIAL_SEGMENTS: 24,
    TUNNEL_WEBGL_MESH_CACHE_VERSION: 'cap-depth-test',
    Float32Array,
    Uint16Array,
    Math,
    tunnelWebGL: {
        meshCache: new Map(),
        gl: {
            ARRAY_BUFFER: 1,
            ELEMENT_ARRAY_BUFFER: 2,
            STATIC_DRAW: 3,
            createBuffer: () => ({}),
            bindBuffer: (_target, buffer) => { boundBuffer = buffer; },
            bufferData: (_target, data) => uploads.set(boundBuffer, Array.from(data))
        }
    },
    trimCylinderMeshCache: () => {}
};
vm.createContext(context);
vm.runInContext(extractFunction('buildCappedTunnelEndGpuMesh'), context);

const mesh = context.buildCappedTunnelEndGpuMesh(16);
if (mesh.indexCount !== 16 * 3) {
    throw new Error(`cap fan has ${mesh.indexCount} indices; expected 48`);
}
const vertices = uploads.get(mesh.vertexBuffer);
const texCoords = uploads.get(mesh.texCoordBuffer);
if (!vertices || !texCoords || vertices.length !== 18 * 3 || texCoords.length !== 18 * 2) {
    throw new Error('cap mesh did not upload its center and complete rim');
}
if (vertices.slice(0, 3).some(value => value !== 0) || texCoords[0] !== 0.5 || texCoords[1] !== 0) {
    throw new Error('cap center is not anchored to the endpoint texture row');
}
for (let i = 1; i <= 17; i++) {
    const offset = i * 3;
    const radius = Math.hypot(vertices[offset], vertices[offset + 1], vertices[offset + 2]);
    if (Math.abs(radius - 1) > 1e-6) throw new Error('cap rim is not unit radius');
    if (texCoords[i * 2 + 1] !== 0) throw new Error('cap sampled away from its endpoint row');
}
if (!html.includes('renderCappedTunnelEndsWebGL(drawList)') ||
    !html.includes("if (TUNNEL_TEXTURE_MODE === 'webgl' && !segmentIsRoundJunction(seg)) continue;")) {
    throw new Error('ordinary caps can still be painted over WebGL walls by the 2D pass');
}

console.log('WebGL cap-depth path passed: textured cap fan is depth-tested and 2D cap overlays are suppressed for ordinary tubes');
