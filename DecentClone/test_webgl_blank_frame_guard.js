const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync('DecentClone/index.html', 'utf8');

function extractFunction(name) {
    const start = html.indexOf('function ' + name + '(');
    if (start < 0) throw new Error(name + ' is missing');
    const match = html.slice(start).match(
        new RegExp('^function ' + name + '\\([\\s\\S]*?\\n        \\}')
    );
    if (!match) throw new Error(name + ' end is missing');
    return match[0];
}

const context = {
    TUNNEL_WEBGL_BLANK_CHANNEL_MIN: 18,
    Uint8Array
};
vm.createContext(context);
vm.runInContext(extractFunction('webglFrameHasVisibleTunnelSurface'), context);

// Use an explicit function rather than an arrow so the fake can populate the
// output buffer supplied by the extracted WebGL helper.
function glWithSamples(samples, options = {}) {
    let call = 0;
    return {
        drawingBufferWidth: options.width ?? 800,
        drawingBufferHeight: options.height ?? 600,
        RGBA: 1,
        UNSIGNED_BYTE: 2,
        readPixels(...args) {
            if (options.throwOnRead) throw new Error('readback unavailable');
            const out = args[args.length - 1];
            out.set(samples[Math.min(call++, samples.length - 1)] || [0, 0, 0, 255]);
        }
    };
}

const clearOnly = glWithSamples(Array.from({ length: 8 }, () => [5, 5, 8, 255]));
if (context.webglFrameHasVisibleTunnelSurface(clearOnly)) {
    throw new Error('clear-color-only WebGL frame was treated as a visible tunnel');
}

const oneBrightPixel = glWithSamples([
    [32, 32, 32, 255],
    ...Array.from({ length: 7 }, () => [5, 5, 8, 255])
]);
if (context.webglFrameHasVisibleTunnelSurface(oneBrightPixel)) {
    throw new Error('a single bright sample suppressed the blank-frame safeguard');
}

const visibleTunnel = glWithSamples([
    [32, 32, 32, 255],
    [5, 5, 8, 255],
    [22, 26, 30, 255]
]);
if (!context.webglFrameHasVisibleTunnelSurface(visibleTunnel)) {
    throw new Error('two visible wall samples incorrectly triggered blank-frame fallback');
}

if (!context.webglFrameHasVisibleTunnelSurface(glWithSamples([], { throwOnRead: true }))) {
    throw new Error('unavailable readback should retain the established draw-count watchdog');
}
if (!context.webglFrameHasVisibleTunnelSurface(glWithSamples([], { width: 1, height: 1 }))) {
    throw new Error('tiny WebGL buffers should retain the established draw-count watchdog');
}
if (!html.includes('TUNNEL_WEBGL_BLANK_FALLBACK_SAMPLES') ||
    !html.includes('WebGL tunnel presented blank frames — falling back to vector walls')) {
    throw new Error('blank-frame fallback was not wired into the WebGL renderer');
}

console.log('WebGL blank-frame guard passed: clear-only frames fall back; real wall samples and unreadable platforms remain safe');
