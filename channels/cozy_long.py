"""Cozy Christmas ambience channel: 1-hour (configurable) instrumental Christmas music videos over a calm,
seamlessly looping animated winter scene, with crackling fire / winter wind underneath.

Format modelled on what performs in this niche: one cozy scene, soft instrumental carols, fireplace sounds,
long duration for relaxing / sleep / focus, formula titles, chapters, and a readable thumbnail.
"""
import math
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from factory import audio
from channels.carol_book import SONGS
from channels.holiday_long import Arrangement, render_audio, vgrad, tree, star_shape, LIGHTS, font

W, H, FPS = 1920, 1080, 24
LOOP = 30.0                      # seconds; every animation is periodic in LOOP so the clip loops seamlessly
TAU = 2 * math.pi
LEADS = {"piano": "Piano", "harp": "Harp", "music_box": "Music Box", "celesta": "Celesta"}


def osc(t, m, ph=0.0):
    """Periodic oscillator with exactly m cycles per loop."""
    return math.sin(TAU * m * t / LOOP + ph)


# ====================================================================== looping snow
class LoopSnow:
    def __init__(self, rng, n=170, region=(0, 0, W, H)):
        x0, y0, x1, y1 = region
        self.region = region
        span = (y1 - y0) + 20
        self.layers = []
        for k, frac, size in ((1, .5, (1.5, 2.8)), (2, .32, (2.8, 4.5)), (3, .18, (4.5, 7))):
            cnt = int(n * frac)
            pts = np.column_stack([rng.uniform(x0, x1, cnt), rng.uniform(0, span, cnt), rng.uniform(*size, cnt),
                                   rng.uniform(0, TAU, cnt), rng.integers(1, 3, cnt)])
            self.layers.append((pts, k * span / LOOP, span))

    def draw(self, d, t):
        x0, y0, x1, y1 = self.region
        for pts, speed, span in self.layers:
            ys = y0 + (pts[:, 1] + t * speed) % span - 10
            xs = pts[:, 0] + np.sin(TAU * pts[:, 4] * t / LOOP + pts[:, 3]) * 22
            for x, y, r in zip(xs, ys, pts[:, 2]):
                if y0 - 10 < y < y1 and x0 <= x <= x1:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))


def _lights_draw(d, lights, t, rmin=7):
    for x, y, ci, ph in lights:
        on = osc(t, 3, ph) > -0.3
        c = LIGHTS[ci] if on else (70, 70, 70)
        d.ellipse([x - rmin, y - rmin, x + rmin, y + rmin], fill=c)


def _fire(d, cx, base, size, t):
    for layer, (col, scale) in enumerate([((255, 110, 30), 1.0), ((255, 170, 40), 0.72), ((255, 235, 140), 0.42)]):
        pts = [(cx - size * scale, base)]
        for k in range(9):
            u = k / 8
            x = cx - size * scale + 2 * size * scale * u
            hgt = (size + size * 0.5 * osc(t, 33 + k * 3 + layer * 5, k * 1.7)) * scale * (1 - abs(u - 0.5) * 1.2)
            pts.append((x, base - max(hgt, 8)))
        pts.append((cx + size * scale, base))
        d.polygon(pts, fill=col)


# ====================================================================== scenes
class FireplaceRoom:
    name, ambience, label, base = "Fireplace", "fire", "Cozy Christmas Fireplace", "Christmas by the Fireplace"

    def __init__(self, rng):
        walls = [((92, 30, 30), (52, 16, 18)), ((30, 52, 44), (16, 30, 26)), ((48, 38, 70), (26, 20, 40))]
        top, bot = walls[int(rng.integers(0, len(walls)))]
        self.bg = vgrad(top, bot)
        d = ImageDraw.Draw(self.bg)
        for x in range(0, W, 60):
            d.line([x, 0, x, 760], fill=tuple(min(255, int(c * 1.12)) for c in top), width=2)
        d.rectangle([0, 760, W, 820], fill=(70, 42, 28))
        d.rectangle([0, 820, W, H], fill=(58, 34, 22))
        for x in range(0, W + 200, 160):
            d.line([x, 820, x - 80, H], fill=(48, 28, 18), width=3)
        d.ellipse([480, 930, 1440, 1120], fill=(120, 30, 34))
        self.win = (120, 180, 500, 640)
        x0, y0, x1, y1 = self.win
        d.rectangle([x0 - 18, y0 - 18, x1 + 18, y1 + 18], fill=(230, 225, 210))
        self.bg.paste(vgrad((10, 18, 50), (40, 60, 110), x1 - x0, y1 - y0), (x0, y0))
        d.ellipse([x1 - 120, y0 + 40, x1 - 50, y0 + 110], fill=(255, 250, 225))
        d.polygon([(x0, y1 - 60), (x0 + 150, y1 - 95), (x1, y1 - 50), (x1, y1), (x0, y1)], fill=(225, 235, 250))
        fx0, fx1, fy0, fy1 = 720, 1200, 380, 820
        d.rectangle([fx0 - 60, fy0 - 40, fx1 + 60, fy0], fill=(110, 70, 45))
        d.rectangle([fx0, fy0, fx1, fy1], fill=(140, 60, 45))
        for yy in range(fy0, fy1, 32):
            off = 0 if (yy // 32) % 2 else 32
            for xx in range(fx0 + off, fx1, 64):
                d.rectangle([xx, yy, xx + 60, yy + 28], outline=(110, 45, 35), width=2)
        self.hearth = (fx0 + 90, fy0 + 150, fx1 - 90, fy1)
        hx0, hy0, hx1, hy1 = self.hearth
        d.rounded_rectangle([hx0, hy0, hx1, hy1 + 20], radius=60, fill=(25, 12, 10))
        d.rectangle([hx0 + 40, hy1 - 40, hx1 - 40, hy1 - 20], fill=(80, 45, 25))
        for i, c in enumerate([(200, 40, 50), (40, 120, 70), (220, 200, 200)]):
            sx = fx0 + 40 + i * 150
            d.rectangle([sx, fy0, sx + 50, fy0 + 70], fill=c)
            d.polygon([(sx, fy0 + 70), (sx + 50, fy0 + 70), (sx + 80, fy0 + 110), (sx + 30, fy0 + 110)], fill=c)
            d.rectangle([sx - 4, fy0, sx + 54, fy0 + 16], fill=(250, 250, 250))
        for x in range(fx0 - 60, fx1 + 60, 26):
            d.ellipse([x - 16, fy0 - 52, x + 16, fy0 - 26], fill=(30, 100, 55))
        # candles on mantel
        self.candles = [(fx0 - 30, fy0 - 40), (fx1 + 30, fy0 - 40)]
        for cx, cy in self.candles:
            d.rectangle([cx - 10, cy - 60, cx + 10, cy], fill=(245, 235, 210))
        self.lights = []
        self.tree_x = 1600
        self.tree_top = tree(d, self.tree_x, 950, 680, rng, self.lights)
        for gx in (-180, -60, 70, 170):
            c = [(200, 50, 60), (50, 110, 200), (230, 180, 50), (160, 80, 180)][int(rng.integers(0, 4))]
            d.rectangle([self.tree_x + gx - 45, 900, self.tree_x + gx + 45, 970], fill=c, outline=(255, 240, 200), width=3)
            d.line([self.tree_x + gx, 900, self.tree_x + gx, 970], fill=(255, 240, 200), width=8)
        self.snow = LoopSnow(rng, n=70, region=self.win)
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse([hx0 - 300, hy0 - 160, hx1 + 300, hy1 + 280], fill=80)
        self.glow = glow.filter(ImageFilter.GaussianBlur(100))

    def frame(self, t):
        img = self.bg.copy()
        flick = 0.85 + 0.15 * osc(t, 41) * osc(t, 13, 1)
        img.paste(Image.new("RGB", (W, H), (255, 150, 60)), (0, 0), self.glow.point(lambda v: int(v * flick)))
        d = ImageDraw.Draw(img)
        self.snow.draw(d, t)
        x0, y0, x1, y1 = self.win
        d.line([(x0 + x1) / 2, y0, (x0 + x1) / 2, y1], fill=(230, 225, 210), width=12)
        d.line([x0, (y0 + y1) / 2, x1, (y0 + y1) / 2], fill=(230, 225, 210), width=12)
        hx0, hy0, hx1, hy1 = self.hearth
        _fire(d, (hx0 + hx1) / 2, hy1 - 40, 150, t)
        for cx, cy in self.candles:
            fl = 4 * osc(t, 37, cx)
            d.ellipse([cx - 9, cy - 95 + fl, cx + 9, cy - 62], fill=(255, 210, 90))
        _lights_draw(d, self.lights, t, 8)
        d.polygon(star_shape(self.tree_x, self.tree_top + 12, 40, 0), fill=(255, 225, 90))
        return img


class LakeCabin:
    name, ambience, label, base = "Cabin by the Lake", "fire_out", "Cozy Christmas Cabin", "Christmas Cabin by the Lake"

    def __init__(self, rng):
        skies = [((6, 12, 38), (40, 62, 120)), ((14, 10, 40), (80, 58, 120)), ((4, 22, 44), (26, 88, 118))]
        top, bot = skies[int(rng.integers(0, len(skies)))]
        self.bg = vgrad(top, bot)
        d = ImageDraw.Draw(self.bg)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, 430), rng.uniform(1, 2.8), rng.uniform(0, TAU), int(rng.integers(1, 4))) for _ in range(170)]
        mx, my = rng.uniform(300, 700), rng.uniform(130, 220)
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse([mx - 170, my - 170, mx + 170, my + 170], fill=90)
        self.bg.paste(Image.new("RGB", (W, H), (255, 250, 225)), (0, 0), glow.filter(ImageFilter.GaussianBlur(55)))
        d = ImageDraw.Draw(self.bg)
        d.ellipse([mx - 70, my - 70, mx + 70, my + 70], fill=(255, 250, 228))
        # mountains
        ph = rng.uniform(0, 6)
        for col, base, amp in (((62, 82, 132), 560, 190), ((96, 116, 164), 610, 120)):
            pts = [(x, base - amp * (0.55 + 0.45 * math.sin(x * 0.0029 + ph + base))) for x in range(0, W + 20, 20)]
            d.polygon(pts + [(W, 700), (0, 700)], fill=col)
            hi = [(x, y + 4) for x, y in pts]
            d.line(hi, fill=tuple(min(255, c + 60) for c in col), width=6)
        # frozen lake with moon reflection
        d.rectangle([0, 640, W, 880], fill=(112, 138, 184))
        for k in range(6):
            yy = 660 + k * 34
            d.ellipse([mx - 70 + k * 6, yy, mx + 70 - k * 6, yy + 12], fill=(205, 210, 228))
        # far-shore pines
        for _ in range(60):
            x = rng.uniform(0, W)
            hgt = rng.uniform(50, 110)
            base = rng.uniform(640, 660)
            d.polygon([(x - hgt * 0.28, base), (x + hgt * 0.28, base), (x, base - hgt)], fill=(24, 58, 48))
        # near snowy bank
        bank = [(x, 880 - 25 * math.sin(x * 0.004 + ph)) for x in range(0, W + 20, 20)]
        d.polygon(bank + [(W, H), (0, H)], fill=(236, 242, 252))
        # big foreground pines at the edges
        for x, hgt in ((90, 520), (260, 380), (1880, 470)):
            base = H + 20
            for i in range(5):
                w = hgt * (0.3 - 0.05 * i)
                yb = base - hgt * 0.19 * i
                d.polygon([(x - w, yb), (x + w, yb), (x, yb - hgt * 0.36)], fill=(18, 52, 40))
                d.polygon([(x - w * 0.55, yb - hgt * 0.1), (x + w * 0.55, yb - hgt * 0.1), (x, yb - hgt * 0.36)], fill=(228, 236, 250))
        self.sky_mid = tuple(int((a + b) / 2) for a, b in zip(top, bot))
        # cabin
        cx0, cy1 = 1120, 930
        d.rectangle([cx0, cy1 - 230, cx0 + 420, cy1], fill=(110, 62, 38), outline=(60, 34, 20), width=4)
        for yy in range(cy1 - 225, cy1, 24):
            d.line([cx0, yy, cx0 + 420, yy], fill=(85, 46, 28), width=3)
        d.polygon([(cx0 - 40, cy1 - 225), (cx0 + 460, cy1 - 225), (cx0 + 210, cy1 - 390)], fill=(240, 245, 255), outline=(170, 180, 205))
        d.rectangle([cx0 + 300, cy1 - 380, cx0 + 345, cy1 - 290], fill=(90, 60, 50))
        self.chimney = (cx0 + 322, cy1 - 385)
        self.windows = [(cx0 + 40, cy1 - 170, 110, 90), (cx0 + 270, cy1 - 170, 110, 90)]
        d.rectangle([cx0 + 175, cy1 - 150, cx0 + 245, cy1], fill=(70, 40, 25))
        wglow = Image.new("L", (W, H), 0)
        gd = ImageDraw.Draw(wglow)
        for wx, wy, ww, wh in self.windows:
            gd.rectangle([wx - 30, wy - 30, wx + ww + 30, wy + wh + 60], fill=110)
        self.wglow = wglow.filter(ImageFilter.GaussianBlur(40))
        self.lights = []
        self.tree_x = 1760
        self.tree_x = 1680
        self.tree_top = tree(d, self.tree_x, 950, 330, rng, self.lights)
        self.snow = LoopSnow(rng, n=190)

    def frame(self, t):
        img = self.bg.copy()
        flick = 0.85 + 0.15 * osc(t, 29) * osc(t, 11, 2)
        img.paste(Image.new("RGB", (W, H), (255, 170, 80)), (0, 0), self.wglow.point(lambda v: int(v * flick)))
        d = ImageDraw.Draw(img)
        for x, y, r, ph, m in self.stars:
            a = 0.55 + 0.45 * osc(t, m * 4, ph)
            c = int(150 + 105 * a)
            rr = r * (0.7 + 0.5 * a)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(c, c, int(c * 0.92)))
        for wx, wy, ww, wh in self.windows:
            g = int(195 + 35 * osc(t, 17, wx))
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=(255, g, 120))
            d.line([wx + ww / 2, wy, wx + ww / 2, wy + wh], fill=(90, 50, 30), width=5)
            d.line([wx, wy + wh / 2, wx + ww, wy + wh / 2], fill=(90, 50, 30), width=5)
        sx, sy = self.chimney
        for k in range(7):     # smoke puffs drifting up, periodic
            u = ((t / LOOP) * 2 + k / 7) % 1.0
            r = 18 + 50 * u
            px = sx + 70 * u + 10 * osc(t, 2, k)
            py = sy - 260 * u
            a = 0.45 * (1 - u)
            col = tuple(int(sc * (1 - a) + 215 * a) for sc in self.sky_mid)
            d.ellipse([px - r, py - r, px + r, py + r], fill=col)
        _lights_draw(d, self.lights, t, 6)
        d.polygon(star_shape(self.tree_x, self.tree_top + 8, 22, 0), fill=(255, 225, 90))
        self.snow.draw(d, t)
        return img


class SnowyVillage:
    name, ambience, label, base = "Snowy Village", "wind", "Snowy Christmas Village", "Snowy Christmas Village Night"

    def __init__(self, rng):
        from channels.holiday_long import Village
        self.v = Village(rng)
        self.v.snow = None
        self.snow = LoopSnow(rng, n=220)
        self.stars = [(x, y, r, ph, int(rng.integers(1, 4))) for x, y, r, ph in self.v.stars]

    def frame(self, t):
        v = self.v
        img = v.bg.copy()
        d = ImageDraw.Draw(img)
        for x, y, r, ph, m in self.stars:
            a = 0.55 + 0.45 * osc(t, m * 4, ph)
            c = int(150 + 105 * a)
            rr = r * (0.7 + 0.5 * a)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(c, c, int(c * 0.92)))
        for wx, wy, ww, wh, ph in v.windows:
            g = int(185 + 40 * osc(t, 11, ph))
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=(255, g, 110))
        _lights_draw(d, v.lights, t, 7)
        d.polygon(star_shape(v.tree_x, v.tree_top + 10, 34, 0), fill=(255, 225, 90))
        self.snow.draw(d, t)
        return img


SCENES = {"fireplace": FireplaceRoom, "cabin": LakeCabin, "village": SnowyVillage}


# ====================================================================== ambience sounds
def _movavg(x, k):
    c = np.cumsum(np.concatenate([[0.0], x.astype(np.float64)]))
    y = (c[k:] - c[:-k]) / k
    pad = len(x) - len(y)
    return np.concatenate([np.full(pad // 2, y[0]), y, np.full(pad - pad // 2, y[-1])]).astype(np.float32)


def ambience(kind, seconds, rng):
    n = int(seconds * audio.SR)
    out = np.zeros(n, dtype=np.float32)
    if kind in ("fire", "fire_out"):
        rumble = np.cumsum(rng.standard_normal(n).astype(np.float32))
        rumble -= _movavg(rumble, 4000)
        out += rumble / (np.abs(rumble).max() + 1e-9) * 0.25
        pops = int(seconds * (3.5 if kind == "fire" else 1.5))
        for _ in range(pops):
            st = int(rng.uniform(0, seconds) * audio.SR)
            L = int(rng.uniform(0.004, 0.03) * audio.SR)
            burst = rng.standard_normal(L).astype(np.float32) * np.exp(-np.arange(L) / (L / 4)).astype(np.float32)
            out[st:st + L] += burst[: n - st] * rng.uniform(0.15, 0.6)
    if kind in ("wind", "fire_out"):
        w = rng.standard_normal(n).astype(np.float32)
        for _ in range(3):
            w = _movavg(w, 60)
        tt = np.arange(n) / audio.SR
        env = 0.6 + 0.4 * np.sin(TAU * tt / 17.0 + rng.uniform(0, 6)) * np.sin(TAU * tt / 7.3)
        out += w / (np.abs(w).max() + 1e-9) * env.astype(np.float32) * 0.5
    return out / (np.abs(out).max() + 1e-9)


# ====================================================================== playlist audio
def cozy_song(key):
    """Instrumental, gentler version of a carol: no lyrics, ~18% slower."""
    s = dict(SONGS[key])
    s["bpm"] = int(s["bpm"] * 0.82)
    s["feel"] = "hymn"
    s["form"] = [(p, None) for p, _ in s["form"]]
    return s


def build_playlist_audio(wav_path, minutes, rng, scene_ambience):
    keys = list(SONGS)
    order, chapters, t = [], [], 0.0
    target = minutes * 60
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(audio.SR)

        def write(x):
            x = np.clip(x, -1, 1)
            d16 = (x * 32767).astype(np.int16)
            wf.writeframes(np.repeat(d16[:, None], 2, axis=1).tobytes())

        last = None
        while t < target - 30:
            choices = [k for k in keys if k != last]
            key = str(rng.choice(choices))
            last = key
            lead = str(rng.choice(list(LEADS)))
            song = cozy_song(key)
            transpose = song.get("transpose", 0) + int(rng.integers(-2, 2))
            arr = Arrangement(song, rng, lead, transpose)
            mix, dur = render_audio(arr, rng, lead, transpose, "hymn", inst_as_lead=True)
            mix = mix.astype(np.float32) * 0.62
            amb = ambience(scene_ambience, len(mix) / audio.SR, rng)
            write(mix + amb[: len(mix)] * 0.07)
            chapters.append((t, SONGS[key]["title"], LEADS[lead]))
            order.append(key)
            t += len(mix) / audio.SR
            gap = 3.0
            write(ambience(scene_ambience, gap, rng) * 0.07)
            t += gap
    return t, chapters


# ====================================================================== thumbnail
def thumbnail(scene, path, line1, line2):
    img = scene.frame(LOOP * 0.37).resize((1280, 720), Image.LANCZOS)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for k in range(250):
        od.line([0, 470 + k, 1280, 470 + k], fill=(6, 8, 26, int(215 * min(1, k / 90))))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)
    d.text((640, 545), line1, font=font("Cardo-Bold.ttf", 84), fill=(255, 226, 150), anchor="mm",
           stroke_width=5, stroke_fill=(40, 20, 10))
    size = 50
    while size > 28 and d.textlength(line2, font=font("CrimsonText-Bold.ttf", size)) > 1200:
        size -= 2
    d.text((640, 640), line2, font=font("CrimsonText-Bold.ttf", size), fill=(255, 255, 255), anchor="mm",
           stroke_width=3, stroke_fill=(20, 20, 40))
    img.save(path, quality=92)


# ====================================================================== main
def make(out_dir: Path, rng, ledger, channel="cozy", minutes=60, scene=None, **_):
    scene = scene or _.get("song_key") or ledger.pick_fresh(channel + ":scene", list(SCENES), rng)
    sc = SCENES[scene](rng)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(out_dir.glob("cozy-*.mp4")))
    stem = f"cozy-{scene}-{minutes}min-{n + 1}"
    wav = out_dir / f"{stem}.wav"
    total, chapters = build_playlist_audio(wav, minutes, rng, sc.ambience)
    # seamless loop clip
    loop_mp4 = out_dir / f"{stem}-loop.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "31", "-pix_fmt", "yuv420p",
           "-g", str(int(LOOP * FPS)), "-movflags", "+faststart", str(loop_mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(LOOP * FPS)):
        p.stdin.write(sc.frame(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg loop render failed")
    mp4 = out_dir / f"{stem}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(loop_mp4), "-i", str(wav),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-t", f"{total:.2f}",
                    "-movflags", "+faststart", str(mp4)], check=True)
    loop_mp4.unlink()
    wav.unlink()
    # ------------- metadata
    mood = str(rng.choice(["Cozy", "Peaceful", "Soothing", "Warm", "Relaxing"]))
    inst = "Christmas Piano" if sum(1 for c in chapters if c[2] == "Piano") >= len(chapters) / 3 else "Instrumental Christmas Music"
    sound = {"fire": "Crackling Fireplace", "fire_out": "Crackling Fire & Snowfall", "wind": "Gentle Winter Wind"}[sc.ambience]
    use = str(rng.choice(["Sleep & Relaxation", "Relaxing, Study & Sleep", "Deep Focus & Calm", "a Peaceful Christmas Eve"]))
    hours = f"{minutes // 60} Hour" if minutes % 60 == 0 else f"{minutes} Minutes"
    title = f"{mood} {sc.base} ❄ Soft {inst} & {sound} | {hours} for {use}"
    if len(title) > 100:
        title = f"{mood} {sc.base} ❄ {inst} & {sound} | {hours}"
    thumb = out_dir / f"{stem}.jpg"
    thumbnail(sc, thumb, sc.label, f"Soft {inst.replace('Instrumental ', '')}  •  {sound}  •  {hours}")
    lines = []
    for st, name, lead in chapters:
        h, rem = divmod(int(st), 3600)
        m, s = divmod(rem, 60)
        lines.append((f"{h}:{m:02d}:{s:02d}" if total >= 3600 else f"{m}:{s:02d}") + f" {name} ({lead})")
    desc = (f"{title}\n\nSettle in by the {sc.name.lower()} with {hours.lower()} of gentle, instrumental Christmas carols "
            f"and soft {sound.lower()}. Perfect for relaxing, reading, studying, falling asleep or a calm Christmas evening.\n\n"
            "TRACKLIST\n" + "\n".join(lines) +
            "\n\nAll carols are public-domain melodies, newly arranged for this channel. Animation and music are original.\n\n"
            "#christmasmusic #relaxingchristmasmusic #christmasambience #cozy #christmaspiano #fireplace")
    ledger.add(channel, stem, title=title)
    return {"file": str(mp4), "thumbnail": str(thumb), "title": title, "description": desc[:4900], "duration": total,
            "tags": ["christmas music", "relaxing christmas music", "christmas ambience", "cozy christmas", "christmas piano",
                     "instrumental christmas music", "fireplace", "christmas fireplace", "winter ambience",
                     "sleep music", "christmas carols instrumental", sc.name.lower()],
            "category_id": "10", "made_for_kids": False}
