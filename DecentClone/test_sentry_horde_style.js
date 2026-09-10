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
    builder: {
        sentries: [
            { id: 'guard-1', label: 'Guard 1', packId: 'patrol-a', mode: 'guard', path: [] },
            { id: 'guard-2', label: 'Guard 2', packId: 'patrol-a', mode: 'guard', path: [] },
            { id: 'leader', label: 'Command Ship', packId: 'patrol-a', mode: 'guard', path: [] }
        ]
    },
    keyboardStatus: { innerText: '' },
    preservedTextureId: (value, _group, fallback) => String(value || '').trim() || fallback,
    sanitizeSentryPath: path => Array.isArray(path) ? path : [],
    rebuildTunnelSentries: () => {},
    saveTunnelMap: () => {}
};
vm.createContext(context);
for (const name of ['findSentryById', 'sentryPackmates', 'sentryPackMembers', 'applySentryEdit']) {
    vm.runInContext(extractFunction(name), context);
}

context.applySentryEdit('guard-1', 'Guard 1', 'guard', [], 'fighter', 'blue_laser', true);
for (const sentry of context.builder.sentries) {
    if (sentry.shipTextureId !== 'fighter' || sentry.effectTextureId !== 'blue_laser') {
        throw new Error('batch Ship/Fire choice did not persist to every horde member');
    }
}

context.applySentryEdit('leader', 'Command Ship', 'guard', [], 'command_ship', 'gold_laser', false);
const leader = context.findSentryById('leader');
const guards = context.builder.sentries.filter(sentry => sentry.id !== 'leader');
if (leader.shipTextureId !== 'command_ship' || leader.effectTextureId !== 'gold_laser') {
    throw new Error('individual horde member could not retain its own Ship/Fire choice');
}
if (guards.some(sentry => sentry.shipTextureId !== 'fighter' || sentry.effectTextureId !== 'blue_laser')) {
    throw new Error('individual customization unexpectedly changed the other patrol members');
}

console.log('sentry horde style regression passed: batch style reaches every member; individual roles remain editable');
