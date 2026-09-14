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

const store = new Map();
const context = {
    MAP_LIBRARY_BUNDLE_VERSION: 1,
    TUNNEL_MAP_LIBRARY_KEY: 'test:library',
    TUNNEL_MAP_STORAGE_KEY: 'test:autosave',
    namedMapKey: id => 'test:map:' + id,
    loadMapLibrary: () => {
        const raw = store.get('test:library');
        return raw ? JSON.parse(raw) : [];
    },
    saveMapLibrary: lib => store.set('test:library', JSON.stringify(lib)),
    localStorage: {
        getItem: k => store.get(k),
        setItem: (k, v) => {
            if (k.includes('huge-map')) throw new Error('QuotaExceededError');
            store.set(k, v);
        }
    },
    console: { warn: () => {}, info: () => {}, log: () => {} }
};
vm.createContext(context);
vm.runInContext(extractFunction('importMapLibraryBundle'), context);

const bundle = {
    version: 1,
    library: [
        { id: 'good-map-1', name: 'Good Map 1' },
        { id: 'huge-map-2', name: 'Huge Map 2' },
        { id: 'good-map-3', name: 'Good Map 3' }
    ],
    namedMaps: {
        'good-map-1': { segments: [{ x: 1 }] },
        'huge-map-2': { segments: [{ x: 2 }] },
        'good-map-3': { segments: [{ x: 3 }] }
    }
};

const result = context.importMapLibraryBundle(bundle);
if (!result.ok) throw new Error('bundle import failed');
if (result.maps !== 2) throw new Error('expected 2 maps stored, got ' + result.maps);
console.log('PASS: importMapLibraryBundle handled QuotaExceededError gracefully without crashing');
