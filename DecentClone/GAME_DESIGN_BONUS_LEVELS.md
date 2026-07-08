# Bonus Levels: Arcade Classics From The Inside

**Vision (Ron, 2026-07-07):** between main levels, a rotating series of bonus
stages that reimagine arcade classics from a first-person cockpit POV:

1. **GALAGA** — locked looking up, fighter waves swoop and dive-bomb, you can
   only strafe left/right and shoot.
2. **PAC-MAN** — you ARE Pac-Man, first person inside the maze, eating dots,
   hunted by four ghosts.
3. **DEFENDER** — side-scroller seen from inside the cockpit, flying the
   scroll lane, rescuing pods.
4. Repeat the cycle at a higher difficulty tier. Forever.

The contrast is the point: the main game is full-freedom 6DOF; each bonus
level *removes* freedoms until it feels like the classic — then hands full
control back when you return.

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
- **Stakes — bonus-isolated (decision)**: no lives lost, ever. Shield acts
  as the "hit points" of the bonus run; if it empties, the run ends early
  ("SHIP DAZED") and you keep the score earned. Bonus score flows into the
  main score/leaderboard. A bonus level is a reward, not a punishment.
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

### Damage (decision: enemies DO fight back, ramped)
- Fighter body contact: shield hit + knockback (never instant death).
- Bolts: shield damage. Shield empty → run ends early, score kept.
- Tier 1 wave 1 is deliberately gentle — the player learns the dance.

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

## Build plan

- **P1**: framework (director, portal entry/exit, input gate, arena
  spawn/teardown, bonus HUD strip) + Galaga dive-only waves 1–2. Playable.
- **P2**: bolts, bosses, challenge wave, scoring polish, results card.
- **P3**: Pac-Man. **P4**: Defender. **P5**: tier scaling + cycle loop.

Every phase ships behind the portal — the main game is untouched until the
player flies into the gold ring.
