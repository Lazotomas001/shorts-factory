"""Kids channel: original cartoon learning Shorts (counting, colors, guess-the-shadow).

Every video randomizes character, scene palette, objects, music key/tempo/instrument and
script wording, and the ledger prevents repeating the same topic, so output is not a
copy-paste template.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from factory import audio
from factory.render import W, H, render_video, vgradient, text_block, ease_out_back, clamp01, fit_size, silhouette
from factory.timeline import Timeline
from channels.cartoon_art import CHARACTERS, OBJECTS, PALETTE, COLOR_FRIENDS, blob, draw_object, shade

FONT = "ComicNeue-Bold.otf"
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
VOICES = ["en-US-AnaNeural", "en-US-JennyNeural", "en-US-AriaNeural", "en-GB-MaisieNeural"]
SCENES = [  # sky top, sky bottom, hill back, hill front
    ((120, 200, 255), (210, 240, 255), (120, 200, 110), (90, 180, 80)),
    ((255, 190, 150), (255, 235, 200), (150, 200, 120), (110, 175, 90)),
    ((170, 150, 255), (230, 215, 255), (130, 200, 160), (90, 170, 130)),
    ((100, 215, 230), (220, 250, 245), (240, 220, 150), (225, 195, 120)),  # beach
]


class Scene:
    def __init__(self, rng):
        top, bot, h1, h2 = SCENES[int(rng.integers(0, len(SCENES)))]
        self.bg = vgradient(top, bot)
        d = ImageDraw.Draw(self.bg)
        ph = rng.uniform(0, 6)
        for col, base, amp, freq in ((h1, 1330, 50, 0.004), (h2, 1430, 35, 0.006)):
            pts = [(x, base + amp * math.sin(x * freq + ph)) for x in range(0, W + 20, 20)]
            d.polygon(pts + [(W, H), (0, H)], fill=col)
        self.clouds = [(rng.uniform(0, W), rng.uniform(140, 420), rng.uniform(0.7, 1.3), rng.uniform(8, 20)) for _ in range(4)]
        self.sun = rng.random() < 0.6

    def draw(self, t):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        if self.sun:
            cx, cy = 900, 230
            for i in range(10):
                a = t * 0.4 + i * math.pi / 5
                d.line([cx + math.cos(a) * 95, cy + math.sin(a) * 95, cx + math.cos(a) * 140, cy + math.sin(a) * 140],
                       fill=(255, 210, 60), width=12)
            d.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], fill=(255, 220, 70))
        for x, y, s, v in self.clouds:
            x = (x + t * v) % (W + 300) - 150
            for ox, oy, r in ((-60, 10, 50), (0, -15, 65), (60, 10, 50)):
                d.ellipse([x + ox * s - r * s, y + oy * s - r * s, x + ox * s + r * s, y + oy * s + r * s], fill="white")
        return img, d


def _confetti(rng, n=90):
    cols = list(PALETTE.values())
    return [(rng.uniform(0, W), rng.uniform(-400, 0), rng.uniform(250, 550), rng.uniform(0, 6), cols[i % len(cols)]) for i in range(n)]


def _draw_confetti(d, parts, age):
    for x, y0, v, ph, c in parts:
        y = y0 + v * age
        if 0 < y < H:
            xx = x + math.sin(age * 3 + ph) * 30
            d.rectangle([xx - 10, y - 6, xx + 10, y + 6], fill=c)


def _layout(n):
    cols = 3 if n <= 6 else 4
    rows = math.ceil(n / cols)
    s = min(170, 900 / cols / 1.9)
    pos = []
    for i in range(n):
        r, c = divmod(i, cols)
        in_row = min(cols, n - r * cols)
        x = W / 2 + (c - (in_row - 1) / 2) * (900 / cols)
        y = 820 + (r - (rows - 1) / 2) * (s * 2.5)
        pos.append((x, y))
    return pos, s


# ------------------------------------------------------------------ formats
def build_counting(tl, rng, char, obj):
    sing, plural, color, emoji = OBJECTS[obj]
    n = int(rng.integers(5, 11))
    col = PALETTE[color] if (rng.random() < 0.5 or obj == "tree") else None
    colors = [col or list(PALETTE.values())[int(rng.integers(0, 8))] for _ in range(n)]
    opener = rng.choice([f"Hi friends! {char} found some {plural}. Let's count them together!",
                         f"Hello! It's {char}! How many {plural} can we count today?",
                         f"Look, {plural}! Can you help {char} count them?"])
    tl.say(opener, "intro", title=f"Let's count {plural}!")
    for i in range(1, n + 1):
        tl.fx(audio.pop(), gain=0.5)
        tl.say(NUM_WORDS[i].capitalize() + "!", "count", gap=0.45, i=i)
    tl.fx(audio.fanfare(), gain=0.5)
    tl.say(rng.choice([f"{NUM_WORDS[n].capitalize()} {plural}! Hooray! Great counting!",
                       f"We counted {NUM_WORDS[n]} {plural}! You did it!",
                       f"Yay! There are {NUM_WORDS[n]} {plural}! Amazing job!"]), "finale", i=n)
    tl.say(rng.choice(["Bye bye, friends!", "See you next time!", "Let's play again soon!"]), "outro", i=n)
    state = {"n": n, "colors": colors, "pos": _layout(n)}
    title = f"Let's Count {n} {plural.title()}! {emoji} Counting for Toddlers"
    return state, title, f"count-{obj}-{n}", ["counting", "numbers", "learn to count", f"{plural}", "1 to 10"]


def build_colors(tl, rng, char, obj_kinds):
    names = list(rng.permutation([c for c in PALETTE if c != "brown"]))[:4]
    rounds = [(obj_kinds[i % len(obj_kinds)], c) for i, c in enumerate(names)]
    tl.say(rng.choice([f"Hi friends! Let's learn colors with {char}!",
                       f"Color time with {char}! Shout out each color!",
                       f"Hello! Can you guess the colors with {char}?"]), "intro", title="What color is it?")
    for k, (obj, c) in enumerate(rounds):
        sing = OBJECTS[obj][0]
        tl.say(f"What color is this {sing}?", "ask", gap=0.1, r=k)
        for j in range(3):
            tl.fx(audio.tick(), gain=0.7)
            tl.hold(0.75, "count3", r=k, num=3 - j)
        tl.fx(audio.ding(), gain=0.5)
        friend = rng.choice(COLOR_FRIENDS[c])
        tl.say(f"{c.capitalize()}! {c.capitalize()}, like {friend}!", "reveal", gap=0.5, r=k)
    tl.fx(audio.fanfare(), gain=0.5)
    tl.say(rng.choice(["You know your colors! Great job!", "Wow, you got them all! Bye bye!"]), "finale", r=len(rounds) - 1)
    state = {"rounds": rounds}
    title = f"Learn Colors with {char}! 🌈 " + " ".join(c.title() for c in names) + " | Toddler Learning"
    return state, title, "colors-" + "-".join(f"{o}:{c}" for o, c in rounds), ["colors", "learn colors", "toddler learning", *names]


def build_shadow(tl, rng, char, obj_kinds):
    rounds = obj_kinds[:4]
    tl.say(rng.choice([f"Who's hiding? Guess the shadow with {char}!",
                       f"Peekaboo! Can you guess what's hiding?",
                       f"Shadow game time! What can it be?"]), "intro", title="Guess the shadow!")
    for k, obj in enumerate(rounds):
        tl.say(rng.choice(["What is it?", "Who's hiding?", "Can you guess?"]), "ask", gap=0.1, r=k)
        for j in range(3):
            tl.fx(audio.tick(), gain=0.7)
            tl.hold(0.75, "count3", r=k, num=3 - j)
        tl.fx(audio.ding(), gain=0.5)
        tl.say(f"It's a {OBJECTS[obj][0]}!", "reveal", gap=0.5, r=k)
    tl.fx(audio.fanfare(), gain=0.5)
    tl.say("You're a super guesser! Bye bye!", "finale", r=len(rounds) - 1)
    title = "Guess the Shadow! 🔍 Fun Guessing Game for Kids | " + ", ".join(OBJECTS[o][1].title() for o in rounds)
    return {"rounds": [(o, OBJECTS[o][2]) for o in rounds]}, title, "shadow-" + "-".join(rounds), ["guessing game", "shadow game", "toddler games"]


# ------------------------------------------------------------------ main
def make(out_dir: Path, rng, ledger, channel="kids", fmt=None):
    char = list(CHARACTERS)[int(rng.integers(0, len(CHARACTERS)))]
    cinfo = CHARACTERS[char]
    tl = Timeline(voice=str(rng.choice(VOICES)), rate="-8%", pitch="+0Hz")
    fmt = fmt or str(rng.choice(["counting", "colors", "shadow"]))
    # pick a fresh topic via ledger
    if fmt == "counting":
        cand = [f"count-{o}" for o in OBJECTS]
        obj = ledger.pick_fresh(channel + ":count", cand, rng).split("-", 1)[1]
        state, title, key, tags = build_counting(tl, rng, char, obj)
        ledger_sub = ("count", f"count-{obj}")
    else:
        pool = [o for o in OBJECTS if fmt == "shadow" or o not in ("tree", "apple", "fish")]
        kinds = list(rng.permutation(pool))
        build = build_colors if fmt == "colors" else build_shadow
        state, title, key, tags = build(tl, rng, char, kinds)
        ledger_sub = None
    music = audio.cheerful_loop(tl.duration, rng)
    mix = tl.mix(music, music_gain=0.32)
    scene = Scene(rng)
    confetti = _confetti(rng)
    finale_t = next((s["start"] for s in tl.segments if s["kind"] == "finale"), 1e9)

    def frame(t):
        img, d = scene.draw(t)
        seg = tl.at(t) or tl.segments[0]
        kind = seg["kind"]
        talking = tl.talking(t)
        jump = 0.0
        # title banner for intro
        if kind == "intro":
            p = ease_out_back(clamp01((t - seg["start"]) / 0.6))
            d.rounded_rectangle([90, 250 - 10, 990, 430], radius=50, fill=(255, 255, 255), outline=cinfo["color"], width=10)
            size = fit_size(d, seg["title"], FONT, 110, 820)
            text_block(d, seg["title"], W / 2, 335, FONT, int(size * max(p, 0.2)), fill=shade(cinfo["color"], 0.7),
                       stroke=(255, 255, 255), sw=2, max_w=880)
        if fmt == "counting":
            pos, s = state["pos"]
            shown = seg.get("i", 0)
            for i in range(shown):
                seg_i = next(x for x in tl.segments if x.get("i") == i + 1)
                p = ease_out_back(clamp01((t - seg_i["start"]) / 0.35))
                x, y = pos[i]
                bob = math.sin(t * 3 + i) * 6
                draw_object(d, obj, x, y + bob, s * max(p, 0.01), state["colors"][i])
                if kind == "count" and i + 1 == shown:
                    d.ellipse([x - s * 1.25, y - s * 1.25, x + s * 1.25, y + s * 1.25], outline=(255, 255, 255), width=8)
            if kind in ("count", "finale", "outro") and shown:
                p = ease_out_back(clamp01((t - seg["start"]) / 0.3))
                text_block(d, str(shown), W / 2, 330, FONT, int(220 * max(p, 0.1)), fill=(255, 255, 255),
                           stroke=shade(cinfo["color"], 0.5), sw=14)
                if kind == "count":
                    text_block(d, NUM_WORDS[shown], W / 2, 470, FONT, 80, fill=(255, 240, 120), stroke=(60, 40, 90), sw=7)
            if kind == "count":
                jump = 0.25 * abs(math.sin((t - seg["start"]) * 6)) if t - seg["start"] < 0.5 else 0
        else:
            r = seg.get("r")
            if r is not None:
                obj_k, cname = state["rounds"][r]
                col = PALETTE[cname]
                cx, cy, s = W / 2, 800, 260
                revealed = kind in ("reveal", "finale")
                if fmt == "shadow" and not revealed:
                    lay, xy = silhouette(lambda dd, x, y: draw_object(dd, obj_k, x, y, s, (0, 0, 0, 255)),
                                         cx, cy + math.sin(t * 2) * 8, int(s * 1.3), (45, 45, 70))
                    img.paste(lay, xy, lay)
                else:
                    p = ease_out_back(clamp01((t - seg["start"]) / 0.4)) if kind == "reveal" else 1
                    draw_object(d, obj_k, cx, cy + math.sin(t * 2) * 8, s * (0.85 + 0.15 * p), col)
                if kind in ("ask", "count3"):
                    num = seg.get("num")
                    label = "?" if num is None else str(num)
                    text_block(d, label, W / 2, 330, FONT, 200, fill=(255, 255, 255), stroke=(60, 60, 90), sw=12)
                if revealed:
                    word = cname.upper() if fmt == "colors" else OBJECTS[obj_k][0].upper() + "!"
                    text_block(d, word, W / 2, 330, FONT, 170, fill=col, stroke=(255, 255, 255), sw=14)
                    if kind == "reveal":
                        jump = 0.3 * abs(math.sin((t - seg["start"]) * 5))
        if t >= finale_t:
            _draw_confetti(d, confetti, t - finale_t)
            jump = max(jump, 0.35 * abs(math.sin((t - finale_t) * 5)))
        blob(d, 230, 1270, 150, cinfo["color"], t, talking=talking, jump=jump, extra=cinfo["extra"])
        return img

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"kids-{key}".replace(":", "_")[:80]
    wav = out_dir / f"{stem}.wav"
    audio.write_wav(wav, mix)
    mp4 = render_video(out_dir / f"{stem}.mp4", tl.duration, frame, wav)
    wav.unlink()
    if ledger_sub:
        ledger.add(channel + ":count", ledger_sub[1])
    ledger.add(channel, key, title=title)
    desc = (f"{title}\n\nA gentle learning short for toddlers and preschoolers with {char}, "
            f"an original cartoon friend. Watch together and say the answers out loud!\n\n#shorts #kidslearning #toddlers")
    return {"file": str(mp4), "title": title[:100], "description": desc,
            "tags": tags + ["kids", "preschool", "toddler", "educational", "cartoon", char],
            "made_for_kids": True, "category_id": "27"}
