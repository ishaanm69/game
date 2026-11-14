"""STARLING - a gravity-slingshot puzzle game built on Pyxel.

Drag to aim, release to launch (or aim with WASD / arrows and fire with SPACE).
Planets bend your probe's path. Reach the wormhole before you run out of probes.
Three phases (BEGINNER / INTERMEDIATE / HARD) of five sectors each, with:
  * solar flares   - the whole screen is hit at random; firing during one fries the probe
  * pulsars        - stars that fire an instant vertical beam at fixed intervals
  * binary stars   - two suns orbiting each other
  * shortcut wormholes - magenta gate in, blue gate out, skips the nasty part
  * hidden secrets - find them and a whole sector is skipped
Plus the SANDBOX LAB with the classic PIXELBOX controls.
Run with:  python main.py
"""
import math
import random

import pyxel

W, H = 160, 120
G = 1.25            # gravity strength
MAX_DRAG = 40.0     # max pull-back distance in pixels
LAUNCH_K = 0.13     # drag distance -> launch speed
MAX_SPEED = 6.0
FLIGHT_LIMIT = 420  # frames before a probe runs out of fuel
GOAL_R = 7
PREVIEW_STEPS = 45
KEY_AIM_SPEED = 0.11   # launch-velocity change per frame when aiming with WASD / arrows

# ---- hazards
FLARE_WARN = 15     # frames of warning before a flare (0.5 s at 30 fps)
BEAM_CHARGE = 18    # frames a pulsar glows before it fires
BEAM_FIRE = 6       # frames the beam stays lethal
BEAM_HALF = 2.5     # beam half-width in pixels
PULSAR_Y = 12       # emitters sit just under the HUD
PORTAL_R = 5        # shortcut wormhole capture radius
PORTAL_COOLDOWN = 16  # substeps before a probe can enter a gate again


def body(x, y, r, m, c, rim, orbit=None):
    """A gravity body. orbit = (cx, cy, radius, angular_speed, phase) for moons."""
    return {"x": x, "y": y, "r": r, "m": m, "c": c, "rim": rim, "orbit": orbit, "mate": None}


def binary(cx, cy, sep, w, ph, a, b):
    """Two suns circling their common centre. a, b = (radius, mass, colour, rim)."""
    ra, ma, ca, ria = a
    rb, mb, cb, rib = b
    da = sep * mb / (ma + mb)
    db = sep * ma / (ma + mb)
    sa = body(0, 0, ra, ma, ca, ria, orbit=(cx, cy, da, w, ph))
    sb = body(0, 0, rb, mb, cb, rib, orbit=(cx, cy, db, w, ph + math.pi))
    sa["mate"] = sb
    sb["mate"] = sa
    return [sa, sb]


# ---- secrets (easter eggs). Each one skips the whole sector when found.
def egg_edge(side, lo, hi, label):
    """Leave the map through one narrow stretch of one edge."""
    return {"type": "edge", "side": side, "lo": lo, "hi": hi, "label": label}


def egg_ghost(x, y, label, r=4):
    """An invisible node. The probe's trail glitches when it gets close."""
    return {"type": "ghost", "x": x, "y": y, "r": r, "label": label}


def egg_lap(body_i, reach, label):
    """Swing a full 360 degrees around one body without dying."""
    return {"type": "lap", "body": body_i, "reach": reach, "label": label}


def egg_taps(n, label):
    """Tap the launch beacon n times, fast, without launching."""
    return {"type": "taps", "n": n, "label": label}


def lvl(name, start, goal, bodies, stars, pulsars=(), portals=(), eggs=(), flare=None):
    """pulsars = (x, period_frames, phase_frames); flare = (min_gap, max_gap, duration) in frames."""
    return dict(name=name, start=start, goal=goal, bodies=bodies, stars=list(stars),
                pulsars=[dict(x=x, period=p, phase=ph) for x, p, ph in pulsars],
                portals=[(tuple(a), tuple(b)) for a, b in portals],
                eggs=list(eggs), flare=flare)


# ---------------------------------------------------------------- the three phases
BEGINNER = [
    lvl("FIRST LIGHT", (18, 100), (140, 24),
        [body(85, 82, 8, 70, 12, 6)],
        [(60, 52), (112, 60)],
        eggs=[egg_edge("right", 96, 110, "DEEP SPACE")]),
    lvl("SLINGSHOT", (15, 60), (145, 60),
        [body(80, 60, 12, 140, 9, 10)],
        [(80, 26), (80, 94)],
        flare=(450, 700, 36)),
    lvl("TWIN WELLS", (15, 100), (145, 22),
        [body(60, 50, 8, 80, 3, 11), body(110, 85, 10, 100, 2, 14)],
        [(85, 66), (132, 48)],
        portals=[((35, 81), (117, 37))],
        eggs=[egg_taps(5, "BEACON HACK")],
        flare=(420, 660, 36)),
    lvl("CLOCKWORK", (15, 105), (145, 20),
        [body(80, 75, 7, 90, 8, 14),
         body(0, 0, 3, 22, 6, 7, orbit=(80, 75, 27, 0.05, 0.0))],
        [(80, 30), (40, 60)],
        pulsars=[(116, 120, 0)],
        flare=(380, 620, 36)),
    lvl("DOUBLE SUN", (14, 100), (146, 26),
        binary(85, 62, 36, 0.045, 0.5, (6, 55, 10, 9), (5, 45, 8, 14)),
        [(85, 28), (85, 96)],
        portals=[((36, 88), (120, 41))],
        eggs=[egg_ghost(146, 104, "GHOST NODE")],
        flare=(330, 540, 36)),
]

INTERMEDIATE = [
    lvl("BINARY ROAD", (12, 60), (148, 60),
        binary(80, 60, 44, -0.05, 0.0, (7, 70, 9, 10), (7, 70, 12, 6)),
        [(80, 22), (80, 98)],
        pulsars=[(108, 100, 20)],
        portals=[((39, 68), (122, 63))],
        flare=(240, 420, 45)),
    lvl("PULSE ALLEY", (12, 95), (148, 28),
        [body(50, 42, 7, 70, 12, 6), body(95, 92, 9, 95, 2, 14)],
        [(72, 70), (116, 50)],
        pulsars=[(72, 90, 0), (116, 105, 40)],
        portals=[((33, 73), (134, 54))],
        eggs=[egg_ghost(30, 25, "GHOST NODE")],
        flare=(240, 420, 45)),
    lvl("CLOCKWORK II", (14, 104), (146, 20),
        [body(80, 70, 8, 110, 8, 14),
         body(0, 0, 3, 18, 6, 7, orbit=(80, 70, 26, 0.055, 0.0)),
         body(0, 0, 3, 18, 13, 7, orbit=(80, 70, 40, -0.035, 2.0))],
        [(80, 28), (40, 60), (112, 100)],
        pulsars=[(108, 110, 30)],
        portals=[((22, 59), (134, 58))],
        eggs=[egg_lap(0, 48, "ORBIT LOCK")],
        flare=(240, 420, 45)),
    lvl("STORM FRONT", (12, 100), (148, 22),
        [body(60, 70, 10, 120, 9, 10)] + binary(105, 50, 28, 0.065, 0.0, (5, 45, 10, 9), (5, 45, 8, 14)),
        [(60, 30), (84, 100)],
        pulsars=[(84, 90, 10), (132, 70, 0)],
        portals=[((30, 86), (118, 34))],
        eggs=[egg_edge("top", 22, 34, "DEEP SPACE")],
        flare=(210, 360, 45)),
    lvl("EVENT HORIZON", (12, 105), (148, 16),
        binary(60, 70, 34, 0.05, 0.0, (6, 60, 9, 10), (6, 60, 12, 6))
        + binary(110, 45, 26, -0.07, 1.0, (5, 45, 10, 9), (5, 45, 8, 14)),
        [(84, 30), (30, 40)],
        pulsars=[(84, 85, 0)],
        portals=[((34, 92), (108, 78))],
        flare=(210, 360, 45)),
]

HARD = [
    lvl("NEEDLE EYE", (12, 60), (148, 60),
        [body(80, 34, 10, 130, 9, 10), body(80, 86, 10, 130, 2, 14),
         body(0, 0, 3, 22, 6, 7, orbit=(80, 60, 14, 0.09, 0.0))],
        [(80, 60), (110, 60)],
        pulsars=[(44, 75, 0), (114, 60, 20)],
        portals=[((39, 54), (132, 51))],
        eggs=[egg_ghost(100, 106, "GHOST NODE")],
        flare=(150, 280, 54)),
    lvl("CROSSFIRE", (12, 100), (148, 20),
        [body(55, 62, 8, 85, 3, 11), body(110, 76, 9, 100, 9, 10)],
        [(84, 40), (130, 100)],
        pulsars=[(40, 70, 0), (84, 80, 25), (130, 90, 50)],
        portals=[((26, 95), (106, 44))],
        flare=(150, 280, 54)),
    lvl("DANCING TWINS", (12, 60), (148, 60),
        binary(60, 60, 40, 0.06, 0.0, (7, 70, 9, 10), (6, 55, 12, 6))
        + binary(110, 60, 30, -0.08, 1.5, (6, 55, 8, 14), (5, 40, 3, 11)),
        [(85, 28), (85, 92)],
        pulsars=[(85, 100, 0), (134, 80, 40)],
        portals=[((25, 30), (129, 87))],
        eggs=[egg_lap(0, 70, "ORBIT LOCK")],
        flare=(150, 280, 54)),
    lvl("SOLAR STORM", (12, 104), (148, 18),
        [body(80, 64, 11, 150, 2, 14), body(0, 0, 3, 24, 6, 7, orbit=(80, 64, 30, 0.06, 0.0))]
        + binary(122, 38, 20, 0.1, 0.0, (4, 40, 10, 9), (4, 40, 8, 14)),
        [(40, 40), (100, 100)],
        pulsars=[(100, 75, 0)],
        portals=[((45, 97), (138, 68))],
        eggs=[egg_taps(7, "BEACON HACK")],
        flare=(120, 240, 60)),
    lvl("SINGULARITY", (12, 60), (148, 60),
        [body(45, 30, 7, 70, 12, 6), body(45, 90, 7, 70, 9, 10)]
        + binary(100, 60, 34, 0.065, 0.0, (6, 60, 10, 9), (6, 60, 8, 14))
        + [body(0, 0, 3, 20, 6, 7, orbit=(45, 60, 18, 0.1, 0.0))],
        [(75, 60), (125, 30), (125, 90)],
        pulsars=[(72, 65, 0), (124, 85, 30)],
        portals=[((18, 76), (130, 39))],
        eggs=[egg_edge("bottom", 70, 84, "DEEP SPACE"), egg_ghost(8, 110, "GHOST NODE")],
        flare=(120, 240, 60)),
]


def make_phase(name, tag, shots, ranks, col, blurb, levels):
    return dict(name=name, tag=tag, shots=shots, ranks=ranks, col=col, blurb=blurb,
                levels=levels, stars=sum(len(lv["stars"]) for lv in levels),
                secrets=sum(len(lv["eggs"]) for lv in levels))


PHASES = [
    make_phase("BEGINNER", "I", 6, (7, 11), 11, "FLARES, 1 PULSAR, TWINS", BEGINNER),
    make_phase("INTERMEDIATE", "II", 5, (9, 14), 10, "BINARIES AND PULSE LANES", INTERMEDIATE),
    make_phase("HARD", "III", 4, (12, 17), 8, "EVERYTHING AT ONCE", HARD),
]



# 3x5 pixel glyphs for the title logo
GLYPHS = {
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "A": ("111", "101", "111", "101", "101"),
    "R": ("110", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "I": ("111", "010", "010", "010", "111"),
    "N": ("101", "111", "111", "111", "101"),
    "G": ("111", "100", "101", "101", "111"),
}


# ---------------------------------------------------------------- sandbox lab assets
SPRITES = {  # 8x8 hex-digit sprites: each char is a Pyxel palette index, 0 = transparent
    "bot_idle": ("00cccc00", "0c7cc7c0", "0cccccc0", "00c66c00",
                 "0cccccc0", "0c0cc0c0", "00c00c00", "00500500"),
    "bot_run": ("00cccc00", "0c7cc7c0", "0cccccc0", "00c66c00",
                "0cccccc0", "00cccc00", "0c0000c0", "05000050"),
    "crate": ("44444444", "49999994", "49499494", "49944994",
              "49944994", "49499494", "49999994", "44444444"),
    "orb": ("00cccc00", "0c7766c0", "c776666c", "c766666c",
            "c666666c", "c666666c", "0c6666c0", "00cccc00"),
}
AL, AR, AT, AB = 4, 156, 11, 116   # sandbox arena bounds
MAX_OBJS = 40
BLAST_R = 22
PULSE_R = 36


def draw_sprite(name, x, y, flip=False):
    for j, row in enumerate(SPRITES[name]):
        for i, ch in enumerate(row):
            if ch != "0":
                pyxel.pset(int(x) + (7 - i if flip else i), int(y) + j, int(ch, 16))



# ---------------------------------------------------------------- physics
def body_pos(b, t):
    if b["orbit"]:
        cx, cy, rad, w, ph = b["orbit"]
        a = ph + w * t
        return cx + math.cos(a) * rad, cy + math.sin(a) * rad
    return b["x"], b["y"]


def accel(px, py, bodies, t):
    ax = ay = 0.0
    for b in bodies:
        bx, by = body_pos(b, t)
        dx, dy = bx - px, by - py
        d2 = dx * dx + dy * dy
        d = math.sqrt(d2)
        if d < 1:
            continue
        f = G * b["m"] / max(d2, 64.0)
        ax += f * dx / d
        ay += f * dy / d
    return ax, ay


def pulsar_phase(pl, t):
    """0 = idle, 1 = charging (visible warning), 2 = firing (lethal)."""
    k = (int(t) + pl["phase"]) % pl["period"]
    if k >= pl["period"] - BEAM_FIRE:
        return 2
    if k >= pl["period"] - BEAM_FIRE - BEAM_CHARGE:
        return 1
    return 0


def new_probe(x, y, vx, vy):
    return {"x": float(x), "y": float(y), "vx": vx, "vy": vy, "cd": 0, "age": 0,
            "warp": None, "warps": 0, "lap": 0.0, "lap_prev": None, "fried": False}


def step(s, t, lv):
    """Advance probe dict s one frame (two substeps).
    Returns None, 'hit' (body) or 'beam' (pulsar). s['warp'] = gate index if it teleported."""
    hit = None
    s["warp"] = None
    bodies = lv["bodies"]
    for k in range(2):
        tt = t + k * 0.5
        ax, ay = accel(s["x"], s["y"], bodies, tt)
        s["vx"] += ax * 0.5
        s["vy"] += ay * 0.5
        sp = math.hypot(s["vx"], s["vy"])
        if sp > MAX_SPEED:
            s["vx"] *= MAX_SPEED / sp
            s["vy"] *= MAX_SPEED / sp
        s["x"] += s["vx"] * 0.5
        s["y"] += s["vy"] * 0.5
        for b in bodies:
            bx, by = body_pos(b, tt)
            if (s["x"] - bx) ** 2 + (s["y"] - by) ** 2 < (b["r"] + 1.5) ** 2:
                hit = "hit"
        for pl in lv["pulsars"]:
            if s["y"] > PULSAR_Y - 3 and abs(s["x"] - pl["x"]) <= BEAM_HALF and pulsar_phase(pl, tt) == 2:
                hit = hit or "beam"
        if s["cd"] > 0:
            s["cd"] -= 1
        elif not hit:
            for i, (a, b2) in enumerate(lv["portals"]):
                if (s["x"] - a[0]) ** 2 + (s["y"] - a[1]) ** 2 < PORTAL_R ** 2:
                    s["x"], s["y"] = float(b2[0]), float(b2[1])
                    s["cd"] = PORTAL_COOLDOWN
                    s["warp"] = i
                    break
    return hit


def probe_tick(p, t, lv):
    """One frame of flight. Returns a list of events:
    ('warp', i), then at most one of ('hit',) ('beam',) ('goal',) ('egg', i) ('lost', side)."""
    events = []
    hit = step(p, t, lv)
    p["age"] += 1
    if p["warp"] is not None:
        p["warps"] += 1
        events.append(("warp", p["warp"]))
    if hit:
        events.append((hit,))
        return events
    x, y = p["x"], p["y"]
    if math.hypot(x - lv["goal"][0], y - lv["goal"][1]) < GOAL_R:
        events.append(("goal",))
        return events
    for i, e in enumerate(lv["eggs"]):
        kind = e["type"]
        if kind == "ghost":
            if math.hypot(x - e["x"], y - e["y"]) < e["r"]:
                events.append(("egg", i))
                return events
        elif kind == "lap":
            bx, by = body_pos(lv["bodies"][e["body"]], t)
            if math.hypot(x - bx, y - by) < e["reach"]:
                a = math.atan2(y - by, x - bx)
                if p["lap_prev"] is not None:
                    p["lap"] += (a - p["lap_prev"] + math.pi) % math.tau - math.pi
                p["lap_prev"] = a
                if abs(p["lap"]) >= math.tau:
                    events.append(("egg", i))
                    return events
            else:
                p["lap_prev"] = None
    side = None
    if x < -15:
        side = "left"
    elif x > W + 15:
        side = "right"
    elif y < -15:
        side = "top"
    elif y > H + 15:
        side = "bottom"
    if side:
        c = y if side in ("left", "right") else x
        for i, e in enumerate(lv["eggs"]):
            if e["type"] == "edge" and e["side"] == side and e["lo"] <= c <= e["hi"]:
                events.append(("egg", i))
                return events
        events.append(("lost", side))
    elif p["age"] > FLIGHT_LIMIT:
        events.append(("lost", "fuel"))
    return events



def stext(x, y, s, col, sh=1):
    pyxel.text(x + 1, y + 1, s, sh)
    pyxel.text(x, y, s, col)


def ctext(y, s, col, sh=1):
    stext((W - len(s) * 4) // 2, y, s, col, sh)


def big_text(x, y, s, px, top, bottom, shadow):
    for dx, dy, shade in ((px // 2 + 1, px // 2 + 1, True), (0, 0, False)):
        cx = x
        for ch in s:
            for ry, row in enumerate(GLYPHS[ch]):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        col = shadow if shade else (top if ry < 3 else bottom)
                        pyxel.rect(cx + rx * px + dx, y + ry * px + dy, px, px, col)
            cx += 4 * px


def panel(x, y, w, h):
    pyxel.rect(x, y, w, h, 1)
    pyxel.rectb(x, y, w, h, 7)
    pyxel.rectb(x + 2, y + 2, w - 4, h - 4, 5)


def draw_body(b, bx, by):
    r = b["r"]
    if r >= 6:
        pyxel.circb(bx, by, int(r * 2.3), 1)  # gravity field hint
    pyxel.circ(bx, by, r, b["c"])
    pyxel.circb(bx, by, r, b["rim"])
    pyxel.pset(bx - r // 3, by - r // 3, 7)   # highlight
    if r >= 8:
        pyxel.pset(bx - r // 3 + 1, by - r // 3, 7)
        pyxel.line(bx - r + 2, by + 1, bx + r - 2, by + 1, b["rim"])  # band


class Game:
    def __init__(self):
        pyxel.init(W, H, title="STARLING", fps=30)
        pyxel.mouse(True)
        self.init_sounds()
        rnd = random.Random(7)
        self.bg = [(rnd.randrange(W), rnd.randrange(H),
                    rnd.choice((1, 1, 5, 13)), rnd.randrange(60)) for _ in range(55)]
        self.particles = []
        self.texts = []
        self.shake = 0
        self.flash = 0
        self.state = "title"
        self.state_t = 0
        self.tele = False
        self.sb = None
        self.sel = 0                  # highlighted phase on the phase screen
        self.last_mouse = (0, 0)
        self.found = set()            # (phase, level, egg) secrets discovered this session
        self.new_run(0)
        self.sb_reset()
        pyxel.play(3, 4, loop=True)
        pyxel.run(self.update, self.draw)

    # ------------------------------------------------------------ audio
    def init_sounds(self):
        s = pyxel.sounds
        s[0].set("c2g2c3", "s", "5", "f", 4)               # launch
        s[1].set("e3b3e4", "p", "6", "n", 5)               # star pickup
        s[2].set("g1e1c1c1", "n", "7531", "f", 12)         # crash
        s[3].set("c3e3g3c4g3c4", "s", "6", "n", 8)         # level clear
        s[4].set("c2rrrg1rrrf1rrrg1rrr", "t", "2", "n", 30)  # ambient loop
        s[5].set("c3a2f2c2", "t", "6", "v", 10)            # lost / abort
        s[6].set("a3", "p", "3", "n", 2)                   # aim tick
        s[7].set("a3e3a3e3a3e3", "s", "5", "v", 3)         # solar flare warning siren
        s[8].set("c3e3g3c4", "t", "2", "n", 5)             # pulsar charging
        s[9].set("c4c2", "n", "5", "f", 6)                 # pulsar beam
        s[10].set("c3g3c4e4g4", "p", "5", "f", 3)          # wormhole shortcut
        s[11].set("c3e3g3c4e4g4c4", "s", "6", "f", 6)      # secret found
        s[12].set("a1g1f1e1", "n", "6", "v", 8)            # flare surge / probe fried

    # ------------------------------------------------------------ state
    def new_run(self, phase_idx=0):
        self.phase_idx = phase_idx
        self.phase = PHASES[phase_idx]
        self.level_idx = 0
        self.score = 0
        self.total_shots = 0
        self.stars_total = 0
        self.load_level(0, keep_state=True)

    def load_level(self, i, keep_state=False):
        lv = self.phase["levels"][i]
        self.lv = lv
        self.level_idx = i
        self.name = lv["name"]
        self.start = lv["start"]
        self.goal = lv["goal"]
        self.bodies = lv["bodies"]
        self.stars = [{"x": x, "y": y, "got": False} for x, y in lv["stars"]]
        self.max_shots = self.phase["shots"]
        self.shots = self.max_shots
        self.level_stars = 0
        self.t = 0
        self.probe = None
        self.trail = []
        self.aim = None
        self.kv = None                # keyboard aim: launch velocity set with WASD
        self.dead_timer = 0
        self.bonus = 0
        self.secret = None            # label of the secret that skipped this sector
        self.warped = False
        self.taps = []
        self.fail_lines = ("SIGNAL LOST", "OUT OF PROBES")
        self.pprev = [0] * len(lv["pulsars"])
        self.fl_state = 0             # 0 calm, 1 warning, 2 flare active
        self.fl_dur = 0
        self.fl_timer = random.randint(lv["flare"][0], lv["flare"][1]) if lv["flare"] else 0
        if not keep_state:
            self.state = "play"
            self.state_t = 0

    @staticmethod
    def confirm():
        return (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN))

    def phase_secrets(self, idx):
        return sum(1 for k in self.found if k[0] == idx)

    # ------------------------------------------------------------ fx
    def burst(self, x, y, n, cols, speed=2.0, life=20):
        for _ in range(n):
            a = random.random() * math.tau
            sp = random.random() * speed + 0.3
            self.particles.append([x, y, math.cos(a) * sp, math.sin(a) * sp,
                                   life + random.randint(-6, 6), random.choice(cols)])

    def add_text(self, x, y, s, col):
        self.texts.append([x, y, s, col, 30])

    def update_fx(self):
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[2] *= 0.94
            p[3] *= 0.94
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for t in self.texts:
            t[1] -= 0.5
            t[4] -= 1
        self.texts = [t for t in self.texts if t[4] > 0]
        if self.shake > 0:
            self.shake -= 1
        if self.flash > 0:
            self.flash -= 1

    # ------------------------------------------------------------ update
    def update(self):
        self.state_t += 1
        self.update_fx()
        if pyxel.btnp(pyxel.KEY_TAB):
            self.tele = not self.tele
        if self.state == "title":
            if pyxel.btnp(pyxel.KEY_S):
                self.sb_reset()
                self.state = "sandbox"
                self.state_t = 0
            elif self.confirm():
                self.state = "phase"
                self.state_t = 0
                self.last_mouse = (pyxel.mouse_x, pyxel.mouse_y)
        elif self.state == "phase":
            self.update_phase()
        elif self.state == "sandbox":
            self.update_sandbox()
        elif self.state == "play":
            self.update_play()
        elif self.state == "clear":
            if self.state_t > 15 and self.confirm():
                if self.level_idx + 1 >= len(self.phase["levels"]):
                    self.state = "win"
                    self.state_t = 0
                    self.flash = 3
                else:
                    self.load_level(self.level_idx + 1)
        elif self.state == "fail":
            if self.state_t > 15 and self.confirm():
                self.load_level(self.level_idx)
        elif self.state == "win":
            if self.state_t > 20 and self.confirm():
                self.state = "phase"
                self.state_t = 0
                self.sel = min(self.phase_idx + 1, len(PHASES) - 1)

    # ------------------------------------------------------------ phase select
    @staticmethod
    def phase_panel(i):
        return 10, 20 + i * 29, 140, 26

    def start_phase(self):
        self.new_run(self.sel)
        self.load_level(0)

    def update_phase(self):
        n = len(PHASES)
        if pyxel.btnp(pyxel.KEY_BACKSPACE):
            self.state = "title"
            self.state_t = 0
            return
        if pyxel.btnp(pyxel.KEY_UP) or pyxel.btnp(pyxel.KEY_W):
            self.sel = (self.sel - 1) % n
            pyxel.play(0, 6)
        if pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btnp(pyxel.KEY_S):
            self.sel = (self.sel + 1) % n
            pyxel.play(0, 6)
        for i, key in enumerate((pyxel.KEY_1, pyxel.KEY_2, pyxel.KEY_3)):
            if i < n and pyxel.btnp(key):
                self.sel = i
                self.start_phase()
                return
        mp = (pyxel.mouse_x, pyxel.mouse_y)
        over = None
        for i in range(n):
            x, y, w, h = self.phase_panel(i)
            if x <= mp[0] < x + w and y <= mp[1] < y + h:
                over = i
        if mp != self.last_mouse:          # hover only counts when the mouse actually moved
            self.last_mouse = mp
            if over is not None:
                self.sel = over
        if self.state_t > 6:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if over is not None:
                    self.sel = over
                    self.start_phase()
            elif pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.start_phase()

    # ------------------------------------------------------------ solar flares
    def update_flare(self):
        cfg = self.lv["flare"]
        if not cfg:
            return
        self.fl_timer -= 1
        if self.fl_timer > 0:
            return
        if self.fl_state == 0:            # heads-up: 0.5 s before it hits
            self.fl_state = 1
            self.fl_timer = FLARE_WARN
            pyxel.play(1, 7)
        elif self.fl_state == 1:          # the flare hits the whole screen
            self.fl_state = 2
            self.fl_timer = cfg[2]
            self.flash = 1
            self.shake = 4
            pyxel.play(1, 12)
        else:
            self.fl_state = 0
            self.fl_timer = random.randint(cfg[0], cfg[1])

    # ------------------------------------------------------------ pulsars
    def update_pulsars(self):
        for i, pl in enumerate(self.lv["pulsars"]):
            ph = pulsar_phase(pl, self.t)
            if ph != self.pprev[i]:
                if ph == 1:
                    pyxel.play(2, 8)
                elif ph == 2:
                    pyxel.play(2, 9)
                    self.burst(pl["x"], PULSAR_Y, 8, (7, 14, 2), 1.6, 10)
                self.pprev[i] = ph

    # ------------------------------------------------------------ play
    def update_play(self):
        self.t += 1
        self.update_flare()
        self.update_pulsars()
        if self.probe is None:
            if self.dead_timer > 0:
                self.dead_timer -= 1
                if self.dead_timer == 0 and self.shots <= 0:
                    self.state = "fail"
                    self.state_t = 0
                return
            self.update_aim()
        else:
            self.update_flight()

    def aim_vector(self):
        if self.kv is not None:
            return self.kv[0], self.kv[1], math.hypot(self.kv[0], self.kv[1]) / LAUNCH_K
        dx = self.aim[0] - pyxel.mouse_x
        dy = self.aim[1] - pyxel.mouse_y
        mag = math.hypot(dx, dy)
        if mag > MAX_DRAG:
            dx *= MAX_DRAG / mag
            dy *= MAX_DRAG / mag
            mag = MAX_DRAG
        return dx * LAUNCH_K, dy * LAUNCH_K, mag

    def update_aim(self):
        if pyxel.btnp(pyxel.KEY_R):
            if self.shots < self.max_shots:
                self.score = max(0, self.score - 50)
                self.add_text(60, 56, "RESET -50", 8)
            else:
                self.add_text(70, 56, "RESET", 7)
            self.load_level(self.level_idx)
            return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.kv = None
            self.aim = (pyxel.mouse_x, pyxel.mouse_y)
            pyxel.play(0, 6)
            if self.register_tap(pyxel.mouse_x, pyxel.mouse_y):
                return
        if self.aim:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                self.aim = None
                return
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                vx, vy, mag = self.aim_vector()
                self.aim = None
                if mag >= 4:
                    self.launch(vx, vy)
        else:
            self.update_key_aim()

    def update_key_aim(self):
        """WASD / arrow keys (or d-pad) set the launch velocity; SPACE / ENTER / A fires."""
        left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
        right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
        up = pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP)
        down = pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN)
        dx = (1 if right else 0) - (1 if left else 0)
        dy = (1 if down else 0) - (1 if up else 0)
        limit = MAX_DRAG * LAUNCH_K
        if dx or dy:
            if self.kv is None:
                self.kv = [0.0, 0.0]
                pyxel.play(0, 6)
            k = KEY_AIM_SPEED * (0.3 if pyxel.btn(pyxel.KEY_SHIFT) else 1.0)
            self.kv[0] += dx * k
            self.kv[1] += dy * k
            m = math.hypot(self.kv[0], self.kv[1])
            if m > limit:
                self.kv[0] *= limit / m
                self.kv[1] *= limit / m
        if self.kv is not None:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) or pyxel.btnp(pyxel.KEY_BACKSPACE):
                self.kv = None
            elif (pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN)
                  or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)):
                vx, vy = self.kv
                self.kv = None
                if math.hypot(vx, vy) >= 4 * LAUNCH_K:
                    self.launch(vx, vy)

    def register_tap(self, mx, my):
        """Secret: tap the launch beacon fast, without launching. True if the sector was skipped."""
        sx, sy = self.start
        if math.hypot(mx - sx, my - sy) > 6:
            return False
        for i, e in enumerate(self.lv["eggs"]):
            if e["type"] != "taps":
                continue
            self.taps = [f for f in self.taps if self.t - f < 75] + [self.t]
            if len(self.taps) >= e["n"]:
                self.taps = []
                self.aim = None
                self.burst(sx, sy, 30, (14, 2, 12, 7), 2.6, 24)
                self.find_secret(i)
                return True
        return False

    def launch(self, vx, vy):
        sx, sy = self.start
        self.probe = new_probe(sx, sy, vx, vy)
        self.trail = []
        self.shots -= 1
        self.total_shots += 1
        self.burst(sx, sy, 10, (7, 6, 12), 1.6, 12)
        self.shake = 2
        pyxel.play(0, 0)
        if self.fl_state == 2:            # fired mid-flare: the electronics are cooked
            self.probe["fried"] = True
            self.burst(sx, sy, 14, (10, 9, 8), 2.2, 18)
            self.add_text(max(4, sx - 14), max(14, sy - 12), "FRIED!", 8)
            pyxel.play(1, 12)

    def lose_probe(self, msg, explode):
        p = self.probe
        if explode:
            cols = (7, 10, 14, 2) if msg == "ZAPPED" else (8, 9, 10, 7)
            self.burst(p["x"], p["y"], 28, cols, 2.8, 24)
            self.shake = 10
            pyxel.play(1, 2)
        else:
            self.burst(p["x"], p["y"], 10, (13, 5), 1.2, 16)
            pyxel.play(1, 5)
        self.add_text(max(8, min(W - 40, p["x"] - 8)), max(14, min(H - 12, p["y"] - 6)), msg, 8)
        self.probe = None
        self.trail = []
        self.dead_timer = 18

    def on_warp(self, p, gate):
        a, b = self.lv["portals"][gate]
        self.burst(a[0], a[1], 14, (2, 14, 7), 1.8, 14)
        self.burst(b[0], b[1], 14, (12, 6, 7), 1.8, 14)
        self.trail = []
        self.warped = True
        self.add_text(max(4, min(W - 30, b[0] - 8)), max(14, b[1] - 12), "WARP", 12)
        pyxel.play(0, 10)

    def collect_stars(self, p):
        for s in self.stars:
            if not s["got"] and math.hypot(p["x"] - s["x"], p["y"] - s["y"]) < 5:
                s["got"] = True
                self.level_stars += 1
                self.burst(s["x"], s["y"], 14, (10, 9, 7), 2.0, 16)
                self.add_text(s["x"] - 8, s["y"] - 8, "+STAR", 10)
                pyxel.play(0, 1)

    def update_flight(self):
        p = self.probe
        events = probe_tick(p, self.t, self.lv)
        self.trail.append((p["x"], p["y"]))
        if len(self.trail) > 26:
            self.trail.pop(0)
        for e in events:
            if e[0] == "warp":
                self.on_warp(p, e[1])
        term = None
        for e in events:
            if e[0] in ("hit", "beam", "goal", "egg", "lost"):
                term = e
        if term and term[0] in ("hit", "beam"):
            self.lose_probe("CRASH" if term[0] == "hit" else "ZAPPED", True)
            return
        self.collect_stars(p)
        if term:
            if term[0] == "lost":
                self.lose_probe("ABORT" if term[1] == "fuel" else "LOST", False)
            elif p["fried"]:
                self.fry_fail(p)
            elif term[0] == "goal":
                self.clear_level()
            else:
                self.burst(max(4, min(W - 4, p["x"])), max(12, min(H - 4, p["y"])), 30, (14, 2, 12, 7), 2.6, 24)
                self.find_secret(term[1])
        elif pyxel.btnp(pyxel.KEY_R):
            self.lose_probe("ABORT", False)

    def fry_fail(self, p):
        """Reached the wormhole with a flare-fried probe: the sector is lost."""
        self.burst(p["x"], p["y"], 34, (10, 9, 8, 7), 3.0, 28)
        self.shake = 12
        self.flash = 2
        pyxel.play(1, 12)
        self.probe = None
        self.trail = []
        self.fail_lines = ("FLARE DAMAGE", "SECTOR LOST")
        self.state = "fail"
        self.state_t = 0

    def find_secret(self, egg_i):
        e = self.lv["eggs"][egg_i]
        self.found.add((self.phase_idx, self.level_idx, egg_i))
        self.secret = e["label"]
        self.clear_level(secret=True)

    def clear_level(self, secret=False):
        if secret:
            self.bonus = 150 + 20 * self.shots
        else:
            self.bonus = 100 + 20 * self.shots + 50 * self.level_stars
            self.stars_total += self.level_stars
        self.score += self.bonus
        self.burst(self.goal[0], self.goal[1], 40, (11, 3, 10, 7, 12), 3.0, 30)
        self.flash = 3
        self.shake = 6
        pyxel.play(1, 11 if secret else 3)
        self.probe = None
        self.trail = []
        self.state = "clear"
        self.state_t = 0

    def shake_offset(self):
        if self.shake > 3:
            return random.randint(-2, 2), random.randint(-2, 2)
        if self.shake:
            return random.randint(-1, 1), random.randint(-1, 1)
        return 0, 0

    def sb_reset(self):
        p = {"x": 76.0, "y": 60.0, "vx": 0.0, "vy": 0.0, "ground": False, "face": 1}
        self.sb = {"p": p, "objs": [], "mode": "top", "orbs": 0, "cd": 0, "rings": []}
        for _ in range(3):
            self.sb_spawn("crate", random.randint(20, 130), random.randint(25, 100))
            self.sb_spawn("orb", random.randint(20, 130), random.randint(25, 100))

    def sb_spawn(self, kind, x, y):
        objs = self.sb["objs"]
        if len(objs) >= MAX_OBJS:
            objs.pop(0)
        objs.append({"kind": kind,
                     "x": max(AL + 1.0, min(AR - 9.0, float(x) - 4)),
                     "y": max(AT + 1.0, min(AB - 9.0, float(y) - 4)),
                     "vx": random.uniform(-0.6, 0.6), "vy": random.uniform(-0.6, 0.6)})

    def sb_pulse(self):
        sb = self.sb
        p = sb["p"]
        cx, cy = p["x"] + 4, p["y"] + 4
        sb["cd"] = 15
        sb["rings"].append([cx, cy, 4, 10, 12])
        for o in sb["objs"]:
            dx = o["x"] + 4 - cx
            dy = o["y"] + 4 - cy
            d = math.hypot(dx, dy) or 1.0
            if d < PULSE_R:
                f = (1 - d / PULSE_R) * 4.5 + 0.5
                o["vx"] += dx / d * f
                o["vy"] += dy / d * f
        self.shake = 3
        self.burst(cx, cy, 10, (12, 6, 7), 1.8, 12)
        pyxel.play(0, 0)

    def sb_detonate(self, mx, my):
        sb = self.sb
        p = sb["p"]
        sb["rings"].append([mx, my, 4, 8, 9])
        for o in sb["objs"][:]:
            if math.hypot(o["x"] + 4 - mx, o["y"] + 4 - my) < BLAST_R:
                sb["objs"].remove(o)
                self.burst(o["x"] + 4, o["y"] + 4, 16, (8, 9, 10, 7), 2.4, 20)
        for o in sb["objs"]:  # shove survivors in the wider blast zone
            dx = o["x"] + 4 - mx
            dy = o["y"] + 4 - my
            d = math.hypot(dx, dy) or 1.0
            if d < BLAST_R * 2:
                f = (1 - d / (BLAST_R * 2)) * 3
                o["vx"] += dx / d * f
                o["vy"] += dy / d * f
        dx = p["x"] + 4 - mx
        dy = p["y"] + 4 - my
        d = math.hypot(dx, dy) or 1.0
        if d < BLAST_R * 1.5:
            f = (1 - d / (BLAST_R * 1.5)) * 4
            p["vx"] += dx / d * f
            p["vy"] += dy / d * f
        self.burst(mx, my, 12, (8, 9, 10), 2.2, 16)
        self.shake = 8
        self.add_text(max(2, min(W - 26, mx - 8)), max(14, my - 10), "BOOM", 8)
        pyxel.play(1, 2)

    def update_sandbox(self):
        sb = self.sb
        p = sb["p"]
        objs = sb["objs"]
        if pyxel.btnp(pyxel.KEY_R):
            self.sb_reset()
            self.add_text(66, 56, "RESET", 7)
            pyxel.play(1, 5)
            return
        if pyxel.btnp(pyxel.KEY_BACKSPACE):
            self.state = "title"
            self.state_t = 0
            return
        if pyxel.btnp(pyxel.KEY_G):
            sb["mode"] = "grav" if sb["mode"] == "top" else "top"
            p["vx"] = p["vy"] = 0.0
            label = "GRAVITY MODE" if sb["mode"] == "grav" else "TOP-DOWN MODE"
            self.add_text((W - len(label) * 4) // 2, 40, label, 10)
            pyxel.play(0, 6)
        grav = sb["mode"] == "grav"

        left = pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT)
        right = pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT)
        up = pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_UP)
        down = pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN)
        dx = (1 if right else 0) - (1 if left else 0)
        dy = (1 if down else 0) - (1 if up else 0)
        if dx:
            p["face"] = dx
        space = pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A)

        if grav:
            p["vx"] += dx * 0.6
            p["vx"] *= 0.78
            p["vy"] += 0.38
            jump = space or pyxel.btnp(pyxel.KEY_W) or pyxel.btnp(pyxel.KEY_UP)
            if jump and p["ground"]:
                p["vy"] = -4.6
                p["ground"] = False
                self.burst(p["x"] + 4, p["y"] + 8, 6, (13, 7), 1.0, 10)
                pyxel.play(0, 0)
        else:
            if dx and dy:
                dx *= 0.7071
                dy *= 0.7071
            p["vx"] = (p["vx"] + dx * 0.55) * 0.80
            p["vy"] = (p["vy"] + dy * 0.55) * 0.80
            if space and sb["cd"] == 0:
                self.sb_pulse()
        if sb["cd"] > 0:
            sb["cd"] -= 1

        p["x"] = max(AL + 1.0, min(AR - 9.0, p["x"] + p["vx"]))
        p["y"] += p["vy"]
        p["ground"] = False
        if p["y"] >= AB - 9:
            p["y"] = AB - 9.0
            p["vy"] = 0.0
            p["ground"] = grav
        elif p["y"] <= AT + 1:
            p["y"] = AT + 1.0
            p["vy"] = max(p["vy"], 0.0)

        floor = AB - 9
        for o in objs:
            if grav:
                o["vy"] += 0.32
                o["vx"] *= 0.985
            else:
                o["vx"] *= 0.95
                o["vy"] *= 0.95
            o["x"] += o["vx"]
            o["y"] += o["vy"]
            if o["x"] < AL + 1:
                o["x"] = AL + 1.0
                o["vx"] = abs(o["vx"]) * 0.6
            elif o["x"] > AR - 9:
                o["x"] = AR - 9.0
                o["vx"] = -abs(o["vx"]) * 0.6
            if o["y"] < AT + 1:
                o["y"] = AT + 1.0
                o["vy"] = abs(o["vy"]) * 0.6
            elif o["y"] > floor:
                o["y"] = float(floor)
                o["vy"] = -abs(o["vy"]) * (0.45 if grav else 0.6)
                if grav:
                    o["vx"] *= 0.9
                    if abs(o["vy"]) < 0.6:
                        o["vy"] = 0.0

        for o in objs[:]:
            if abs(o["x"] - p["x"]) < 8 and abs(o["y"] - p["y"]) < 8:
                if o["kind"] == "orb":
                    objs.remove(o)
                    sb["orbs"] += 1
                    self.burst(o["x"] + 4, o["y"] + 4, 12, (12, 6, 7), 1.8, 14)
                    self.add_text(int(o["x"]) - 4, int(o["y"]) - 6, "+1 ORB", 12)
                    pyxel.play(0, 1)
                else:
                    ddx = o["x"] - p["x"]
                    ddy = o["y"] - p["y"]
                    d = math.hypot(ddx, ddy) or 1.0
                    o["vx"] += ddx / d * 0.6 + p["vx"] * 0.3
                    if not grav:
                        o["vy"] += ddy / d * 0.6 + p["vy"] * 0.3

        mx, my = pyxel.mouse_x, pyxel.mouse_y
        inside = AL < mx < AR and AT < my < AB
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) and inside:
            orb = pyxel.btn(pyxel.KEY_SHIFT)
            self.sb_spawn("orb" if orb else "crate", mx, my)
            self.burst(mx, my, 8, (7, 12) if orb else (7, 9), 1.2, 10)
            pyxel.play(0, 6)
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT) and inside:
            self.sb_detonate(mx, my)

        for r in sb["rings"]:
            r[2] += 3
            r[3] -= 1
        sb["rings"] = [r for r in sb["rings"] if r[3] > 0]

    def draw_sandbox(self, fc):
        sb = self.sb
        p = sb["p"]
        grav = sb["mode"] == "grav"
        sx, sy = self.shake_offset()
        pyxel.camera(sx, sy)
        for gx in range(AL + 8, AR, 16):
            for gy in range(AT + 8, AB, 16):
                pyxel.pset(gx, gy, 1)
        pyxel.rectb(AL, AT, AR - AL, AB - AT, 5)
        if grav:
            pyxel.line(AL + 1, AB - 1, AR - 2, AB - 1, 13)
        for o in sb["objs"]:
            if o["kind"] == "orb":
                draw_sprite("orb", o["x"], o["y"] + int(1.2 * math.sin(fc * 0.2 + o["x"])))
            else:
                draw_sprite("crate", o["x"], o["y"])
        for r in sb["rings"]:
            pyxel.circb(r[0], r[1], r[2], r[4])
        moving = abs(p["vx"]) > 0.3 or abs(p["vy"]) > 0.3
        draw_sprite("bot_run" if moving and (fc // 4) % 2 else "bot_idle", p["x"], p["y"], p["face"] < 0)
        for q in self.particles:
            pyxel.pset(q[0], q[1], q[5])
        for t in self.texts:
            stext(int(t[0]), int(t[1]), t[2], t[3])
        pyxel.camera(0, 0)

        pyxel.rect(0, 0, W, 9, 1)
        pyxel.line(0, 9, W, 9, 5)
        pyxel.text(2, 2, "LAB " + ("GRAVITY" if grav else "TOP-DOWN"), 13)
        pyxel.text(80, 2, f"ORBS {sb['orbs']:02d}", 10)
        pyxel.text(112, 2, f"OBJ {len(sb['objs'])}/{MAX_OBJS}", 6)
        if self.state_t < 240:
            ctext(91, "ARROWS/WASD MOVE SPACE PULSE/JUMP", 7)
            ctext(98, "CLICK:CRATE SHIFT:ORB RCLICK:BOOM", 7)
            ctext(105, "G:MODE TAB:INFO R:RESET BKSP:MENU", 13)

    def draw_telemetry(self, lines):
        w = max(len(s) for s in lines) * 4 + 6
        pyxel.rect(4, 12, w, len(lines) * 8 + 3, 0)
        pyxel.rectb(4, 12, w, len(lines) * 8 + 3, 5)
        for i, s in enumerate(lines):
            pyxel.text(7, 15 + i * 8, s, 11)
        pyxel.rectb(7, 103, 146, 12, 5)
        for c in range(16):
            x = 8 + c * 9
            pyxel.rect(x, 104, 9, 10, c)
            pyxel.text(x + 1, 106, str(c), 0 if c in (6, 7, 9, 10, 11, 14, 15) else 7)

    def tele_lines(self):
        lines = [f"STATE {self.state.upper()}", f"FRAME {pyxel.frame_count}",
                 f"MOUSE {pyxel.mouse_x},{pyxel.mouse_y}", f"PART {len(self.particles)}"]
        if self.state == "sandbox":
            p = self.sb["p"]
            lines += [f"MODE {self.sb['mode'].upper()}", f"POS {int(p['x'])},{int(p['y'])}",
                      f"VEL {p['vx']:.1f},{p['vy']:.1f}", f"OBJ {len(self.sb['objs'])}"]
        elif self.state not in ("title", "phase"):
            lines += [f"PHASE {self.phase['name'][:3]}", f"LEVEL {self.level_idx + 1}",
                      f"SHOTS {self.shots}", f"T {self.t}",
                      f"FLARE {('CALM', 'WARN', 'ON')[self.fl_state]} {max(0, self.fl_timer)}"]
            if self.probe:
                lines.append(f"SPEED {math.hypot(self.probe['vx'], self.probe['vy']):.1f}")
        return lines

    # ------------------------------------------------------------ draw
    def preview(self, vx, vy):
        s = new_probe(self.start[0], self.start[1], vx, vy)
        t = self.t
        pts = []
        for i in range(PREVIEW_STEPS):
            hit = step(s, t, self.lv)
            t += 1
            if hit:
                break
            if i % 3 == 2:
                pts.append((s["x"], s["y"]))
        return pts

    def draw(self):
        pyxel.cls(0)
        fc = pyxel.frame_count
        flare_on = self.state == "play" and self.fl_state == 2
        if flare_on:
            self.warm_palette()
        for x, y, c, ph in self.bg:
            pyxel.pset(x, y, 7 if (fc + ph) % 60 < 3 else c)

        if self.state == "title":
            self.draw_title(fc)
        elif self.state == "phase":
            self.draw_phase(fc)
        elif self.state == "sandbox":
            self.draw_sandbox(fc)
        else:
            sx, sy = self.shake_offset()
            pyxel.camera(sx, sy)
            self.draw_world(fc)
            pyxel.camera(0, 0)
            self.draw_hud()
            self.draw_overlays(fc)
        if flare_on:
            pyxel.pal()
            self.draw_flare(fc)
        if self.state == "play" and self.lv["flare"] and self.fl_state:
            self.draw_flare_banner(fc)
        if self.flash > 0 and self.flash % 2 == 1:
            pyxel.rect(0, 0, W, H, 7)
        if self.tele:
            self.draw_telemetry(self.tele_lines())

    @staticmethod
    def warm_palette():
        """Remap the cool colours to warm ones while a flare is burning."""
        for a, b in ((1, 2), (5, 4), (6, 15), (7, 15), (12, 9), (13, 14)):
            pyxel.pal(a, b)

    def draw_flare(self, fc):
        pyxel.dither(0.18 + 0.1 * math.sin(fc * 0.4))
        pyxel.rect(0, 0, W, H, 9)
        pyxel.dither(0.5)
        for _ in range(4):
            y = random.randrange(10, H)
            x = random.randrange(0, W - 30)
            pyxel.rect(x, y, random.randrange(10, 60), 1, 10)
        pyxel.dither(1.0)
        pyxel.rectb(0, 0, W, H, 9)

    def draw_flare_banner(self, fc):
        if self.fl_state == 1:
            if (fc // 2) % 2:
                pyxel.rectb(0, 0, W, H, 10)
                pyxel.rectb(1, 1, W - 2, H - 2, 9)
            if (fc // 3) % 2:
                ctext(100, "! SOLAR FLARE INCOMING !", 10)
        else:
            ctext(100, "FLARE ACTIVE - HOLD FIRE", 10 if (fc // 4) % 2 else 8)

    def draw_world(self, fc):
        gx, gy = self.goal
        pulse = int(2 * math.sin(fc * 0.2))
        for i, col in enumerate((11, 3, 11)):
            pyxel.circb(gx, gy, max(1, GOAL_R - i * 2 + pulse), col)
        pyxel.circ(gx, gy, 1, 7)

        self.draw_portals(fc)

        for b in self.bodies:
            m = b["mate"]
            if m is not None:                   # binary: faint orbit ring around the shared centre
                cx, cy, rad = b["orbit"][0], b["orbit"][1], b["orbit"][2]
                pyxel.circb(cx, cy, int(rad), 1)
                if id(b) < id(m):
                    ax, ay = body_pos(b, self.t)
                    mx, my = body_pos(m, self.t)
                    pyxel.line(ax, ay, mx, my, 1)
        for b in self.bodies:
            bx, by = body_pos(b, self.t)
            draw_body(b, int(bx), int(by))

        self.draw_pulsars(fc)

        for i, s in enumerate(self.stars):
            if s["got"]:
                continue
            x = s["x"]
            y = s["y"] + int(1.5 * math.sin(fc * 0.15 + i))
            c = 10 if fc % 20 < 14 else 7
            pyxel.pset(x, y, c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                pyxel.pset(x + dx, y + dy, 9)
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                if fc % 20 < 10:
                    pyxel.pset(x + dx, y + dy, 9)

        # secret ghost nodes only shimmer when the probe flies close
        if self.probe:
            for e in self.lv["eggs"]:
                if e["type"] == "ghost":
                    d = math.hypot(self.probe["x"] - e["x"], self.probe["y"] - e["y"])
                    if d < 16 and fc % 2 == 0:
                        pyxel.pset(e["x"] + random.randint(-2, 2), e["y"] + random.randint(-2, 2), 14)

        stx, sty = self.start
        if self.state == "play" and self.probe is None and self.dead_timer == 0:
            pyxel.circb(stx, sty, 4 + (fc // 8) % 2, 6)
            pyxel.circ(stx, sty, 2, 7)

        if (self.aim or self.kv is not None) and self.probe is None:
            vx, vy, mag = self.aim_vector()
            bx = stx - vx / LAUNCH_K
            by = sty - vy / LAUNCH_K
            if self.kv is not None:             # keyboard aim: show the firing direction
                bx, by = stx + vx / LAUNCH_K, sty + vy / LAUNCH_K
            doomed = self.fl_state == 2
            pyxel.line(stx, sty, bx, by, 8 if doomed else 13)
            pyxel.circb(bx, by, 2, 8 if doomed else 13)
            for px, py in self.preview(vx, vy):
                pyxel.pset(px, py, 8 if doomed else 7)
            pw = mag / MAX_DRAG
            pyxel.rect(2, 110, 30, 5, 5)
            pyxel.rect(3, 111, int(28 * pw), 3, 11 if pw < 0.5 else (10 if pw < 0.85 else 8))

        for i, (tx, ty) in enumerate(self.trail):
            col = 5 if i < len(self.trail) * 0.4 else (13 if i < len(self.trail) * 0.8 else 6)
            if self.probe and self.probe["fried"]:
                col = random.choice((8, 9, 10))
            pyxel.pset(tx, ty, col)
        if self.probe:
            p = self.probe
            if p["fried"] and fc % 3 == 0:
                pyxel.circ(p["x"], p["y"], 2, 8)
            else:
                pyxel.circ(p["x"], p["y"], 2, 7)
            pyxel.pset(p["x"], p["y"], 10)

        for p in self.particles:
            pyxel.pset(p[0], p[1], p[5])
        for t in self.texts:
            stext(int(t[0]), int(t[1]), t[2], t[3])

    def draw_pulsars(self, fc):
        for pl in self.lv["pulsars"]:
            x = pl["x"]
            ph = pulsar_phase(pl, self.t)
            for y in range(PULSAR_Y + 4, H, 5):           # faint lane marker
                pyxel.pset(x, y, 5)
            if ph == 1:                                   # charging: lane flickers
                if fc % 4 < 2:
                    for y in range(PULSAR_Y + 3, H, 3):
                        pyxel.pset(x, y, 14)
                    pyxel.line(x - 2, PULSAR_Y + 3, x - 2, H, 2)
                    pyxel.line(x + 2, PULSAR_Y + 3, x + 2, H, 2)
            elif ph == 2:                                 # firing: the whole column at once
                pyxel.rect(x - 2, PULSAR_Y, 5, H - PULSAR_Y, 14)
                pyxel.rect(x - 1, PULSAR_Y, 3, H - PULSAR_Y, 7)
                pyxel.rect(x - 3, PULSAR_Y, 1, H - PULSAR_Y, 2)
                pyxel.rect(x + 3, PULSAR_Y, 1, H - PULSAR_Y, 2)
            core = 7 if ph else 14
            pyxel.circ(x, PULSAR_Y, 3, 2)
            pyxel.circ(x, PULSAR_Y, 1, core)
            a = fc * (0.5 if ph else 0.15)
            for k in range(4):
                aa = a + k * math.pi / 2
                pyxel.line(x, PULSAR_Y, x + math.cos(aa) * 6, PULSAR_Y + math.sin(aa) * 6, 14 if ph else 2)

    def draw_portals(self, fc):
        for a, b in self.lv["portals"]:
            n = int(math.hypot(b[0] - a[0], b[1] - a[1]) // 6)
            for i in range(1, n):                         # faint link between the two gates
                pyxel.pset(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, 1)
            self.draw_gate(a[0], a[1], fc, True)
            self.draw_gate(b[0], b[1], fc, False)

    @staticmethod
    def draw_gate(x, y, fc, entry):
        cols = (2, 14, 7) if entry else (12, 6, 7)
        r = PORTAL_R
        pyxel.circb(x, y, r, cols[0])
        pyxel.circb(x, y, r - 2, cols[1])
        pyxel.pset(x, y, cols[2])
        spin = fc * 0.15 * (1 if entry else -1)
        for k in range(4):
            a = spin + k * math.pi / 2
            pyxel.pset(x + math.cos(a) * (r + 1), y + math.sin(a) * (r + 1), cols[2])
        pr = (fc // 2) % 5                                # entry sucks inward, exit pushes outward
        rr = (r + 3 - pr) if entry else (r - 2 + pr)
        if rr > 1:
            pyxel.circb(x, y, rr, cols[0])

    def draw_hud(self):
        pyxel.rect(0, 0, W, 9, 1)
        pyxel.line(0, 9, W, 9, 5)
        pyxel.text(2, 2, f"{self.level_idx + 1} {self.name}", 13)
        pyxel.text(68, 2, f"{self.score:05d}", 10)
        if self.state == "play" and self.lv["flare"] and self.fl_state:
            if self.fl_state == 2:
                pyxel.text(92, 2, "FLARE", 8)
            elif (pyxel.frame_count // 2) % 2:
                pyxel.text(92, 2, "FLARE", 10)
        for i in range(self.max_shots):
            pyxel.circ(W - 6 - i * 7, 4, 2, 7 if i < self.shots else 5)
        if self.state == "play":
            if self.probe:
                hint = "R: ABORT FLIGHT"
            else:
                hint = "DRAG OR WASD+SPACE - R: RESET"
            pyxel.text(W - len(hint) * 4 - 2, 112, hint, 5)

    def draw_overlays(self, fc):
        blink = fc % 30 < 20
        if self.state == "clear":
            if self.secret:
                panel(22, 30, 116, 60)
                ctext(37, "SECRET FOUND!", 14)
                ctext(48, self.secret, 10)
                ctext(58, "SECTOR SKIPPED", 7)
                ctext(68, f"BONUS +{self.bonus}", 10)
                if blink and self.state_t > 15:
                    ctext(79, "CLICK TO CONTINUE", 13)
            else:
                panel(22, 34, 116, 54)
                ctext(41, "SECTOR CLEARED", 11)
                ctext(53, f"STARS {self.level_stars}/{len(self.stars)}", 10)
                ctext(61, f"PROBES LEFT {self.shots}", 7)
                ctext(69, f"BONUS +{self.bonus}", 10)
                if blink and self.state_t > 15:
                    ctext(79, "CLICK TO CONTINUE", 13)
        elif self.state == "fail":
            panel(22, 38, 116, 44)
            ctext(46, self.fail_lines[0], 8)
            ctext(57, self.fail_lines[1], 7)
            if blink and self.state_t > 15:
                ctext(70, "CLICK TO RETRY", 13)
        elif self.state == "win":
            ph = self.phase
            panel(14, 16, 132, 88)
            ctext(24, f"{ph['name']} COMPLETE", ph["col"])
            ctext(35, f"SCORE {self.score}", 10)
            ctext(44, f"STARS {self.stars_total}/{ph['stars']}", 10)
            ctext(53, f"PROBES USED {self.total_shots}", 7)
            ctext(62, f"SECRETS {self.phase_secrets(self.phase_idx)}/{ph['secrets']}", 14)
            if self.total_shots <= ph["ranks"][0]:
                rank = "ADMIRAL"
            elif self.total_shots <= ph["ranks"][1]:
                rank = "NAVIGATOR"
            else:
                rank = "CADET"
            ctext(73, f"RANK: {rank}", 14)
            if blink and self.state_t > 20:
                ctext(90, "CLICK TO CONTINUE", 13)

    def draw_title(self, fc):
        pyxel.camera(0, 0)
        big_text(32, 16, "STARLING", 3, 10, 9, 2)
        ctext(42, "A GRAVITY SLINGSHOT PUZZLE", 6)
        cx, cy = 80, 70
        pyxel.circb(cx, cy, 27, 1)
        pyxel.circb(cx, cy, 20, 1)
        pyxel.circ(cx, cy, 8, 12)
        pyxel.circb(cx, cy, 8, 6)
        pyxel.pset(cx - 3, cy - 3, 7)
        pyxel.line(cx - 6, cy + 1, cx + 6, cy + 1, 6)
        a = fc * 0.06
        pyxel.circ(cx + math.cos(a) * 20, cy + math.sin(a) * 20, 3, 7)
        b = fc * 0.035 + 2
        px, py = cx + math.cos(b) * 27, cy + math.sin(b) * 27
        pyxel.circ(px, py, 2, 10)
        pyxel.pset(px - math.sin(b) * 4, py + math.cos(b) * 4, 9)
        if fc % 30 < 20:
            ctext(99, "CLICK/SPACE: CAMPAIGN", 7)
        ctext(106, "S: SANDBOX LAB", 13)
        ctext(113, "DRAG OR WASD - RELEASE/SPACE TO FIRE", 5)

    def draw_phase(self, fc):
        pyxel.camera(0, 0)
        ctext(6, "SELECT PHASE", 10)
        for i, ph in enumerate(PHASES):
            x, y, w, h = self.phase_panel(i)
            on = i == self.sel
            pyxel.rect(x, y, w, h, 1)
            pyxel.rectb(x, y, w, h, ph["col"] if on else 5)
            if on:
                pyxel.rectb(x + 2, y + 2, w - 4, h - 4, 5)
                if fc % 20 < 14:
                    pyxel.text(x - 8, y + 10, ">", ph["col"])
            pyxel.text(x + 6, y + 5, f"{i + 1} {ph['name']}", ph["col"])
            pyxel.text(x + w - 6 - 28, y + 5, f"{ph['shots']} PROBES", 13)
            pyxel.text(x + 6, y + 14, ph["blurb"], 7)
            for k in range(3):                       # difficulty pips
                pyxel.rect(x + w - 6 - 12 + k * 4, y + 15, 3, 3, ph["col"] if k <= i else 5)
        ctext(108, f"SECRETS FOUND {len(self.found)}/{sum(p['secrets'] for p in PHASES)}", 14)
        ctext(114, "1-3/CLICK:PLAY  W/S:MOVE  BKSP:BACK", 5)



if __name__ == "__main__":
    Game()
