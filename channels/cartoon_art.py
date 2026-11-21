"""Original cartoon characters and objects, drawn procedurally (no copyrighted assets)."""
import math

PALETTE = {
    "red": (235, 64, 52), "orange": (255, 146, 43), "yellow": (255, 214, 10), "green": (76, 187, 72),
    "blue": (46, 134, 222), "purple": (155, 89, 182), "pink": (255, 120, 180), "brown": (150, 95, 55),
}

CHARACTERS = {
    "Bubbo": {"color": (90, 170, 255), "extra": "antenna"},
    "Pip": {"color": (255, 205, 60), "extra": "tuft"},
    "Mimi": {"color": (255, 140, 190), "extra": "ears"},
    "Tuko": {"color": (110, 210, 120), "extra": "nubs"},
    "Zuzu": {"color": (180, 130, 255), "extra": "antenna"},
}


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def blob(d, cx, cy, r, color, t, talking=False, jump=0.0, extra="antenna"):
    """A round, friendly creature. `jump` 0..1 lifts it; `talking` animates mouth + wobble."""
    wob = math.sin(t * 18) * 0.04 if talking else math.sin(t * 2.5) * 0.015
    cy = cy - jump * r * 0.9 + math.sin(t * 2.5) * 4
    rx, ry = r * (1 + wob), r * (1 - wob)
    dark = shade(color, 0.6)
    # feet
    for sx in (-1, 1):
        d.ellipse([cx + sx * r * 0.45 - r * 0.28, cy + ry * 0.82, cx + sx * r * 0.45 + r * 0.28, cy + ry * 1.08],
                  fill=shade(color, 0.8), outline=dark, width=6)
    # extras behind/above body
    if extra == "antenna":
        for sx in (-1, 1):
            x2 = cx + sx * r * 0.45 + math.sin(t * 4 + sx) * 10
            d.line([cx + sx * r * 0.25, cy - ry * 0.85, x2, cy - ry * 1.45], fill=dark, width=8)
            d.ellipse([x2 - 18, cy - ry * 1.45 - 18, x2 + 18, cy - ry * 1.45 + 18], fill=(255, 230, 90), outline=dark, width=5)
    elif extra == "ears":
        for sx in (-1, 1):
            ex = cx + sx * r * 0.62
            d.ellipse([ex - r * 0.3, cy - ry * 1.05, ex + r * 0.3, cy - ry * 0.45], fill=color, outline=dark, width=6)
            d.ellipse([ex - r * 0.15, cy - ry * 0.92, ex + r * 0.15, cy - ry * 0.6], fill=(255, 200, 220))
    elif extra == "nubs":
        for sx in (-1, 1):
            ex = cx + sx * r * 0.4
            d.polygon([(ex - 22, cy - ry * 0.9), (ex + 22, cy - ry * 0.9), (ex, cy - ry * 1.25)], fill=(255, 240, 200), outline=dark)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=color, outline=dark, width=8)
    if extra == "tuft":
        for k in (-1, 0, 1):
            d.arc([cx + k * 28 - 30, cy - ry - 50, cx + k * 28 + 30, cy - ry + 10], 200, 340, fill=dark, width=7)
    # belly
    d.ellipse([cx - rx * 0.55, cy + ry * 0.05, cx + rx * 0.55, cy + ry * 0.85], fill=shade(color, 1.18))
    # eyes (blink every ~3.3s)
    blink = (t % 3.3) < 0.12
    for sx in (-1, 1):
        ex, ey = cx + sx * r * 0.33, cy - ry * 0.25
        if blink:
            d.arc([ex - 30, ey - 12, ex + 30, ey + 24], 200, 340, fill=(30, 30, 40), width=7)
        else:
            d.ellipse([ex - 34, ey - 42, ex + 34, ey + 42], fill="white", outline=dark, width=4)
            px = ex + math.sin(t * 0.9) * 6
            d.ellipse([px - 18, ey - 14, px + 18, ey + 26], fill=(30, 30, 40))
            d.ellipse([px - 8, ey - 8, px + 3, ey + 3], fill="white")
        d.ellipse([ex - 30 + sx * 22, ey + 48, ex + 14 + sx * 22, ey + 70], fill=(255, 150, 170))
    # mouth
    my = cy + ry * 0.22
    if talking:
        h = 18 + abs(math.sin(t * 22)) * 34
        d.ellipse([cx - 40, my - 10, cx + 40, my + h], fill=(120, 30, 50), outline=dark, width=5)
        d.ellipse([cx - 22, my + h * 0.45, cx + 22, my + h + 4], fill=(255, 120, 140))
    else:
        d.arc([cx - 55, my - 40, cx + 55, my + 30], 20, 160, fill=(80, 30, 40), width=9)


# ---------------------------------------------------------------- objects
def _star(cx, cy, r, n=5, inner=0.45, rot=-90):
    pts = []
    for i in range(n * 2):
        rr = r if i % 2 == 0 else r * inner
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def draw_object(d, kind, cx, cy, s, color, outline=(40, 40, 50)):
    """Draw object `kind` centered at (cx,cy) with half-size s."""
    ow = max(4, int(s / 18))
    if kind == "balloon":
        d.line([cx, cy + s * 0.75, cx + s * 0.1, cy + s * 1.15], fill=outline, width=ow)
        d.polygon([(cx - s * 0.1, cy + s * 0.8), (cx + s * 0.1, cy + s * 0.8), (cx, cy + s * 0.66)], fill=color)
        d.ellipse([cx - s * 0.62, cy - s * 0.9, cx + s * 0.62, cy + s * 0.72], fill=color, outline=outline, width=ow)
        d.ellipse([cx - s * 0.35, cy - s * 0.65, cx - s * 0.15, cy - s * 0.3], fill=(255, 255, 255))
    elif kind == "star":
        d.polygon(_star(cx, cy, s), fill=color, outline=outline, width=ow)
    elif kind == "apple":
        d.line([cx, cy - s * 0.6, cx + s * 0.1, cy - s * 0.95], fill=(110, 70, 30), width=ow * 2)
        d.ellipse([cx + s * 0.05, cy - s * 0.95, cx + s * 0.5, cy - s * 0.7], fill=(70, 170, 60), outline=outline, width=ow // 2)
        d.ellipse([cx - s * 0.85, cy - s * 0.7, cx + s * 0.85, cy + s * 0.85], fill=color, outline=outline, width=ow)
        d.ellipse([cx - s * 0.5, cy - s * 0.45, cx - s * 0.25, cy - s * 0.15], fill=(255, 255, 255))
    elif kind == "fish":
        d.polygon([(cx + s * 0.45, cy), (cx + s, cy - s * 0.5), (cx + s, cy + s * 0.5)], fill=color, outline=outline, width=ow)
        d.ellipse([cx - s * 0.9, cy - s * 0.55, cx + s * 0.6, cy + s * 0.55], fill=color, outline=outline, width=ow)
        d.ellipse([cx - s * 0.6, cy - s * 0.25, cx - s * 0.35, cy], fill="white", outline=outline, width=ow // 2)
        d.ellipse([cx - s * 0.52, cy - s * 0.17, cx - s * 0.42, cy - s * 0.07], fill=outline)
    elif kind == "flower":
        d.line([cx, cy, cx, cy + s * 1.1], fill=(60, 150, 60), width=ow * 2)
        for i in range(6):
            a = i * math.pi / 3
            px, py = cx + math.cos(a) * s * 0.5, cy + math.sin(a) * s * 0.5
            d.ellipse([px - s * 0.38, py - s * 0.38, px + s * 0.38, py + s * 0.38], fill=color, outline=outline, width=ow // 2)
        d.ellipse([cx - s * 0.3, cy - s * 0.3, cx + s * 0.3, cy + s * 0.3], fill=(255, 220, 60), outline=outline, width=ow // 2)
    elif kind == "heart":
        r = s * 0.5
        d.ellipse([cx - s, cy - s * 0.75, cx, cy + s * 0.25], fill=color)
        d.ellipse([cx, cy - s * 0.75, cx + s, cy + s * 0.25], fill=color)
        d.polygon([(cx - s * 0.97, cy - s * 0.1), (cx + s * 0.97, cy - s * 0.1), (cx, cy + s)], fill=color)
        d.ellipse([cx - s * 0.7, cy - s * 0.5, cx - s * 0.45, cy - s * 0.25], fill=(255, 255, 255))
    elif kind == "ball":
        d.ellipse([cx - s * 0.85, cy - s * 0.85, cx + s * 0.85, cy + s * 0.85], fill=color, outline=outline, width=ow)
        d.arc([cx - s * 0.85, cy - s * 0.35, cx + s * 0.85, cy + s * 0.35], 0, 180, fill=(255, 255, 255), width=ow * 2)
        d.arc([cx - s * 0.85, cy - s * 0.35, cx + s * 0.85, cy + s * 0.35], 180, 360, fill=(255, 255, 255), width=ow * 2)
    elif kind == "house":
        d.rectangle([cx - s * 0.7, cy - s * 0.2, cx + s * 0.7, cy + s * 0.85], fill=color, outline=outline, width=ow)
        d.polygon([(cx - s * 0.9, cy - s * 0.15), (cx + s * 0.9, cy - s * 0.15), (cx, cy - s * 0.95)], fill=(200, 70, 60), outline=outline, width=ow)
        d.rectangle([cx - s * 0.18, cy + s * 0.3, cx + s * 0.18, cy + s * 0.85], fill=(130, 80, 40), outline=outline, width=ow // 2)
        d.rectangle([cx + s * 0.3, cy, cx + s * 0.55, cy + s * 0.25], fill=(200, 235, 255), outline=outline, width=ow // 2)
    elif kind == "tree":
        d.rectangle([cx - s * 0.15, cy + s * 0.2, cx + s * 0.15, cy + s], fill=(130, 80, 40), outline=outline, width=ow // 2)
        for ox, oy, rr in ((0, -0.35, 0.55), (-0.4, 0.0, 0.45), (0.4, 0.0, 0.45)):
            d.ellipse([cx + (ox - rr) * s, cy + (oy - rr) * s, cx + (ox + rr) * s, cy + (oy + rr) * s], fill=color, outline=outline, width=ow // 2)
    elif kind == "umbrella":
        d.line([cx, cy - s * 0.2, cx, cy + s * 0.8], fill=outline, width=ow * 2)
        d.arc([cx - s * 0.3, cy + s * 0.6, cx, cy + s * 0.95], 0, 180, fill=outline, width=ow * 2)
        d.pieslice([cx - s, cy - s * 0.8, cx + s, cy + s * 0.4], 180, 360, fill=color, outline=outline, width=ow)
    elif kind == "car":
        d.rounded_rectangle([cx - s, cy - s * 0.15, cx + s, cy + s * 0.45], radius=int(s * 0.2), fill=color, outline=outline, width=ow)
        d.rounded_rectangle([cx - s * 0.55, cy - s * 0.6, cx + s * 0.45, cy - s * 0.1], radius=int(s * 0.2), fill=color, outline=outline, width=ow)
        d.rectangle([cx - s * 0.42, cy - s * 0.5, cx - s * 0.08, cy - s * 0.18], fill=(200, 235, 255))
        d.rectangle([cx + s * 0.02, cy - s * 0.5, cx + s * 0.33, cy - s * 0.18], fill=(200, 235, 255))
        for wx in (-0.55, 0.55):
            d.ellipse([cx + (wx - 0.25) * s, cy + s * 0.2, cx + (wx + 0.25) * s, cy + s * 0.7], fill=(50, 50, 60), outline=outline, width=ow // 2)
    else:
        raise ValueError(kind)


OBJECTS = {  # kind: (singular, plural, natural color, emoji for titles)
    "balloon": ("balloon", "balloons", "red", "🎈"), "star": ("star", "stars", "yellow", "⭐"),
    "apple": ("apple", "apples", "red", "🍎"), "fish": ("fish", "fish", "orange", "🐟"),
    "flower": ("flower", "flowers", "purple", "🌸"), "heart": ("heart", "hearts", "pink", "💖"),
    "ball": ("ball", "balls", "blue", "⚽"), "house": ("house", "houses", "yellow", "🏠"),
    "tree": ("tree", "trees", "green", "🌳"), "umbrella": ("umbrella", "umbrellas", "purple", "☂️"),
    "car": ("car", "cars", "blue", "🚗"),
}

COLOR_FRIENDS = {
    "red": ["a strawberry", "a fire truck", "a ladybug"], "orange": ["a carrot", "a pumpkin", "an orange"],
    "yellow": ["a banana", "the sun", "a little duck"], "green": ["a frog", "the grass", "a leaf"],
    "blue": ["the sky", "the ocean", "a blueberry"], "purple": ["grapes", "a plum", "lavender"],
    "pink": ["a flamingo", "a piglet", "cotton candy"], "brown": ["a teddy bear", "chocolate", "a tree trunk"],
}
