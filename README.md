# STARLING — a Gravity Slingshot Puzzle (Pyxel)

Drag back, release, and let the planets bend your probe's flight to the wormhole.
Now with **three difficulty phases**, **solar flares**, **pulsars**, **binary stars**,
**shortcut wormholes** and **hidden secrets** that skip a whole sector.
Built on the PIXELBOX / Pyxel stack: 160×120 canvas, 16-color palette, procedural chiptune audio.

## Run it

```bash
pip install -r requirements.txt   # installs pyxel
python main.py                    # or: pyxel run main.py
```

Python 3.8+. No assets to load: all visuals and sounds are generated in code.
`main.py` is self-contained and uses only Pyxel and the standard library.

## Phases

Pick a phase after the title screen. Each has 5 hand-built sectors. Probes are refilled on every retry.

| Phase | Probes / sector | Solar flares | What you meet |
|---|---|---|---|
| **1 BEGINNER** | 6 | rare (every ~11–23 s), 1.2 s long, from sector 2 | the original planets and moons, one slow pulsar, your first shortcut wormhole, your first binary star |
| **2 INTERMEDIATE** | 5 | every ~7–14 s, 1.5 s long | binaries as roadblocks, pulsar lanes, two-moon systems, shortcuts guarded by their own risks |
| **3 HARD** | 4 | every ~4–9 s, 1.8–2 s long | corridors with orbiting moons, up to 3 pulsar lanes at once, two binaries dancing, heavy planets |

Ranks are per phase (fewest probes used across all 5 sectors):

| Phase | Admiral | Navigator | Cadet |
|---|---|---|---|
| Beginner | ≤ 7 | ≤ 11 | more |
| Intermediate | ≤ 9 | ≤ 14 | more |
| Hard | ≤ 12 | ≤ 17 | more |

## Controls

| Input | Action |
|---|---|
| **Left mouse: press, drag, release** | Pull back and fire the probe (further pull = faster) |
| **Right click** (while aiming) | Cancel the aim |
| **W A S D** or **arrow keys** (or d-pad) | Aim with the keyboard: sets the launch direction and power (**Shift** = fine adjust) |
| **Space / Enter** (or gamepad A) | Fire a keyboard aim. Also start, continue, retry |
| **Backspace** (while keyboard-aiming) | Cancel the keyboard aim |
| **R** | Abort a probe in flight. While aiming, resets the sector (−50 if you already fired) |
| **Click / Space** | Start, continue, retry |
| **1 / 2 / 3**, **W / S**, **click** | Phase select |
| **Backspace** | Back (phase select → title, sandbox → title) |
| **Tab** | Toggle the telemetry panel |
| **S** (title screen) | Sandbox Lab |
| **ESC** | Quit |

The **Sandbox Lab** keeps the classic PIXELBOX controls: arrows/WASD move, Space pulses (or jumps),
left click spawns a crate, Shift+click spawns an orb, right click detonates, G toggles gravity mode,
R resets, Backspace returns to the menu.

## How to play

- Reach the green wormhole to clear a sector.
- Planets pull on the probe. Touching one destroys it. Flying off-screen loses it.
- Collect **stars** for +50 each. Unused probes are worth +20 each.
- A dotted preview shows the first moments of your trajectory (including pulsar hits and gate jumps). Judge the rest yourself.

## New mechanics

### Solar flares
At random moments a flare sweeps the whole screen, whether or not a probe is flying.

- **Warning:** 0.5 s before it hits, the screen border flashes, a siren plays and the HUD shows `FLARE`.
- **During the flare:** the screen turns hot and sepia, the aim line and preview turn red.
- **Do not fire.** A probe launched while the flare is active is **fried**. It flickers red, and if it reaches the wormhole (or a secret) the victory is void and you lose the sector (`FLARE DAMAGE`). Wait it out.
- Probes already in flight are shielded. A fried probe can still crash or be lost like any other.

### Pulsars
Violet spinning stars sitting under the HUD. They fire on a fixed beat:

1. **Idle:** a faint dotted lane marks the column they cover.
2. **Charging (0.6 s):** the lane flickers pink. Your cue.
3. **Firing (0.2 s):** the *entire* column, top to bottom, becomes a beam. Anything inside it is destroyed (`ZAPPED`).

Every pulsar has its own period, and your launch time is up to you, so timing a crossing is the puzzle.

### Binary stars
Two suns orbiting their shared centre (a faint ring and link line show the dance).
Heavier stars sit closer to the centre. Touching either one destroys the probe. Thread the gap, or ride their pull.

### Shortcut wormholes
A **magenta** gate is the entrance, a **blue** gate is the exit (a faint dotted line links them).
Fly into the magenta gate and you come out of the blue one **with the same velocity**, skipping whatever lay between.
The catch: stars and secrets usually sit on the long way round, and the exit speed and direction still have to bring you to the goal.
Shortcuts get harder to line up from phase to phase.

### Secrets
Each phase hides several secrets. Find one and the **entire sector is skipped**
(+150 and +20 per probe left, but no star bonus). There are no on-screen markers.
The win screen shows how many you've found in that phase, and the phase screen shows your session total.

## What changed from the previous build

- Added the **phase select** screen and 15 sectors (5 per phase) with per-phase probe counts, flare pacing and ranks.
- Added solar flares, pulsars, binary stars, shortcut wormholes and secrets, with 6 new chiptune effects (flare siren, flare surge, pulsar charge, pulsar beam, warp, secret).
- Added keyboard aiming (WASD / arrows + Space) alongside mouse aiming. Every previous control still works.
- The physics core is now a pure function (`probe_tick`), so every sector can be solved by a headless bot. All 15 sectors, every shortcut and every secret were verified reachable this way.
- Tunable constants stay at the top of `main.py` (`G`, `LAUNCH_K`, `MAX_SPEED`, `FLARE_WARN`, `BEAM_CHARGE`, `BEAM_FIRE`, `PORTAL_R`, …). Sector data, including flare timing, pulsar periods and gate positions, lives in the `BEGINNER` / `INTERMEDIATE` / `HARD` lists.

<details>
<summary><b>Spoilers: where the secrets are (11 total)</b></summary>

| Sector | Secret | How |
|---|---|---|
| Beginner 1 FIRST LIGHT | DEEP SPACE | Leave the map through the **right edge**, between y 96 and 110 (a fast, low shot) |
| Beginner 3 TWIN WELLS | BEACON HACK | Tap the launch beacon **5 times within 2.5 s** without dragging |
| Beginner 5 DOUBLE SUN | GHOST NODE | Invisible node at the **bottom-right corner** (146, 104). Your trail glitches when you're near |
| Intermediate 2 PULSE ALLEY | GHOST NODE | Invisible node at the **top-left** (30, 25) |
| Intermediate 3 CLOCKWORK II | ORBIT LOCK | Swing a full **360° around the central planet** (within 48 px) without dying |
| Intermediate 4 STORM FRONT | DEEP SPACE | Leave through the **top edge**, x between 22 and 34 |
| Hard 1 NEEDLE EYE | GHOST NODE | Invisible node **below and right of the lower planet** (100, 106) |
| Hard 3 DANCING TWINS | ORBIT LOCK | Swing a full **360° around the larger orange sun** (within 70 px) |
| Hard 4 SOLAR STORM | BEACON HACK | Tap the launch beacon **7 times within 2.5 s** |
| Hard 5 SINGULARITY | DEEP SPACE | Leave through the **bottom edge**, x between 70 and 84 |
| Hard 5 SINGULARITY | GHOST NODE | Invisible node at the **bottom-left corner** (8, 110) |

</details>

## PromptCraft

> **Edit this section to match what you actually did.** The prompts below are drafted from this iteration; replace them with your real ones.

### 1. Framing the constraint first
"Pyxel only, 160×120, 16 colors, no external assets, must run with `python main.py`, no crashes. Keep every existing control working (WASD, left/right click, R, Space, ESC)."

### 2. Phases before features
"Before adding anything, split the campaign into beginner, intermediate and hard phases with clearly increasing difficulty." Phases gave every new mechanic a place to be introduced gently and then pushed.

### 3. Specifying mechanics, not just vibes
- Flares: "At random times a flare hits the whole screen, even with no probe flying. Warn the player 0.5 s early. Firing during a flare ruins the probe, and reaching the goal with it costs the level."
- Pulsars: "Stars fire a vertical beam across the whole screen at fixed intervals. Telegraph it, keep it fair."
- Binaries: "Two stars revolving around each other that the probe has to navigate."
- Shortcuts: "Wormhole pairs that skip the hard threats, plus hidden secrets that skip a whole level, like shooting off the map in a particular direction. Make them hard to find."

### 4. Verifying with a bot
"Make the physics a pure function so a headless script can try thousands of launches per sector." Used to confirm every sector, shortcut and secret is reachable and to tune each phase's difficulty.

### What worked
- Telling the AI the hard rules (controls, stack, no assets) before asking for features.
- One mechanic at a time, with exact timings in frames (0.5 s warning = 15 frames).
- Keeping the physics separate from drawing, so a bot could check solvability.

### What didn't (fill in honestly)
- e.g. the first shortcut placements were too easy (80% of aimed shots succeeded) and had to be re-tuned per phase.
- e.g. a secret in the top-right corner of NEEDLE EYE was unreachable until the bot said so.
