const fs = require('fs');
const vm = require('vm');

const sourcePath = 'DecentClone/index.html';
const html = fs.readFileSync(sourcePath, 'utf8');
const limitMatch = html.match(/const MAP_IMPORT_MAX_SEGMENTS = (\d+);/);
if (!limitMatch) throw new Error('MAP_IMPORT_MAX_SEGMENTS is missing');

const limit = Number(limitMatch[1]);
if (limit !== 2000) {
    throw new Error(`expected import limit 2000, received ${limit}`);
}

const functionMatch = html.match(
    /function applyTunnelMap\(map, message = 'map loaded'\) \{[\s\S]*?\n        \}/
);
if (!functionMatch) {
    throw new Error('applyTunnelMap boundary is missing');
}

const noop = () => {};
const context = {
    MAP_IMPORT_MAX_SEGMENTS: limit,
    DEFAULT_WALL_TEXTURE_ID: 'wall',
    DEFAULT_RIB_COLOR: '#ffffff',
    tunnelVisualMode: 'textured',
    defaultWallTextureId: 'wall',
    defaultRibColor: '#ffffff',
    defaultWallOpaque: true,
    keyboardStatus: { innerText: '' },
    builder: { radius: 120, bendDeg: 0 },
    mapMouse: {
        selection: { clear: noop },
        targetSelection: { clear: noop }
    },
    rocketCollectedCacheIds: { clear: noop },
    rocketCacheRespawnAt: { clear: noop },
    copyVec: value => ({ ...value }),
    normalize: value => value,
    clampMapSegmentRadius: value => value,
    sanitizeTextureId: value => value || 'wall',
    normalizeHexColor: value => value || '#ffffff',
    sanitizePortalList: () => [],
    sanitizeTargetList: () => [],
    sanitizeRocketCacheList: () => [],
    sanitizeSentryList: () => [],
    invalidateTunnelSegmentCache: noop,
    syncBuilderTargetsFromGeometry: noop,
    clearSelectedRangeBend: noop,
    repairBuilderBasis: noop,
    sanitizeMapSegments: noop,
    rebuildTunnelStars: noop,
    rebuildTunnelTargets: noop,
    rebuildTunnelSentries: noop,
    rebuildRocketCaches: noop,
    resetPlayerCombatState: noop,
    updateWebGLCanvasVisibility: noop,
    placeShipOnLoadedMap: noop,
    loadMiniMapExploration: noop,
    saveTunnelMap: noop,
    frameMapCameraOnTunnel: noop
};
vm.createContext(context);
vm.runInContext(`${functionMatch[0]}; this.applyTunnelMap = applyTunnelMap;`, context);

const segment = () => ({ to: { x: 0, y: 0, z: 0 }, forward: { x: 0, y: 0, z: 1 } });
function assertAccepted(count) {
    const map = { segments: Array.from({ length: count }, segment) };
    if (context.applyTunnelMap(map, 'accepted') !== true) {
        throw new Error(`a ${count}-segment map was not accepted`);
    }
    if (context.builder.segments.length !== count) {
        throw new Error(`the ${count}-segment map did not reach the shared import boundary`);
    }
}

assertAccepted(1001);
assertAccepted(limit);

const sentinel = [{ sentinel: true }];
context.builder.segments = sentinel;
const rejectedMap = { segments: Array.from({ length: limit + 1 }, segment) };
if (context.applyTunnelMap(rejectedMap, 'rejected') !== false) {
    throw new Error('a 2,001-segment map was not rejected');
}
if (context.builder.segments !== sentinel) {
    throw new Error('the rejected map mutated builder.segments');
}
if (!context.keyboardStatus.innerText.includes('2001 segments exceeds import limit 2000')) {
    throw new Error('the rejection did not provide the expected status');
}
if (context.applyTunnelMap({ segments: { length: limit + 1 } }, 'invalid') !== false) {
    throw new Error('a non-array segments representation bypassed structural validation');
}
if (context.builder.segments !== sentinel) {
    throw new Error('invalid map input mutated builder.segments');
}

console.log('map import segment limit regression passed: 1001 and 2000 accepted; 2001 and non-array input rejected before mutation');
