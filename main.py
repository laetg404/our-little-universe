import math
import random
import time
import tkinter
import turtle

# NUESTRO PEQUEÑO UNIVERSO ♡
# ESPACIO = pausa/reanudar | ESC = salir

WIDTH, HEIGHT = 1000, 700
FPS = 30
FRAME_MS = 1000 // FPS
random.seed(14)
dyn = random.Random()          # aleatoriedad "viva" (estrellas fugaces)

BG_TOP, BG_BOTTOM = "#04071A", "#16204D"
PLANET_Y, R = 15, 132          # centro vertical y radio del planeta
LIGHT = (-34, PLANET_Y + 34, 138)   # círculo de luz: lo que queda fuera es sombra
OCEAN, OCEAN_RIM = "#456BA5", "#7896C9"
LAND, ICE = "#83A88E", "#9CB8D3"
NIGHT = "#0B1233"

screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("Nuestro pequeño universo ♡")
screen.bgcolor("#0A1030")
screen.tracer(0, 0)


def make_turtle():
    t = turtle.Turtle(visible=False)
    t.hideturtle()
    t.speed(0)
    t.penup()
    return t


static = make_turtle()   # se dibuja una sola vez
motion = make_turtle()   # se redibuja en cada fotograma

frame = 0
paused = False
running = True
shooter = None


# ---------------------------------------------------------------- color ----
def _rgb(c):
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return "#%02X%02X%02X" % tuple(
        round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))


def bg_at(y):
    return mix(BG_TOP, BG_BOTTOM, (HEIGHT / 2 - y) / HEIGHT)


def backdrop(x, y):
    """Color de lo que hay detrás de un punto (planeta o cielo)."""
    return OCEAN if math.hypot(x, y - PLANET_Y) < R else bg_at(y)


def is_lit(x, y):
    return (x - LIGHT[0]) ** 2 + (y - LIGHT[1]) ** 2 <= LIGHT[2] ** 2


# ------------------------------------------------------------- primitivas --
def move(t, x, y):
    t.penup()
    t.goto(x, y)


def disk(t, x, y, r, color, outline=None, width=1):
    move(t, x, y - r)
    t.setheading(0)
    t.pensize(width)
    t.color(outline or color, color)
    t.pendown()
    t.begin_fill()
    t.circle(r, steps=10 if r < 3 else min(90, 14 + int(r * 0.6)))
    t.end_fill()
    t.penup()


def path(t, points, color, width=1):
    if len(points) < 2:
        return
    move(t, *points[0])
    t.pencolor(color)
    t.pensize(width)
    t.pendown()
    for p in points[1:]:
        t.goto(*p)
    t.penup()


def polygon(t, pts, color):
    move(t, *pts[0])
    t.color(color)
    t.pensize(1)
    t.pendown()
    t.begin_fill()
    for p in pts[1:]:
        t.goto(*p)
    t.end_fill()
    t.penup()


HEART_UNIT = []
for _i in range(61):
    _a = math.tau * _i / 60
    HEART_UNIT.append((
        16 * math.sin(_a) ** 3 / 32,
        (13 * math.cos(_a) - 5 * math.cos(2 * _a)
         - 2 * math.cos(3 * _a) - math.cos(4 * _a)) / 32))


def heart(t, x, y, size, color):
    polygon(t, [(x + px * size, y + py * size) for px, py in HEART_UNIT], color)


def sparkle(t, x, y, r, color):
    disk(t, x, y, r, color)
    path(t, [(x - r * 2.4, y), (x + r * 2.4, y)], color, 1)
    path(t, [(x, y - r * 2.4), (x, y + r * 2.4)], color, 1)


def crescent(t, c1, r1, c2, r2, color, n=40):
    """Círculo 1 menos círculo 2, como un único polígono (luna, sombra)."""
    (x1, y1), (x2, y2) = c1, c2
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    phi = math.atan2(dy, dx)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    alpha = math.acos(max(-1, min(1, a / r1)))
    beta = math.acos(max(-1, min(1, (d - a) / r2)))
    psi = phi + math.pi
    pts = []
    for i in range(n + 1):
        th = phi + alpha + (math.tau - 2 * alpha) * i / n
        pts.append((x1 + r1 * math.cos(th), y1 + r1 * math.sin(th)))
    for i in range(1, n):
        th = psi + beta - 2 * beta * i / n
        pts.append((x2 + r2 * math.cos(th), y2 + r2 * math.sin(th)))
    polygon(t, pts, color)


def shaded_path(t, pts, lit_col, dark_col, width):
    """Línea que cambia de color entre la zona iluminada y la sombra."""
    if len(pts) < 2:
        return
    run, run_lit = [pts[0]], None
    for p, q in zip(pts, pts[1:]):
        lit = is_lit((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if run_lit is None:
            run_lit = lit
        if lit != run_lit:
            path(t, run, lit_col if run_lit else dark_col, width)
            run, run_lit = [p], lit
        run.append(q)
    path(t, run, lit_col if run_lit else dark_col, width)


# ------------------------------------------------------------- datos fijos --
ORBITS = [
    dict(rx=205, ry=75, tilt=-20, phase=0, speed=.010, size=14, color="#FFB5C8"),
    dict(rx=250, ry=100, tilt=22, phase=2, speed=-.008, size=11, color="#F5D5E8"),
    dict(rx=290, ry=118, tilt=-8, phase=4, speed=.006, size=10, color="#D7C8FF"),
]
ORBIT_PTS = []
TRAIL = 6


def orbit_xy(o, a):
    ang = math.radians(o["tilt"])
    x, y = o["rx"] * math.cos(a), o["ry"] * math.sin(a)
    return (x * math.cos(ang) - y * math.sin(ang),
            PLANET_Y + x * math.sin(ang) + y * math.cos(ang))


for _o in ORBITS:
    ORBIT_PTS.append([orbit_xy(_o, math.tau * i / 120) for i in range(121)])

CONSTELLATIONS = [
    [(-365, 90), (-325, 125), (-282, 105), (-260, 150), (-220, 165)],
    [(255, -160), (290, -125), (335, -140), (365, -95), (410, -75)],
    [(-390, -190), (-355, -165), (-325, -195), (-290, -180)],
]

STAR_COLORS = ["#FFF1CC", "#DCE8FF", "#E8D9FF", "#FFD9E6"]
TWINKLES = []


def star_position():
    while True:
        x, y = random.randint(-480, 480), random.randint(-330, 335)
        if math.hypot(x, y - PLANET_Y) < 205:
            continue
        if y > 282 and abs(x) < 220:
            continue
        if y < -222 and abs(x) < 250:
            continue
        if math.hypot(x - 390, y - 245) < 48:
            continue
        return x, y


# ----------------------------------------------------------- escena fija ----
def nebula(cx, cy, r, tint, strength):
    base = bg_at(cy)
    layers = 7
    for i in range(layers):
        disk(static, cx, cy, r * (1 - i / layers),
             mix(base, tint, strength * (i + 1) / layers))


def draw_static_scene():
    # Cielo en degradado.
    band = 10
    for i in range(HEIGHT // band + 2):
        y = HEIGHT / 2 - i * band
        c = bg_at(y - band / 2)
        polygon(static, [(-WIDTH / 2 - 2, y), (WIDTH / 2 + 2, y),
                         (WIDTH / 2 + 2, y - band - 1), (-WIDTH / 2 - 2, y - band - 1)], c)

    # Nebulosas suaves.
    nebula(-330, -150, 130, "#5B3A8C", .30)
    nebula(-250, -210, 90, "#3F4FA0", .25)
    nebula(340, 80, 120, "#2F5C9A", .26)
    nebula(420, 20, 80, "#7A3F86", .22)

    # Estrellas de fondo.
    for _ in range(130):
        x, y = star_position()
        r = random.choice([.8, 1.1, 1.5, 1.8])
        c = mix(bg_at(y), random.choice(STAR_COLORS), random.uniform(.5, 1))
        disk(static, x, y, r, c)

    # Estrellas que titilan (se animan en cada fotograma).
    for _ in range(34):
        x, y = star_position()
        TWINKLES.append((x, y, random.choice([1.0, 1.3, 1.7]),
                         random.choice(STAR_COLORS),
                         random.uniform(0, math.tau), random.uniform(.03, .09)))

    # Halo del planeta y órbitas.
    for r, k in [(192, .025), (178, .04), (166, .06), (156, .085)]:
        disk(static, 0, PLANET_Y, r, mix(bg_at(PLANET_Y), "#4A74C8", k))
    for pts in ORBIT_PTS:
        path(static, pts, "#36466F", 1)

    # Constelaciones.
    for pts in CONSTELLATIONS:
        path(static, pts, "#566B9E", 1)

    # Luna creciente con resplandor.
    for r, k in [(72, .04), (56, .07), (43, .11)]:
        disk(static, 390, 245, r, mix(bg_at(245), "#F8EBCB", k))
    crescent(static, (390, 245), 29, (405, 258), 27, "#F8EBCB")

    # Título y dedicatoria.
    static.color("#2B3B72")
    move(static, 1, 294)
    static.write("NUESTRO PEQUEÑO UNIVERSO", align="center", font=("Georgia", 21, "italic"))
    static.color("#C9D6F2")
    move(static, 0, 295)
    static.write("NUESTRO PEQUEÑO UNIVERSO", align="center", font=("Georgia", 21, "italic"))
    heart(static, 0, 272, 11, "#FFB5C8")

    static.color("#F2E7D8")
    move(static, 0, -255)
    static.write("De todos los universos posibles,", align="center", font=("Georgia", 16, "italic"))
    move(static, 0, -285)
    static.write("qué suerte coincidir en este contigo. ♡", align="center", font=("Georgia", 16, "italic"))
    static.color("#8797C4")
    move(static, 0, -322)
    static.write("Un pequeño universo hecho para nosotras dos", align="center", font=("Georgia", 10, "italic"))
    static.color("#4F5E8F")
    move(static, 485, -334)
    static.write("ESPACIO · pausa     ESC · salir", align="right", font=("Georgia", 8, "italic"))


# ------------------------------------------------------------ animación ----
def draw_planet():
    cx, cy = 0, PLANET_Y
    pulse = .5 + .5 * math.sin(frame * .04)

    # Atmósfera que "respira".
    disk(motion, cx, cy, 146, mix(bg_at(cy), "#4B76C9", .18 + .08 * pulse))
    disk(motion, cx, cy, 139, mix(bg_at(cy), "#6C93DA", .34 + .10 * pulse))
    disk(motion, cx, cy, R, OCEAN, OCEAN_RIM, 2)

    # Brillo del lado iluminado y sombra del lado opuesto.
    disk(motion, -48, cy + 52, 58, mix(OCEAN, "#A9C4EE", .16))
    disk(motion, -52, cy + 56, 34, mix(OCEAN, "#A9C4EE", .28))
    crescent(motion, (cx, cy), R, (LIGHT[0], LIGHT[1]), LIGHT[2], "#2A4373")

    # Olas con curvatura de esfera.
    phase = frame * .012
    wave_colors = ["#6F91BD", "#547FB0", "#8AA8C9", "#3F669D"]
    for j in range(7):
        y0 = cy - 88 + j * 28
        pts = []
        for k in range(37):
            x = -112 + k * 6.2
            y = y0 + 7 * math.sin(k * .22 + phase + j * .7) + 9 * (x / R) ** 2 - 4.5
            if x * x + (y - cy) ** 2 <= 124 ** 2:
                pts.append((cx + x, y))
        col = wave_colors[j % 4]
        shaded_path(motion, pts, col, mix(col, NIGHT, .42), 5 if j % 2 == 0 else 3)

    # Continentes a la deriva.
    drift = 16 * math.sin(phase)
    lands = [(-53 + drift, 66, 26, LAND), (-29 + drift, 57, 20, LAND),
             (55 - drift, -38, 33, LAND), (78 - drift, -20, 21, LAND),
             (-4 + drift * .4, -78, 17, LAND), (-48, 92, 12, ICE)]
    for x, y, r, col in lands:
        c = col if is_lit(x, y) else mix(col, NIGHT, .42)
        disk(motion, x, y, r, c, mix(c, "#FFFFFF", .10), 1)


def orbit_layers():
    back, front = [], []
    for o in ORBITS:
        direction = 1 if o["speed"] > 0 else -1
        a0 = o["phase"] + frame * o["speed"]
        for k in range(TRAIL, 0, -1):
            a = a0 - direction * k * .055
            x, y = orbit_xy(o, a)
            depth = -math.sin(a)
            fade = k / (TRAIL + 1)
            col = mix(o["color"], backdrop(x, y), .25 + .65 * fade)
            r = o["size"] * .16 * (1 - fade * .7) * (1 + .2 * depth)
            (front if depth > 0 else back).append(("dot", x, y, r, col))
        x, y = orbit_xy(o, a0)
        depth = -math.sin(a0)
        pulse = 1 + .12 * math.sin(frame * .08 + o["phase"])
        size = o["size"] * pulse * (1 + .25 * depth)
        col = o["color"] if depth > 0 else mix(o["color"], bg_at(y), .38)
        (front if depth > 0 else back).append(("heart", x, y, size, col))
    return back, front


def draw_items(items):
    for kind, x, y, s, col in items:
        if kind == "heart":
            heart(motion, x, y, s, col)
        else:
            disk(motion, x, y, s, col)


def draw_front_arcs():
    for pts in ORBIT_PTS:
        path(motion, pts[60:], "#6A7DB3", 1)


def draw_twinkles():
    for x, y, r, col, ph, sp in TWINKLES:
        b = .5 + .5 * math.sin(frame * sp + ph)
        if b < .2:
            continue
        c = mix(bg_at(y), col, .3 + .7 * b)
        if b > .85:
            sparkle(motion, x, y, r * .8, c)
        else:
            disk(motion, x, y, r * (.6 + .5 * b), c)


def draw_constellation_stars():
    for gi, pts in enumerate(CONSTELLATIONS):
        for i, (x, y) in enumerate(pts):
            b = .5 + .5 * math.sin(frame * .06 + i + gi)
            sparkle(motion, x, y, 1.8 + 1.4 * b,
                    mix(bg_at(y), "#E7E9FF", .55 + .45 * b))
    for i in range(0, 10, 2):
        x = -440 + i * 96
        y = 220 + 10 * math.sin(frame * .035 + i)
        b = .5 + .5 * math.sin(frame * .05 + i)
        sparkle(motion, x, y, 1.3, mix(bg_at(y), "#DCE8FF", .5 + .5 * b))


def draw_shooting_star():
    global shooter
    if shooter is None:
        if dyn.random() < .004:
            shooter = [dyn.uniform(-250, 0), dyn.uniform(205, 265),
                       -dyn.uniform(8, 11), -dyn.uniform(3, 4.5), 0]
        return
    x, y, vx, vy, age = shooter
    x, y, age = x + vx, y + vy, age + 1
    shooter = [x, y, vx, vy, age]
    life = 26
    env = min(1, age / 4, (life - age) / 8)
    if age >= life or x < -470 or env <= 0:
        shooter = None
        return
    for k in range(10):
        px, py = x - vx * k * .55, y - vy * k * .55
        disk(motion, px, py, max(.6, 2.3 * (1 - k / 11)),
             mix(bg_at(py), "#FFFFFF", env * (1 - k / 10) * .95))


def render():
    motion.clear()
    back, front = orbit_layers()
    draw_items(back)          # corazones detrás del planeta
    draw_planet()
    draw_front_arcs()         # tramo delantero de las órbitas
    draw_items(front)         # corazones delante del planeta
    draw_twinkles()
    draw_constellation_stars()
    draw_shooting_star()


def animate():
    global frame
    if not running:
        return
    t0 = time.perf_counter()
    try:
        if not paused:
            frame += 1
            render()
        screen.update()
        elapsed = int((time.perf_counter() - t0) * 1000)
        screen.ontimer(animate, max(1, FRAME_MS - elapsed))
    except (turtle.Terminator, tkinter.TclError):
        return


def toggle_pause():
    global paused
    paused = not paused


def close():
    global running
    running = False
    try:
        screen.bye()
    except (turtle.Terminator, tkinter.TclError):
        pass


def main():
    draw_static_scene()
    screen.update()
    screen.listen()
    screen.onkey(toggle_pause, "space")
    screen.onkey(close, "Escape")
    try:
        screen.getcanvas().winfo_toplevel().protocol("WM_DELETE_WINDOW", close)
    except Exception:
        pass
    screen.ontimer(animate, FRAME_MS)
    try:
        screen.mainloop()
    except turtle.Terminator:
        pass


if __name__ == "__main__":
    main()