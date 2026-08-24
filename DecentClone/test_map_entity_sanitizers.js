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

const context = {
    SENTRY_MAX_COUNT: 100,
    SENTRY_MAX_PATROL_POINTS: 256,
    LOOT_ITEM_DEFS: { rocketPack: {} },
    LOOT_RESPAWN_MAX_SECONDS: 86400,
    ROCKET_CACHE_MAX_COUNT: 50,
    builder: {
        right: { x: 1, y: 0, z: 0 },
        down: { x: 0, y: 1, z: 0 },
        forward: { x: 0, y: 0, z: 1 },
        segments: []
    },
    copyVec: value => ({ x: value.x, y: value.y, z: value.z }),
    normalize: value => ({ x: value.x, y: value.y, z: value.z }),
    cross: () => ({ x: 0, y: 0, z: 1 }),
    isFiniteVec: value => !!value && Number.isFinite(value.x) && Number.isFinite(value.y) && Number.isFinite(value.z),
    preservedTextureId: (value, _group, fallback) => value || fallback
};
vm.createContext(context);

for (const name of [
    'makeRocketCacheId',
    'sanitizeRocketCacheList',
    'makeSentryId',
    'uniqueSentryId',
    'sentryForwardAxis',
    'sanitizeSentryPath',
    'sanitizeSentryList'
]) {
    vm.runInContext(extractFunction(name), context);
}

const vector = { x: 1, y: 2, z: 3 };
const longPath = Array.from({ length: 257 }, (_, index) => ({
    point: { x: index, y: 0, z: 0 },
    lingerSec: index === 0 ? Infinity : 1
}));
const validSentry = {
    id: 'same-id',
    packId: 'pack-a',
    mode: 'patrol',
    spawn: { point: vector, right: { x: 1, y: 0, z: 0 }, down: { x: 0, y: 1, z: 0 }, forward: { x: 0, y: 0, z: 1 } },
    path: longPath
};
const duplicateSentry = { ...validSentry, path: [{ point: vector, lingerSec: 2 }] };
const invalidPointSentry = { ...validSentry, id: 'bad-point', spawn: { ...validSentry.spawn, point: { x: 'bad', y: 0, z: 0 } } };
const invalidForwardSentry = { ...validSentry, id: 'bad-forward', spawn: { ...validSentry.spawn, forward: { x: Infinity, y: 0, z: 1 } } };

const sentries = context.sanitizeSentryList([
    validSentry,
    duplicateSentry,
    invalidPointSentry,
    invalidForwardSentry
]);
if (sentries.length !== 2) throw new Error('invalid sentry frames were not rejected');
if (sentries[0].path.length !== 256) throw new Error('257-point patrol path was not bounded to 256');
if (sentries[0].path[0].lingerSec !== 0) throw new Error('non-finite linger time was not reset to zero');
if (sentries[0].id === sentries[1].id) throw new Error('duplicate sentry IDs were not deduplicated');
if (sentries[0].packId !== 'pack-a') throw new Error('valid sentry metadata was not preserved');

const caches = context.sanitizeRocketCacheList([
    { id: 'valid-cache', point: vector, quantity: 2 },
    { id: 'bad-point', point: { x: 'bad', y: 0, z: 0 } },
    { id: 'bad-orientation', point: vector, right: { x: Infinity, y: 0, z: 0 } }
]);
if (caches.length !== 1 || caches[0].id !== 'valid-cache') {
    throw new Error('non-finite rocket-cache vectors were not rejected');
}

console.log('map entity sanitizer regression passed: valid data retained; oversized paths, invalid vectors, and duplicate IDs handled safely');
