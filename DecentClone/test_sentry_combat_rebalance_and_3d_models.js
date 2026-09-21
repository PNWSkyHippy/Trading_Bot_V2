// DecentClone/test_sentry_combat_rebalance_and_3d_models.js
// Regression test verifying combat rebalance, spawn grace period, Defender mini-game isolation,
// tunnel sightline occlusion, and solid 3D faceted gunship mesh specifications.

const fs = require('fs');

for (const target of ['DecentClone/index.html', 'index.html']) {
    console.log(`\n--- Testing ${target} ---`);
    const html = fs.readFileSync(target, 'utf8');

    function assert(cond, msg) {
        if (!cond) {
            console.error('FAIL:', msg);
            process.exit(1);
        }
        console.log('PASS:', msg);
    }

    // 1. Damage Rebalance
    assert(html.includes('SENTRY_SHIELD_DAMAGE = 5'), 'SENTRY_SHIELD_DAMAGE is 5 (reduced from 9)');
    assert(html.includes('SENTRY_SHIELD_DAMAGE_FRONT = 4'), 'SENTRY_SHIELD_DAMAGE_FRONT is 4');
    assert(html.includes('SENTRY_SHIELD_DAMAGE_REAR = 7'), 'SENTRY_SHIELD_DAMAGE_REAR is 7 (halved from 14)');
    assert(html.includes('SENTRY_HULL_DAMAGE = 10'), 'SENTRY_HULL_DAMAGE is 10 (halved from 20)');
    assert(html.includes('SENTRY_PACK_ALERT_RANGE = 220'), 'SENTRY_PACK_ALERT_RANGE is 220 (tightened from 450)');

    // 2. Spawn Protection Grace Period
    assert(html.includes('playerSpawnInvulnUntil = performance.now() + 6000'), '6s spawn invulnerability initialization present');
    assert(html.includes('if (now < playerSpawnInvulnUntil) return;'), 'applySentryDamageToPlayer enforces spawn invulnerability');

    // 3. Defender & Arcade Mini-game Isolation
    assert(html.includes('!defenderPhase.active') && html.includes('flightSentryAiActive'), 'flightSentryAiActive guards against defenderPhase.active');
    assert(html.includes('if (defenderPhase?.active || galagaPhase?.active || gulletPhase?.active) return;'), 'applySentryDamageToPlayer guards against arcade mini-game phases');
    assert(html.includes('sentryBeams.length = 0') && html.includes('sentryMuzzleFlashes.length = 0'), 'startDefenderPhase purges sentry beams and flashes');

    // 4. Mission Squad Spacing
    assert(html.includes('Math.max(6, Math.min(10, Math.floor(n * 0.18)))'), 'Scout drone spaced well down-tunnel');

    // 5. Solid 3D Faceted Gunship Mesh
    assert(html.includes('SENTRY_GUNSHIP_VERTS = {'), 'SENTRY_GUNSHIP_VERTS defined');
    assert(html.includes('SENTRY_GUNSHIP_FACES = SENTRY_RAW_FACES.map'), 'SENTRY_GUNSHIP_FACES precomputed');
    assert(html.includes('getSentrySquadronInfo(sentry)'), 'getSentrySquadronInfo defined');
    assert(html.includes('shadeRgb('), 'shadeRgb lighting helper defined');

    // 6. Tunnel Sightline Occlusion
    assert(html.includes('function tunnelSightlineClear('), 'tunnelSightlineClear implemented');
    assert(html.includes('if (!sentryCorridorVisibleToPlayer(sentry)) continue;'), 'checkLaserSentryHits respects sightlines');
    assert(html.includes('if (!beamSentry || !sentryCorridorVisibleToPlayer(beamSentry)) return;'), 'applySentryBeamImpact respects sightlines');
}

console.log('\nAll combat rebalance, spawn grace, sightline, and 3D model checks passed successfully!');
