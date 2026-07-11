# Phase Progression: Arcade Classics From The Inside

## Implementation status (2026-07-11)

- **GALAGA 1 of 10 is implemented and playable** inside `index.html`: restricted arcade movement, intro/play/results flow, three enemy waves, bees, butterflies, a boss, enemy fire, shared shield/hull damage, scoring, sprites, and boss special attacks.
- **GALAGA levels 2–10 remain to be designed and implemented.** The existing first stage is the foundation for the nine additional Galaga stages.
- **PAC-MAN levels 1–10 are not implemented.**
- **DEFENDER levels 1–10 are not implemented.**
- Challenge-wave behavior, the deep-space phase, station/repair missions, and the complete tunnels → arcade → deep-space progression loop remain future work.

The complete campaign contains **90 levels** arranged as 30 three-level chapters:

- 30 tunnel levels.
- 30 rotating arcade levels: 10 Galaga, 10 Pac-Man, and 10 Defender.
- 30 space-exploration levels with a station for repairs, buying items, and receiving quests.

The first Galaga stage is the only completed arcade stage so far.

**Vision (Ron, 2026-07-07, campaign sequence clarified 2026-07-11):** the game is a repeating LOOP
of three level types, each chapter harder than the last. The arcade stages are
not bonus rounds — they are **acts in the progression**, with shared lives
and real stakes:

```
TUNNELS phase  →  ARCADE phase  →  DEEP SPACE phase  →  (repeat, tier+1)
 (the core        (rotating:        (space station:
  6DOF crawl)      Galaga →          repairs, missions —
                   Pac-Man →         "help the mining
                   Defender)         colony on Planet X")
```

Arcade phases, rotating one per lap:
1. **GALAGA** — locked looking up, fighter waves swoop and dive-bomb, you can
   only strafe left/right and shoot. They shoot back. They have to.
2. **PAC-MAN** — you ARE Pac-Man, first person inside the maze, eating dots,
   hunted by four ghosts.
3. **DEFENDER** — side-scroller seen from inside the cockpit, flying the
   scroll lane, rescuing pods.

## Campaign sequence

Each numbered chapter contains exactly three levels:

1. A tunnel level.
2. The next arcade level in the repeating Galaga → Pac-Man → Defender rotation.
3. A space-exploration level with a station for repairs, item purchases, and quests.

The opening sequence is:

| Campaign level | Content |
|---:|---|
| 1 | Tunnel 1 |
| 2 | Galaga 1 |
| 3 | Space 1 |
| 4 | Tunnel 2 |
| 5 | Pac-Man 1 |
| 6 | Space 2 |
| 7 | Tunnel 3 |
| 8 | Defender 1 |
| 9 | Space 3 |
| 10 | Tunnel 4 |
| 11 | Galaga 2 |
| 12 | Space 4 |

That pattern continues through Tunnel 30, the tenth level of the appropriate arcade family, and Space 30. The final totals are 30 tunnel + 30 arcade + 30 space levels.

The contrast is the point: the tunnels are full-freedom 6DOF; each arcade
phase *removes* freedoms until it feels like the classic — then hands full
control back. The deep space phase opens the world up wider than ever, then
the next tunnel dive feels claustrophobic again. Rhythm: tight → locked →
vast → tight...

---

## Shared framework (build once, reuse for every bonus level)

**BonusLevelDirector** — one state machine that owns any bonus stage:
`enter → intro card → play (waves / objective) → results card → return`.

- **Entry**: a distinct door portal (gold ring) — reuses the existing
  `portal.door` plumbing. Spawned by main-game triggers (level goals met,
  found in a stash room, etc. — trigger design comes with main game logic).
- **Arena**: constructed on demand in far-away empty space (the engine
  already proved segments at (9000, 9000, 9000) work fine); the player is
  teleported in via portal transit and back to their exact saved main-game
  position/state afterward. Arena segments are tagged and removed on exit.
- **Input gate**: each level type declares which controls pass through
  (Galaga: strafe + fire; Pac-Man: yaw + forward; Defender: fore/aft +
  lift + fire). Everything else is ignored while the mode is active.
- **Stakes — SHARED lives (Ron's call)**: these are progression acts, not
  rewards. Shield/hull carry over; dying in an arcade phase costs a life
  exactly like dying in the tunnels. Score flows to the main leaderboard.
  Repairs happen at the space station between laps — that's the breather.
- **HUD**: auto-switch to `min` HUD mode + a bonus strip (score, wave/
  objective, timer). Restore the player's HUD mode on exit.
- **Difficulty tier**: a single integer, +1 each time the cycle repeats.
  Scales speeds, counts, aggression, timers in every level type.

---

## Level 1: GALAGA (v1 build target)

### Arena and camera
- Dome: one chamber-sphere segment, radius ~1400, spawned in empty space.
- Player pinned near the bottom of the dome, nose locked to the up-axis.
  Camera horizon fixed (no roll/pitch/yaw input) with a slight lateral tilt
  lag while strafing so the cockpit feels alive.
- Starfield/skybox visible through the dome shell (shell mostly transparent
  for this level, or fully open space if the dome reads too "indoors").

### Player (decisions)
- **Strafe: straight line** (classic), ±600u, A/D and arrow keys. A shallow
  arc was considered; straight wins for v1 — pure Galaga muscle memory.
- Fire: existing laser + cooldown. Space/V/RMB all fire.
- No thrust, no rotation. Ship model bobs subtly at idle.

### Fighters (NOT sentries — these are choreography, not AI)
Lightweight entities with four phases:
1. **Entry swoop** — cubic bezier from an off-dome spawn ring to an assigned
   formation slot (Galaga's signature looping entrances).
2. **Formation idle** — grid of slots above the player, breathing gently
   (sine sway, slow expand/contract).
3. **Dive** — peel off on a bezier that sweeps through the player's strafe
   line with lead-targeting; tier 2+ divers release 1–2 slow bolts mid-dive.
4. **Recover** — survivors loop around and rejoin formation (tier 1: exit).

Rendered with the sentry wireframe style: three small silhouettes
(bee / butterfly / boss), color-coded per type.

### Waves (v1)
| Wave | Content | Behavior |
|------|---------|----------|
| 1 | 2×8 bees | dive-only, no shooting |
| 2 | 8 bees + 8 butterflies | butterflies fire bolts on dives |
| 3 | + boss row (4, 2 HP each) | bosses dive in pairs with escorts |
| every 4th | **CHALLENGE WAVE** | pure flyby patterns, nothing attacks — clear all 40 for a perfect bonus (Galaga's challenge stage) |

### Scoring
- Formation kill: 50–150 by type. Diving kill: ×2. Boss: 400 / 800 diving.
- Perfect challenge wave: +10,000. Wave-clear streak multiplier.
- Results card: kills, accuracy, waves, bonus total → main leaderboard.

### Damage (Ron's call: they shoot at you — "have to be")
- Fighter body contact: shield hit + knockback.
- Bolts: shield damage; every wave has shooters from tier 1 (ramped counts,
  slower bolts on the first wave so the player learns the dance).
- Shield → hull → death costs a LIFE, same as the tunnels. Survive the
  phase to reach the space station and repair.

### Tractor beam (decision: design for it, build later)
The boss ship-steal + dual-ship rescue is v2. The fighter phase machine
gets a reserved `special` phase slot now so v2 slots in without rework.

---

## Level 2: PAC-MAN (sketch — build after Galaga ships)

You are Pac-Man. First person, inside the maze.
- **The maze is tunnels** — the engine's core competency. Auto-generate a
  flat classic-layout tunnel grid with the map builder machinery.
- Dots: existing target pickups spaced along tunnel axes; eat by flying
  through. Power pellets glow larger.
- Ghosts: four sentry-derived drones with the classic personalities —
  Blinky (direct chase), Pinky (ambush ahead of you), Inky (flank via
  Blinky mirror), Clyde (approach-then-shy). Power pellet flips them blue
  and vulnerable — ram them through the tunnels.
- Input gate: yaw + forward thrust only (tunnel running, no strafe/lift).
- Win: clear the dots. Timer pressure via tier.

## Level 3: DEFENDER (sketch — build after Pac-Man)

Side-scroller from inside the cockpit.
- Constrained to a vertical plane: fore/aft along the scroll axis + lift,
  world wraps around (a ring corridor — again, the engine has the parts).
- Terrain strip below; abductor drones descend toward pods; grab-and-climb.
  Shoot abductors, catch falling pods for big points, lose pods → mutants
  (faster hunters).
- Camera: nose locked along the scroll direction; the "side view" reading
  comes from the parallax of terrain and targets sliding past.

---

## Third level of every chapter: DEEP SPACE (sketch — needs its own design pass)

The wide-open act between laps. Full 6DOF in open space.
- **Space station**: dock to repair hull/shield (the loop's only repair
  point — this is what makes shared lives across arcade phases fair),
  restock, receive the next mission.
- **Missions**: structured objectives in open space — e.g. "help the mining
  colony on Planet X" (defend miners from raider waves), escort a convoy,
  clear a debris field, recover cargo. One mission per lap, harder each tier.
- **Planets/points of interest**: destinations that give the space lap
  geography. Chambers at planetary scale could serve as landing zones.
- Completing the mission opens the next tunnel entrance — the loop closes.

## Remaining build plan

- **P1 — substantially complete in Galaga level 1**: arcade-mode state, input gate, restricted arena play, phase HUD, three waves with shooters, boss, scoring, and results flow. Portal-driven entry/exit and reusable cross-game director structure still need verification before calling the shared framework complete.
- **P2**: Galaga levels 2–10, including challenge-wave progression and additional difficulty/content design.
- **P3**: Pac-Man levels 1–10.
- **P4**: Defender levels 1–10.
- **P5**: 30 deep-space levels — station, docking/repair, item shop, quests, and escalating exploration missions.
- **P6**: the full 90-level campaign: tunnel → rotating arcade → space, repeated for 30 chapters with difficulty scaling; the campaign state machine owns the current chapter, arcade-family level number, and completion state.

Each phase ships behind its portal/gate — the current game is untouched
until the loop logic is switched on.
