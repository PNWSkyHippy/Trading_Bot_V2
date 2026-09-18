const fs = require('fs');
const assert = require('assert');

console.log('Testing Tunnel Arcade Systems in DecentClone/index.html...');
const html = fs.readFileSync('DecentClone/index.html', 'utf8');

assert(html.includes('tunnelArcadeFix4'), 'BUILD_ID must contain tunnelArcadeFix4');
console.log('✔ BUILD_ID contains tunnelArcadeFix4');

assert(html.includes('function ensureTunnelMissionSquadrons'), 'ensureTunnelMissionSquadrons must exist');
assert(html.includes('function getActiveTunnelMissionTarget'), 'getActiveTunnelMissionTarget must exist');
assert(html.includes('function checkExitVaultUnlock'), 'checkExitVaultUnlock must exist');
assert(html.includes('function renderTunnelArcadeHud'), 'renderTunnelArcadeHud must exist');
console.log('✔ Core functions exist in source');

const vm = require('vm');

const context = {
    window: { innerWidth: 1280, innerHeight: 720 },
    document: { getElementById: () => ({ innerText: '', style: {}, setAttribute: () => {} }) },
    canvas: { width: 1280, height: 720 },
    keyboardStatus: { innerText: '' },
    performance: { now: () => 1000 },
    Math: Math,
    Date: Date,
    copyVec: (v) => ({ x: v.x, y: v.y, z: v.z }),
    getSegmentMidpoint: (seg) => seg && seg.from && seg.to ? { x: (seg.from.x + seg.to.x) * 0.5, y: (seg.from.y + seg.to.y) * 0.5, z: (seg.from.z + seg.to.z) * 0.5 } : { x: 0, y: 0, z: 0 },
    playSfx: () => {},
    sentryIsActive: (s) => !s.destroyedAt && s.health > 0,
    builder: {
        sentries: [],
        segments: Array.from({ length: 50 }, (_, i) => ({
            from: { x: 0, y: 0, z: i * 140 },
            to: { x: 0, y: 0, z: (i + 1) * 140 },
            forward: { x: 0, y: 0, z: 1 },
            right: { x: 1, y: 0, z: 0 },
            down: { x: 0, y: 1, z: 0 },
            radius: 120
        }))
    },
    tunnelSentries: [],
    tunnelMission: {
        active: true,
        initialized: false,
        keys: { crimson: false, cobalt: false, amber: false },
        keyItems: [],
        bulkheads: []
    },
    tunnelBoss: {
        x: 0, y: 0, z: 0, hp: 1200, maxHp: 1200, shields: 600, maxShields: 600,
        active: false, alive: true, phase: 1, defeatedAt: null, exitPortalPoint: null
    }
};

vm.createContext(context);

function extractFn(fnName) {
    const start = html.indexOf('function ' + fnName + '(');
    if (start < 0) throw new Error(fnName + ' not found');
    let depth = 0;
    let started = false;
    let end = start;
    for (let i = start; i < html.length; i++) {
        if (html[i] === '{') {
            depth++;
            started = true;
        } else if (html[i] === '}') {
            depth--;
            if (started && depth === 0) {
                end = i + 1;
                break;
            }
        }
    }
    return html.substring(start, end);
}

vm.runInContext(extractFn('getActiveTunnelMissionTarget'), context);
vm.runInContext(extractFn('ensureTunnelMissionSquadrons'), context);
vm.runInContext(extractFn('checkExitVaultUnlock'), context);

context.ensureTunnelMissionSquadrons();
assert.strictEqual(context.tunnelSentries.length, 10, 'Expected 10 sentries');
console.log('✔ ensureTunnelMissionSquadrons spawned ' + context.tunnelSentries.length + ' active combat sentries');

const recon = context.tunnelSentries.find(s => s.id.startsWith('forward_recon'));
assert(recon, 'Forward recon drone must exist');
console.log('✔ Forward Recon Drone spawned at z=' + recon.z);

let target = context.getActiveTunnelMissionTarget();
assert.strictEqual(target.type, 'crimson');
console.log('✔ Active Target correctly identified: ' + target.title);

context.tunnelMission.keys.crimson = true;
target = context.getActiveTunnelMissionTarget();
assert.strictEqual(target.type, 'cobalt');
console.log('✔ Target advanced to: ' + target.title);

context.tunnelMission.keys.cobalt = true;
target = context.getActiveTunnelMissionTarget();
assert.strictEqual(target.type, 'amber');
console.log('✔ Target advanced to: ' + target.title);

context.tunnelMission.keys.amber = true;
context.checkExitVaultUnlock();
assert.strictEqual(context.tunnelMission.bulkheads[0].opened, true);
assert.strictEqual(context.tunnelBoss.active, true);
target = context.getActiveTunnelMissionTarget();
assert.strictEqual(target.type, 'boss');
console.log('✔ Vault unlocked, Boss activated, Target advanced to: ' + target.title);

context.tunnelBoss.alive = false;
context.tunnelBoss.defeatedAt = 2000;
context.tunnelBoss.exitPortalPoint = { x: 0, y: 0, z: 7000 };
target = context.getActiveTunnelMissionTarget();
assert.strictEqual(target.type, 'portal');
console.log('✔ Target advanced to: ' + target.title);

console.log('\n★ ALL TUNNEL ARCADE UNIT TESTS PASSED SUCCESSFULLY! ★');
