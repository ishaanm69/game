# STARLING — A Gravity Slingshot Puzzle

STARLING is a Pyxel-based space puzzle game. Pull back to aim, release to launch,
and use planetary gravity to guide your probe into the wormhole. The campaign now
contains **three phases and nine sectors**, with escalating environmental hazards,
binary-star systems, wormhole shortcuts, and hidden easter-egg routes.

## Run it

```bash
pip install pyxel
python main.py
```

- Python 3.8+
- Pyxel
- 160×120 resolution, 16-colour palette
- No external art or sound assets; visuals and audio are generated in code.

## Campaign progression

| Phase | Sectors | Difficulty | What you'll encounter |
|---|---:|---|---|
| I — Exploration | 1–3 | Beginner | Core gravity puzzles, first solar flares, introductory pulsars and binary stars |
| II — Turbulence | 4–6 | Intermediate | More frequent hazards, trickier orbital paths and optional wormhole shortcuts |
| III — Singularity | 7–9 | Hard | Layered hazards, faster binary systems, tighter routes and harder-to-find secrets |

### New mechanics

- **Solar flares:** A warning appears about 0.5 seconds before the screen-wide ion
  storm. A probe launched while the flare is active suffers catastrophic navigation
  failure and costs the sector.
- **Pulsar blasts:** Stars periodically charge up, giving a visual warning before
  firing a narrow, full-height vertical beam. Crossing an active beam destroys the
  probe. The interval tightens in later sectors.
- **Binary stars:** Selected sectors contain pairs of gravitational bodies orbiting
  a shared centre. Their moving gravity wells make trajectories change over time.
- **Wormhole shortcuts:** In later sectors, paired portals let a probe enter one
  location and emerge from the other, bypassing sections of the normal route.
- **Secret route:** A very rare off-map upper-left trajectory is an easter egg that
  clears the current sector. It is intentionally difficult to discover.

## Controls

### Campaign

| Input | Action |
|---|---|
| Left mouse: press, drag, release | Aim and launch the probe; a longer pull gives more speed |
| Right mouse (while aiming) | Cancel the current aim |
| `R` | Abort a probe in flight; when aiming, reset the sector |
| Left click / `Space` / `Enter` | Start, continue, or retry from menus |
| `Tab` | Toggle the telemetry/debug overlay |
| `Esc` | Quit |

### Sandbox Lab

| Input | Action |
|---|---|
| `W A S D` or arrow keys | Move |
| `Space` | Pulse in top-down mode; jump in gravity mode |
| Left click | Spawn a crate at the cursor |
| `Shift` + left click | Spawn an orb |
| Right click | Detonate at the cursor |
| `G` | Toggle top-down / gravity mode |
| `R` | Reset the sandbox |
| `Backspace` | Return to the title screen |
| `Tab` | Toggle the telemetry/debug overlay |
| `Esc` | Quit |

## How to play

- Reach the green wormhole to clear a sector.
- You have five probes per sector.
- Planets and stars exert gravity; colliding with a body destroys the probe.
- Flying off-screen normally loses the probe. The hidden upper-left route is the
  exception.
- Collect stars for bonus points. Unused probes also contribute to the sector bonus.
- Watch for the pulsar charge-up and solar-flare warning before committing to a shot.
- Wormholes are optional shortcuts: use them to avoid difficult sections of a route.

## Scoring and completion

Clear all nine sectors to finish the campaign. Your final rank is based on probes
used: **Admiral**, **Navigator**, or **Cadet**. Collecting stars and conserving
probes improves your score.

## Technical notes

The game uses a custom inverse-square gravity model, moving orbital bodies,
trajectory preview, particle effects, screen shake, and procedural chiptune audio.
All gameplay and rendering remain inside the Pyxel 160×120, 16-colour constraints.
