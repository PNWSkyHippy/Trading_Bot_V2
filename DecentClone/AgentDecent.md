# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

---

## Environment

- **Python 3.12** via `venv312` — always activate before running anything
- **Platform:** Windows 11, PowerShell. Machine timezone is **Pacific Time (Spokane, WA)**
  ** main game running on hostnger (in local dns ping for ip) , ssh access to server **
  ** Code here locally git push origin main to publish which will auto push to hostinger **
  ** Never create extra branchs, if cloud based pull files from repo , edit , put back to repo and push 
     to hostinger, but do all on branch main. There are commit backups of every upload in histoty
     so its easy to pull back in time without cluttering up space with tons of branches **
  ** load and execute skill /code-check on every single code change made, be thorough, use integrity,
     take o shortcuts, be honest with that the esults show and recify the before commiting code **

```bash
# Activate venv (PowerShell)
venv312\Scripts\activate

# Or one-liner (use semicolons in PowerShell -c, not newlines)
venv312\Scripts\activate; python bot_engine.py
```

---

## Running the test local server
start-astral.bat start-astral.sh

```bash
# Main game engine
index.html
```

---

## Utility Scripts

## Architecture

### Data Flow


The machine runs Pacific Time. `schedule.at()` calls in `bot_engine.py` use **PT**. Market hours 
checks inside scan functions use `ZoneInfo("America/New_York")` for real ET enforcement. Do not 
conflate the two — always note both times when modifying scheduled jobs. --- **Status: DISABLED** — 
API limit hit April 17, 2026. Resets May 1, 2026.

---

## Pending Work

1. Deevlop main game logic for AI, Goals, graphics
1a. high priority develop opening scren graphics to be displayed imediately to over up this horrible 5 minute delay o tunnel graphs loading
    Lets make  a game logo openig vide montager welcome to Astral Drifdt showing cutaway sceense of action in tunnels, in bonus leve,s im space levels with background musi cgoing
2. Build out 10 levels of the galaga bonus leve, 10 of the pacman bonus level and 10 of the defender bonus level
3. Build out 30 levels of tunnel maps 
4. Build out 30 levels of open space (Space station , ugrades, repair bays, space runner guild taks boards
4a. Develop cino-graphci high res high detail deep space (nebluas , galaxies, black holes, planets, asteroid fields, as predone  images made to be sequenced into mp4 format for
    precorded sequences and simulaed 60fps ray tracing, ie load a scene with wrap around texuture and ray trace every image view in full 360.shown on  vifewfporf format depending where player looks
4b. Develop repair station at space station, repair hull, upgrade rockets, emps, oil slicks, etc quantity and strength based on player level. Devise ship upgrades for cash hull strength laser strength, shield regen speed, ship  accelleration and max speed upgradse.
4c. along these lines Develop strategy for exp VS level gaining  and for cash generation in all tunnel , bonus leve, space level endeavors rewards for accompishments, loot sold at space station collect do missons, coin picked up for loot stashess in game---
4d. Deveop high res custom image tiles for al tunnel and bonus level game walls fllors ceilings. Where possible 
   and appropriate develop still imaged ray trace sequences through the image seuqnces simlulating movement and 
   display as a roll of tiles in game (Tunnels). I want to totally eliminate the problem of gaps where one
   image  begins and another ends by premaking an entire tunnels maps worth of imagry into one big long image sequnece that can be laid down anf ignoe all tunnel segment bounaries all together.

5. Develop the etire  start to finish gameplan,  loading screen, charcter generation, starting map, opening splash screen, beginning game montage video sequence describing
  game play and goals and how to access help ad move about the game. perhaps a tutorial level
6. Revamp and createcustom sound effects utilizing dosplar effect sound technique for all bullet engine,s lasers explosions rocket emisons scrapes bumps, button activate, portal usages
6a. Also develop overal game themr bakground music to be choosable from 1-5 choices or turnred off

## Coding Conventions
- use skill /code-check on every code chage made, no shortcuts, adhere t the skill
- 4-space indentation, no tab
- In PowerShell `-c` commands, use semicolons to separate statements (newlines get scrambled)

