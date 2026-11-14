"""STARLING - a gravity-slingshot puzzle game built on Pyxel.

Drag to aim, release to launch. Planets bend your probe's path.
Reach the wormhole before you run out of probes. Grab stars for bonus points.
Two modes: the 5-sector CAMPAIGN, and a SANDBOX LAB with the classic PIXELBOX
controls (move, pulse/jump, spawn crates/orbs, detonate, G mode toggle, TAB inspector).
Run with:  python main.py
"""
import math
import random
import copy

import pyxel

W, H = 160, 120
G = 1.25            # gravity strength
MAX_DRAG = 40.0     # max pull-back distance in pixels
LAUNCH_K = 0.13     # drag distance -> launch speed
MAX_SPEED = 6.0
SHOTS = 5
FLIGHT_LIMIT = 420  # frames before a probe runs out of fuel
GOAL_R = 7
PREVIEW_STEPS = 45


def body(x, y, r, m, c, rim, orbit=None):
    """A gravity body. orbit = (cx, cy, radius, angular_speed, phase) for moons."""
    return {"x": x, "y": y, "r": r, "m": m, "c": c, "rim": rim, "orbit": orbit}


LEVELS = [
    dict(name="FIRST LIGHT", start=(18, 100), goal=(140, 24),
         bodies=[body(85, 82, 8, 70, 12, 6)],
         stars=[(60, 52), (112, 60)]),
    dict(name="SLINGSHOT", start=(15, 60), goal=(145, 60),
         bodies=[body(80, 60, 12, 140, 9, 10)],
         stars=[(80, 26), (80, 94)]),
    dict(name="TWIN WELLS", start=(15, 100), goal=(145, 22),
         bodies=[body(60, 50, 8, 80, 3, 11), body(110, 85, 10, 100, 2, 14)],
         stars=[(85, 66), (132, 48)]),
    dict(name="CLOCKWORK", start=(15, 105), goal=(145, 20),
         bodies=[body(80, 75, 7, 90, 8, 14),
                 body(0, 0, 3, 22, 6, 7, orbit=(80, 75, 27, 0.05, 0.0))],
         stars=[(80, 30), (40, 60)]),
    dict(name="GAUNTLET", start=(12, 60), goal=(148, 60),
         bodies=[body(50, 30, 7, 70, 12, 6), body(50, 90, 7, 70, 9, 10),
                 body(100, 60, 9, 100, 2, 14),
                 body(0, 0, 3, 20, 6, 7, orbit=(100, 60, 24, -0.07, 1.0))],
         stars=[(75, 60), (125, 30), (125, 90)]),
]
# Expand the original five sectors into a nine-sector, three-phase campaign.
# Later sectors remix proven layouts and layer additional hazards.
_extra = []
for _idx, _base in enumerate((LEVELS[1], LEVELS[2], LEVELS[3], LEVELS[4])):
    _lv = copy.deepcopy(_base)
    _lv["name"] = ("CROSSCURRENT", "ECLIPSE", "DEEP FIELD", "SINGULARITY")[_idx]
    _lv["start"] = ((14, 96), (14, 22), (14, 60), (12, 105))[_idx]
    _lv["goal"] = ((146, 22), (146, 98), (146, 60), (148, 16))[_idx]
    _extra.append(_lv)
LEVELS.extend(_extra)
# True binary systems: two gravity wells orbit a shared barycentre.
for _li, _cx, _cy, _rad, _speed in (
    (2, 82, 62, 12, 0.045),
    (4, 82, 60, 15, 0.060),
    (6, 80, 60, 17, 0.070),
    (7, 80, 60, 20, 0.082),
    (8, 80, 60, 22, 0.095),
):
    LEVELS[_li]["bodies"].extend([
        body(0, 0, 4, 38, 10, 7, orbit=(_cx, _cy, _rad, _speed, 0.0)),
        body(0, 0, 5, 48, 8, 14, orbit=(_cx, _cy, _rad, _speed, math.pi)),
    ])
TOTAL_STARS = sum(len(lv["stars"]) for lv in LEVELS)

PHASES = (
    ("EXPLORATION", 0, 3),
    ("TURBULENCE", 3, 6),
    ("SINGULARITY", 6, 9),
)

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


def step(x, y, vx, vy, t, bodies):
    """Advance one frame (two substeps). Returns x, y, vx, vy, hit."""
    hit = False
    for k in range(2):
        tt = t + k * 0.5
        ax, ay = accel(x, y, bodies, tt)
        vx += ax * 0.5
        vy += ay * 0.5
        sp = math.hypot(vx, vy)
        if sp > MAX_SPEED:
            vx *= MAX_SPEED / sp
            vy *= MAX_SPEED / sp
        x += vx * 0.5
        y += vy * 0.5
        for b in bodies:
            bx, by = body_pos(b, tt)
            if (x - bx) ** 2 + (y - by) ** 2 < (b["r"] + 1.5) ** 2:
                hit = True
    return x, y, vx, vy, hit


# ---------------------------------------------------------------- drawing helpers
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
        self.new_run()
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

    # ------------------------------------------------------------ state
    def new_run(self):
        self.level_idx = 0
        self.score = 0
        self.total_shots = 0
        self.stars_total = 0
        self.load_level(0, keep_state=True)

    def load_level(self, i, keep_state=False):
        lv = LEVELS[i]
        self.level_idx = i
        self.name = lv["name"]
        self.start = lv["start"]
        self.goal = lv["goal"]
        self.bodies = lv["bodies"]
        self.stars = [{"x": x, "y": y, "got": False} for x, y in lv["stars"]]
        self.shots = SHOTS
        self.level_stars = 0
        self.t = 0
        self.probe = None
        self.trail = []
        self.aim = None
        self.dead_timer = 0
        self.bonus = 0
        # Environmental hazards are frame-driven and reset on each sector.
        self.flare_timer = random.randint(150, 240)
        self.flare_warning = 0
        self.flare_active = 0
        self.pulsar_clock = 0
        self.pulsar_beams = []
        # Optional paired wormholes: entering one exits from the other.
        self.wormholes = self.make_wormholes(i)
        self.secret_found = False
        if not keep_state:
            self.state = "play"
            self.state_t = 0

    def make_wormholes(self, level_index):
        # Wormhole shortcuts appear from the intermediate phase onward.
        if level_index < 3:
            return []
        layouts = [
            ((54, 24), (116, 94)),
            ((38, 92), (122, 28)),
            ((48, 22), (112, 98)),
            ((32, 60), (128, 60)),
            ((42, 24), (120, 96)),
            ((30, 88), (130, 30)),
        ]
        a, b = layouts[(level_index - 3) % len(layouts)]
        return [tuple(map(float, a)), tuple(map(float, b))]

    def update_hazards(self):
        # Solar flare: a half-second warning at 30 fps, then a short screen-wide
        # ion storm. Launching during the warning/flare is deliberately unsafe.
        if self.flare_active > 0:
            self.flare_active -= 1
        elif self.flare_warning > 0:
            self.flare_warning -= 1
            if self.flare_warning == 0:
                self.flare_active = 22
                self.add_text(48, 14, "SOLAR FLARE!", 8)
        else:
            self.flare_timer -= 1
            if self.flare_timer <= 0:
                self.flare_warning = 15
                self.flare_timer = random.randint(
                    max(105, 210 - self.level_idx * 8),
                    max(165, 330 - self.level_idx * 10))
        self.pulsar_clock += 1
        # Every uncollected star is a potential pulsar source. Staggered
        # intervals keep beams readable instead of filling the whole screen.
        interval = max(72, 150 - self.level_idx * 7)
        if self.level_idx >= 1:
            for idx, star in enumerate(self.stars):
                if star["got"]:
                    continue
                phase = (self.pulsar_clock + idx * 37) % interval
                if phase == interval - 24:
                    self.pulsar_beams.append({"x": float(star["x"]), "warn": 24, "life": 0})
        for beam in self.pulsar_beams:
            if beam["warn"] > 0:
                beam["warn"] -= 1
                if beam["warn"] == 0:
                    beam["life"] = 8
            elif beam["life"] > 0:
                beam["life"] -= 1
        self.pulsar_beams = [b for b in self.pulsar_beams if b["warn"] > 0 or b["life"] > 0]

    @staticmethod
    def confirm():
        return (pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE)
                or pyxel.btnp(pyxel.KEY_RETURN))

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
                self.new_run()
                self.load_level(0)
        elif self.state == "sandbox":
            self.update_sandbox()
        elif self.state == "play":
            self.update_play()
        elif self.state == "clear":
            if self.state_t > 15 and self.confirm():
                if self.level_idx + 1 >= len(LEVELS):
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
                self.new_run()
                self.state = "title"
                self.state_t = 0

    def update_play(self):
        self.t += 1
        self.update_hazards()
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
            if self.shots < SHOTS:
                self.score = max(0, self.score - 50)
                self.add_text(60, 56, "RESET -50", 8)
            else:
                self.add_text(70, 56, "RESET", 7)
            self.load_level(self.level_idx)
            return
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.aim = (pyxel.mouse_x, pyxel.mouse_y)
            pyxel.play(0, 6)
        if self.aim:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
                self.aim = None
                return
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                vx, vy, mag = self.aim_vector()
                self.aim = None
                if mag >= 4:
                    self.launch(vx, vy)
                    if self.flare_active > 0:
                        # A launch during the active ion storm fries navigation.
                        self.probe["flare_fault"] = True

    def launch(self, vx, vy):
        sx, sy = self.start
        self.probe = {"x": float(sx), "y": float(sy), "vx": vx, "vy": vy, "age": 0}
        self.trail = []
        self.shots -= 1
        self.total_shots += 1
        self.burst(sx, sy, 10, (7, 6, 12), 1.6, 12)
        self.shake = 2
        pyxel.play(0, 0)

    def lose_probe(self, msg, explode):
        p = self.probe
        if explode:
            self.burst(p["x"], p["y"], 28, (8, 9, 10, 7), 2.8, 24)
            self.shake = 10
            pyxel.play(1, 2)
        else:
            self.burst(p["x"], p["y"], 10, (13, 5), 1.2, 16)
            pyxel.play(1, 5)
        self.add_text(max(8, min(W - 40, p["x"] - 8)), max(14, min(H - 12, p["y"] - 6)), msg, 8)
        self.probe = None
        self.trail = []
        self.dead_timer = 18

    def update_flight(self):
        p = self.probe
        if p.get("flare_fault"):
            self.shots = 0
            self.lose_probe("MACHINERY FRIED", True)
            return
        x, y, vx, vy, hit = step(p["x"], p["y"], p["vx"], p["vy"], self.t, self.bodies)
        p.update(x=x, y=y, vx=vx, vy=vy)
        p["age"] += 1
        self.trail.append((x, y))
        if len(self.trail) > 26:
            self.trail.pop(0)
        if hit:
            self.lose_probe("CRASH", True)
            return
        for s in self.stars:
            if not s["got"] and math.hypot(x - s["x"], y - s["y"]) < 5:
                s["got"] = True
                self.level_stars += 1
                self.burst(s["x"], s["y"], 14, (10, 9, 7), 2.0, 16)
                self.add_text(s["x"] - 8, s["y"] - 8, "+STAR", 10)
                pyxel.play(0, 1)
        # A live pulsar beam spans the full height of the playfield.
        for beam in self.pulsar_beams:
            if beam["life"] > 0 and abs(x - beam["x"]) < 2.5:
                self.lose_probe("PULSAR HIT", True)
                return
        # Wormhole pairs are optional mid/late-game route shortcuts.
        if len(self.wormholes) == 2:
            for wi, (wx, wy) in enumerate(self.wormholes):
                if math.hypot(x - wx, y - wy) < 5:
                    ox, oy = self.wormholes[1 - wi]
                    p.update(x=ox, y=oy, vx=vx * 0.88, vy=vy * 0.88)
                    self.burst(wx, wy, 16, (11, 3, 10), 2.0, 18)
                    self.burst(ox, oy, 16, (11, 3, 10), 2.0, 18)
                    self.add_text(int(ox) - 16, int(oy) - 9, "WORMHOLE!", 11)
                    pyxel.play(0, 3)
                    x, y = ox, oy
                    break
        if math.hypot(x - self.goal[0], y - self.goal[1]) < GOAL_R:
            self.clear_level()
            return
        # Rare off-map easter egg: a clean upper-left escape skips the sector.
        if x < -15 and y < -15 and not self.secret_found:
            self.secret_found = True
            self.add_text(40, 56, "SECRET ROUTE!", 10)
            self.clear_level()
            return
        if x < -15 or x > W + 15 or y < -15 or y > H + 15:
            self.lose_probe("LOST", False)
        elif p["age"] > FLIGHT_LIMIT or pyxel.btnp(pyxel.KEY_R):
            self.lose_probe("ABORT", False)

    def clear_level(self):
        self.bonus = 100 + 20 * self.shots + 50 * self.level_stars
        self.score += self.bonus
        self.stars_total += self.level_stars
        self.burst(self.goal[0], self.goal[1], 40, (11, 3, 10, 7, 12), 3.0, 30)
        self.flash = 3
        self.shake = 6
        pyxel.play(1, 3)
        self.probe = None
        self.state = "clear"
        self.state_t = 0

    # ------------------------------------------------------------ sandbox lab
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

    def tele_lines(self):
        lines = [f"STATE {self.state.upper()}", f"FRAME {pyxel.frame_count}",
                 f"MOUSE {pyxel.mouse_x},{pyxel.mouse_y}", f"PART {len(self.particles)}"]
        if self.state == "sandbox":
            p = self.sb["p"]
            lines += [f"MODE {self.sb['mode'].upper()}", f"POS {int(p['x'])},{int(p['y'])}",
                      f"VEL {p['vx']:.1f},{p['vy']:.1f}", f"OBJ {len(self.sb['objs'])}"]
        elif self.state != "title":
            lines += [f"LEVEL {self.level_idx + 1}", f"SHOTS {self.shots}", f"T {self.t}"]
            if self.probe:
                lines.append(f"SPEED {math.hypot(self.probe['vx'], self.probe['vy']):.1f}")
        return lines

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

    # ------------------------------------------------------------ draw
    def preview(self, vx, vy):
        x, y = self.start
        x, y = float(x), float(y)
        t = self.t
        pts = []
        for i in range(PREVIEW_STEPS):
            x, y, vx, vy, hit = step(x, y, vx, vy, t, self.bodies)
            t += 1
            if hit:
                break
            if i % 3 == 2:
                pts.append((x, y))
        return pts

    def draw(self):
        pyxel.cls(0)
        fc = pyxel.frame_count
        for x, y, c, ph in self.bg:
            pyxel.pset(x, y, 7 if (fc + ph) % 60 < 3 else c)

        if self.state == "title":
            self.draw_title(fc)
        elif self.state == "sandbox":
            self.draw_sandbox(fc)
        else:
            sx, sy = self.shake_offset()
            pyxel.camera(sx, sy)
            self.draw_world(fc)
            pyxel.camera(0, 0)
            self.draw_hud()
            self.draw_overlays(fc)
            if self.state == "play" and self.flare_warning > 0:
                if fc % 4 < 2:
                    pyxel.rectb(1, 11, W - 2, H - 12, 8)
                    pyxel.text(48, 14, "FLARE INCOMING", 8)
            if self.state == "play" and self.flare_active > 0:
                pyxel.rect(0, 10, W, H - 10, 9)
                for yy in range(14, H, 9):
                    pyxel.line(0, yy, W, yy - 5, 8)
                pyxel.text(52, 14, "ION STORM", 7)
        if self.flash > 0 and self.flash % 2 == 1:
            pyxel.rect(0, 0, W, H, 7)
        if self.tele:
            self.draw_telemetry(self.tele_lines())

    def draw_world(self, fc):
        gx, gy = self.goal
        pulse = int(2 * math.sin(fc * 0.2))
        for i, col in enumerate((11, 3, 11)):
            pyxel.circb(gx, gy, max(1, GOAL_R - i * 2 + pulse), col)
        pyxel.circ(gx, gy, 1, 7)

        for b in self.bodies:
            bx, by = body_pos(b, self.t)
            draw_body(b, int(bx), int(by))

        # Shortcut portals and their animated rings.
        for wi, (wx, wy) in enumerate(self.wormholes):
            rr = 5 + int(1.5 * math.sin(fc * 0.18 + wi))
            pyxel.circb(wx, wy, rr, 11)
            pyxel.circb(wx, wy, max(2, rr - 2), 3)
            pyxel.pset(wx, wy, 7)
        # Pulsar warning stripes, then a bright full-height beam.
        for beam in self.pulsar_beams:
            if beam["warn"] > 0:
                if fc % 6 < 3:
                    for yy in range(12, H, 8):
                        pyxel.pset(int(beam["x"]), yy, 10)
            elif beam["life"] > 0:
                pyxel.rect(int(beam["x"]) - 1, 10, 3, H - 10, 8)
                pyxel.line(int(beam["x"]), 10, int(beam["x"]), H - 1, 7)

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

        stx, sty = self.start
        if self.state == "play" and self.probe is None and self.dead_timer == 0:
            pyxel.circb(stx, sty, 4 + (fc // 8) % 2, 6)
            pyxel.circ(stx, sty, 2, 7)

        if self.aim and self.probe is None:
            vx, vy, mag = self.aim_vector()
            bx = stx - vx / LAUNCH_K
            by = sty - vy / LAUNCH_K
            pyxel.line(stx, sty, bx, by, 13)
            pyxel.circb(bx, by, 2, 13)
            for px, py in self.preview(vx, vy):
                pyxel.pset(px, py, 7)
            pw = mag / MAX_DRAG
            pyxel.rect(2, 110, 30, 5, 5)
            pyxel.rect(3, 111, int(28 * pw), 3, 11 if pw < 0.5 else (10 if pw < 0.85 else 8))

        for i, (tx, ty) in enumerate(self.trail):
            pyxel.pset(tx, ty, 5 if i < len(self.trail) * 0.4 else (13 if i < len(self.trail) * 0.8 else 6))
        if self.probe:
            pyxel.circ(self.probe["x"], self.probe["y"], 2, 7)
            pyxel.pset(self.probe["x"], self.probe["y"], 10)

        for p in self.particles:
            pyxel.pset(p[0], p[1], p[5])
        for t in self.texts:
            stext(int(t[0]), int(t[1]), t[2], t[3])

    def draw_hud(self):
        pyxel.rect(0, 0, W, 9, 1)
        pyxel.line(0, 9, W, 9, 5)
        phase_name = next((n for n, lo, hi in PHASES if lo <= self.level_idx < hi), "PHASE")
        pyxel.text(2, 2, f"{self.level_idx + 1} {self.name}", 13)
        pyxel.text(2, 11, phase_name, 5)
        pyxel.text(68, 2, f"{self.score:05d}", 10)
        for i in range(SHOTS):
            pyxel.circ(W - 6 - i * 7, 4, 2, 7 if i < self.shots else 5)
        if self.state == "play":
            hint = "R: ABORT FLIGHT" if self.probe else "DRAG TO FIRE - R: RESET"
            pyxel.text(W - len(hint) * 4 - 2, 112, hint, 5)

    def draw_overlays(self, fc):
        blink = fc % 30 < 20
        if self.state == "clear":
            panel(22, 34, 116, 54)
            ctext(41, "SECTOR CLEARED", 11)
            ctext(53, f"STARS {self.level_stars}/{len(self.stars)}", 10)
            ctext(61, f"PROBES LEFT {self.shots}", 7)
            ctext(69, f"BONUS +{self.bonus}", 10)
            if blink and self.state_t > 15:
                ctext(79, "CLICK TO CONTINUE", 13)
        elif self.state == "fail":
            panel(22, 38, 116, 44)
            ctext(46, "SIGNAL LOST", 8)
            ctext(57, "OUT OF PROBES", 7)
            if blink and self.state_t > 15:
                ctext(70, "CLICK TO RETRY", 13)
        elif self.state == "win":
            panel(14, 22, 132, 78)
            ctext(30, "ALL SECTORS CLEARED", 11)
            ctext(42, f"SCORE {self.score}", 10)
            ctext(52, f"STARS {self.stars_total}/{TOTAL_STARS}", 10)
            ctext(62, f"PROBES USED {self.total_shots}", 7)
            if self.total_shots <= 8:
                rank = "ADMIRAL"
            elif self.total_shots <= 12:
                rank = "NAVIGATOR"
            else:
                rank = "CADET"
            ctext(74, f"RANK: {rank}", 14)
            if blink and self.state_t > 20:
                ctext(88, "CLICK TO PLAY AGAIN", 13)

    def draw_title(self, fc):
        pyxel.camera(0, 0)
        big_text(32, 16, "STARLING", 3, 10, 9, 2)
        ctext(42, "A GRAVITY SLINGSHOT PUZZLE", 6)
        ctext(50, "3 PHASES - 9 SECTORS", 10)
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
        ctext(113, "DRAG TO AIM - RELEASE TO FIRE", 5)


Game()
