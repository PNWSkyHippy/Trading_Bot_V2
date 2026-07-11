# Game Design Document: Project Astral Drift (Working Title)

## 1. Executive Summary & Inspiration
A modern six-degrees-of-freedom (6DOF) spaceship shooter inspired by classic 90s gravity-free tunnel shooters (*Descent*). The game focuses on high-speed motion, light, and perspective, blending claustrophobic mechanical structures with impossibly vast cosmic vistas. 

## 2. The Core Pillars
*   **Impossible Motion:** Full 6DOF flight (pitch, yaw, roll, strafe, vertical/horizontal thrust) with absolutely no fixed up or down. 
*   **Astral Wonder:** A deep emotional hook focused on beauty, disorientation, and the dreamlike feeling of astral travel.
*   **Seamless Transitions:** Bursting out of tight industrial corridors directly into galaxy-scale vistas with zero loading cuts.

## 3. Player Fantasy & Core Loop
The player pilots a highly responsive, nimble ship through asteroid interiors, reactor tunnels, and open-space regions. While combat mirrors the frantic wave-based nature of top-down shooters, it unfolds in a fully 3D, zero-gravity environment.
1.  **Navigate:** Master disorienting 360-degree environments and sharp tunnel drops.
2.  **Survive:** Fight off hostile drone waves entering from side shafts and open-space swarms.
3.  **Explore & Upgrade:** Locate hidden caches to enhance ship capabilities.
4.  **Escape:** Move through increasingly surreal transition routes to reach the next zone.

## 4. Mechanical Specifications

### 4.1. Movement Loop
*   **Controls:** Immediate, crisp, and responsive (never mushy). Must run entirely local on the client with no heavy state systems or server round-trips.
*   **Features:** Dedicated boost for hyperspeed tunnel runs, and precision brake/reverse thrust.
*   **Orientation:** HUD provides optional orientation assistance, but the game world itself has no true floor or ceiling.

### 4.2. Combat & Upgrade Caches
*   **Combat:** Visually rich but mechanically elegant. Features enemy drone waves, bright projectile trails, and charged missile shots.
*   **Upgrade System:** Caches hidden in tunnels incentivize deep exploration. 
    *   *Faster Boost Recharge* / *Wider Weapon Spread*
    *   *Homing Shard Projectiles* / *Temporary Shields*
    *   *Roll-Stabilizer Assist* / *Light-Burst Bombs*

## 5. Signature Visual Moments (Tech Demo Targets)
*   **The Bloom:** Shooting out of a dark tunnel into the sudden, blinding bloom of open space.
*   **Dandelion Splinter:** A weapon projectile splits into a hundred glowing, seed-like fragments that the player can fly directly through as they spiral away.
*   **Hyperspeed Streaks:** Nebula fog and starfields stretch dramatically during maximum boost.
*   **Dissolving Reality:** Walled rooms seamlessly fade into transparent geometry, dissolving entirely into open galaxies.

## 6. Initial Prototype Scope (Phase 1)
To ensure immediate playability, the first prototype will be built as a lightweight browser-based 3D demo:
*   **Engine:** Three.js (or a similar lightweight web-based 3D renderer).
*   **Assets:** One player ship model, one basic tunnel/complex layout, and one open-space transition zone.
*   **Gameplay:** 6DOF movement, basic shooting mechanics, one enemy drone type, and one grabable upgrade cache.
*   **VFX/UI:** Star-streak boost effect and a debug overlay displaying FPS and frame time.

## 7. Creative Identity & Working Titles
*   Astral Drift *(Current Lead)*
*   Tunnelstar
*   No Up But Forward
*   Dandelion Drive
*   Voidvector
*   Dream Velocity

## 8. Release Modes, Custom Maps, And Competitive Integrity

Astral Drift should preserve the freedom of classic save-file editing and
player-created levels without allowing modified JSON to impersonate an official
competitive run. Encrypting browser map/save files is not sufficient because a
client-side decryption key and the running JavaScript can always be inspected or
modified.

### Builder / Developer Edition

Keep the full creative toolchain:

* Map and builder modes.
* JSON library import/export.
* DXF conversion and custom-map loading.
* Developer repair/testing shortcuts.
* Editable saves and custom content.

### Public Player Edition

Official play should hide or disable builder tools, developer shortcuts, and raw
map import from the normal player UI. Official maps should be distributed with a
map ID, version, and digital signature created using a private signing key that
is never shipped in the browser. The game contains only the public verification
key.

If an official map is edited, its signature no longer validates. The game should
still allow it in custom mode, but visibly label the session:

```text
CUSTOM / MODIFIED MAP
Official achievements and leaderboard submission disabled
```

### Leaderboards

A signed map alone cannot make a browser run trustworthy because players can
modify JavaScript or runtime state. Official leaderboard runs should also use a
server-issued session token and server-side validation of map/build version,
score constraints, completion time, and replay/event data. Impossible movement,
damage, firing, item, currency, or scoring patterns should invalidate the run.

Maintain separate categories:

* **Official mode:** signed maps, achievements, and validated leaderboard.
* **Custom mode:** imported/modified maps with a separate community leaderboard
  or no competitive submission.
* **Builder edition:** unrestricted creation, DXF workflow, testing, and modding.

This is intentionally a trust boundary, not an attempt to prevent players from
experimenting with their own offline maps and saves.

---

### 📝 Notes For Future Codex Reference
*   **Project Context:** This is an independent, high-priority creative game prototype for Ron. It is **not** a trading bot feature or a throwaway conversation. Treat this file as a persistent project seed to be preserved and referenced for future development.
*   **The Anchor Feeling:** Never lose the core juxtaposition: old-school 6DOF tunnel-shooter physics combined with modern, dreamlike cosmic speed and beautiful disorientation.
