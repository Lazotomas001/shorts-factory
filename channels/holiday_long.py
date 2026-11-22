"""Long-form Christmas channel: full carols (every verse) as 16:9 sing-along videos, plus compilations.

Each render picks a song, a lead instrument, a key, a scene (snowy village / cozy fireplace) and a palette,
arranges melody + real hymn harmony (or chord accompaniment), and renders karaoke-style lyrics.
"""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from factory import audio
from factory.audio import Mix, CHORDS, midi as note_midi
from factory.lily import parse
from channels.carol_book import SONGS

W, H, FPS = 1920, 1080, 24
SERIF, SERIF2 = "CrimsonText-Bold.ttf", "Cardo-Bold.ttf"
LEADS = {"piano": "Piano", "music_box": "Music Box", "celesta": "Celesta", "harp": "Harp", "bell": "Bells"}
LIGHTS = [(255, 80, 80), (255, 210, 80), (110, 200, 255), (130, 255, 150), (255, 150, 230), (255, 240, 200)]


def font(name, size):
    from factory.render import font as f
    return f(name, size)


# ====================================================================== lyrics fitting
def tokenize(line):
    """'Si-lent night _ one=horse' -> [(text, word_end, hard_hyphen)] with '_' = melisma marker."""
    out = []
    for word in line.split():
        if word == "_":
            out.append(("_", True, False))
            continue
        parts, buf = [], ""
        for ch in word:
            if ch in "-=":
                parts.append((buf, ch == "="))
                buf = ""
            else:
                buf += ch
        if buf or not parts:
            parts.append((buf, False))
        trailing = word[-1] in "-="           # "an-" : word continues after a melisma marker
        for i, (p, hard) in enumerate(parts):
            if i == len(parts) - 1 and trailing:
                out.append((p + ("-" if hard else ""), False, hard))
                continue
            out.append((p + ("-" if hard else ""), i == len(parts) - 1, hard))
    return out


def fit_line(notes, line):
    """Assign syllables to notes. Returns (notes, syll) where syll[i] = index into tokens or None (melisma)."""
    toks = tokenize(line)
    notes = [list(n) for n in notes]  # [midi, beats]
    while len(toks) > len(notes):     # more syllables than notes: split the longest note
        i = max(range(len(notes)), key=lambda k: (notes[k][1], k))
        m, b = notes[i]
        notes[i:i + 1] = [[m, b / 2], [m, b / 2]]
    syll = []
    ti = 0
    for k in range(len(notes)):
        if ti < len(toks):
            if toks[ti][0] == "_":
                syll.append(None)
            else:
                syll.append(ti)
            ti += 1
        else:
            syll.append(None)       # extra notes extend the last syllable
    words = [(t, end) for t, end, _ in toks if t != "_"]
    return notes, syll, toks


# ====================================================================== arrangement
def _parse_part(part, transpose):
    rel = part.get("relative")
    mel = [(n.midi + transpose if n.midi is not None else None, n.beats) for n in parse(part["melody"], rel)]
    harm = []
    if "satb" in part:
        rels = part["satb"].get("relative", {})
        for v in ("alto", "tenor", "bass"):
            harm.append((v, [(n.midi + transpose if n.midi is not None else None, n.beats)
                             for n in parse(part["satb"][v], rels.get(v))]))
    return mel, harm


def chord_notes(name, transpose):
    if name == "N":
        return None
    root, rest = name[0], name[1:]
    acc = 0
    if rest[:1] in ("#", "b"):
        acc = 1 if rest[0] == "#" else -1
        rest = rest[1:]
    q = "m" if rest.startswith("m") else ("7" if "7" in rest else "")
    r = note_midi(root + "3") + acc + transpose
    return r, [r + 12 + i for i in CHORDS[q]]


class Arrangement:
    def __init__(self, song, rng, lead, transpose):
        self.song, self.rng, self.lead = song, rng, lead
        self.spb = 60.0 / song["bpm"]
        self.meter = song.get("meter", 4)
        self.events = []      # (beat, midi, beats, voice)
        self.chords = []      # (beat, beats, name)
        self.lines = []       # dict(start_beat, end_beat, pieces=[(text, beat, word_end)], label, instrumental)
        self.sections = []    # (start_beat, label)
        parts = {k: _parse_part(p, transpose) for k, p in song["parts"].items()}
        b = 0.0
        # intro: last line of the first part, instrumental
        first = song["form"][0][0]
        mel, harm = parts[first]
        counts = song["parts"][first]["lines"]
        start_idx = sum(counts[:-1])
        intro_mel = [n for n in mel if n[0] is not None][start_idx:]
        intro_len = sum(n[1] for n in intro_mel)
        self.sections.append((0.0, "Intro"))
        self._add_melody(intro_mel, 0.0, "lead_soft")
        tot = sum(n[1] for n in mel)
        offset = tot - intro_len
        for v, notes in harm:
            self._add_voice(notes, 0.0 - offset, v, window=(offset, tot))
        if "chords" in song["parts"][first]:
            self._add_chords(song["parts"][first]["chords"], -offset, window=(offset, tot))
        b = intro_len + (self.meter - intro_len % self.meter) % self.meter
        verse_no = 0
        for part_name, verse_key in song["form"]:
            mel, harm = parts[part_name]
            part = song["parts"][part_name]
            label = "Instrumental" if verse_key is None else (
                "Chorus" if part_name == "chorus" else f"Verse {verse_no + 1}")
            if verse_key is not None and part_name != "chorus":
                verse_no += 1
                label = f"Verse {verse_no}"
            self.sections.append((b, label))
            notes = [n for n in mel if n[0] is not None]
            lyr = song["verses"][verse_key] if verse_key is not None else None
            cursor_note, beat = 0, b
            # rests inside melody: keep timing by walking the raw melody
            raw_iter = iter(mel)
            line_notes_all = []
            for count in part["lines"]:
                ln = []
                while len(ln) < count:
                    m, d = next(raw_iter)
                    if m is None:
                        beat += d
                        continue
                    ln.append((m, d, beat))
                    beat += d
                line_notes_all.append(ln)
            for li, ln in enumerate(line_notes_all):
                if lyr:
                    fitted, syll, toks = fit_line([(m, d) for m, d, _ in ln], lyr[li])
                    # rebuild start beats after any splits
                    nb, beats = ln[0][2], []
                    for m, d in fitted:
                        beats.append(nb)
                        nb += d
                    pieces = []
                    for k, (m, d) in enumerate(fitted):
                        self.events.append((beats[k], m, d, "lead"))
                        if syll[k] is not None:
                            t, end, _ = toks[syll[k]]
                            pieces.append((t, beats[k], end))
                    self.lines.append(dict(start=ln[0][2], end=ln[-1][2] + ln[-1][1], pieces=pieces, label=label))
                else:
                    for m, d, bt in ln:
                        self.events.append((bt, m, d, "lead_inst"))
                    if li == 0:
                        self.lines.append(dict(start=ln[0][2], end=line_notes_all[-1][-1][2] + line_notes_all[-1][-1][1],
                                               pieces=[], label=label, instrumental=True))
            for v, hn in harm:
                self._add_voice(hn, b, v)
            if "chords" in part:
                self._add_chords(part["chords"], b)
            b = beat
        self.end_beat = b
        # final ritardando over the last line
        self.rit_start = self.lines[-1]["start"] if self.lines else b - 4

    def _add_melody(self, notes, b0, voice):
        b = b0
        for m, d in notes:
            self.events.append((b, m, d, voice))
            b += d

    def _add_voice(self, notes, b0, voice, window=None):
        b = b0
        for m, d in notes:
            if m is not None and (window is None or b - b0 >= window[0] - 1e-6):
                self.events.append((b, m, d, voice))
            b += d

    def _add_chords(self, chords, b0, window=None):
        b = b0
        for d, name in chords:
            if window is None or b - b0 >= window[0] - 1e-6:
                self.chords.append((max(b, 0.0), d, name))
            b += d

    # beat -> seconds with a gentle final ritardando
    def t(self, beat):
        s, r0, r1 = self.spb, self.rit_start, self.end_beat
        if beat <= r0:
            return 1.0 + beat * s
        span = max(r1 - r0, 1e-6)
        x = min(beat, r1) - r0
        extra = 0.35 * s * x * x / (2 * span)
        tail = max(beat - r1, 0) * s * 1.35
        return 1.0 + r0 * s + x * s + extra + tail


def render_audio(arr, rng, lead_name, transpose, feel, inst_as_lead=False):
    lead = audio.INSTRUMENTS[lead_name]
    inst_lead = audio.INSTRUMENTS["celesta" if lead_name != "celesta" else "music_box"]
    total = arr.t(arr.end_beat) + 5.0
    mix = Mix(total)
    oct_up = 12 if lead_name in ("music_box", "celesta", "bell") else 0
    for b, m, d, voice in arr.events:
        t0, t1 = arr.t(b), arr.t(b + d)
        dur = max(t1 - t0, 0.08)
        if inst_as_lead and voice == "lead_inst":
            voice = "lead"
        if voice in ("lead", "lead_soft"):
            mix.note(lead, m + oct_up, t0, dur * 0.97, 0.42 if voice == "lead" else 0.3)
        elif voice == "lead_inst":
            mix.note(inst_lead, m + 12, t0, dur * 0.97, 0.34)
            mix.note(audio.strings, m, t0, dur, 0.06)
        elif voice in ("alto", "tenor"):
            mix.note(audio.strings, m, t0, dur, 0.085)
        elif voice == "bass":
            mix.note(audio.cello, m, t0, dur * 0.95, 0.2)
    for b, d, name in arr.chords:
        ch = chord_notes(name, transpose)
        if not ch:
            continue
        root, tones = ch
        t0, t1 = arr.t(b), arr.t(b + d)
        for m in tones[:3]:
            mix.note(audio.strings, m, t0, t1 - t0, 0.05)
        mix.note(audio.cello, root, t0, (t1 - t0) * 0.9, 0.22)
        # light arpeggio on each beat for movement
        for k in range(int(d)):
            m = tones[k % len(tones)] + 12
            mix.note(audio.harp, m, arr.t(b + k), arr.spb * 0.9, 0.07)
    # percussion / sparkle
    nbeats = int(arr.end_beat) + 1
    for k in range(nbeats):
        tb = arr.t(k)
        if feel == "bells":
            mix.add(audio.sleigh_bells(0.22, rng), tb, 0.12 if k % 2 else 0.17)
        elif k % arr.meter == 0:
            mix.add(audio.bell(audio.hz(84 + transpose), 0.4), tb, 0.018)
    # final chord bloom
    last = arr.lines[-1]["end"] if arr.lines else arr.end_beat
    tf = arr.t(arr.end_beat)
    final_notes = [e for e in arr.events if abs(e[0] + e[2] - arr.end_beat) < 1e-3 and e[3] in ("lead", "lead_inst")]
    if final_notes:
        m = final_notes[-1][1]
        for iv in (0, 7, 12, 16):
            mix.note(audio.bell, m - 12 + iv, tf, 2.5, 0.05)
    out = audio.reverb(mix.buf, 2.6, 0.32)[: int(total * audio.SR)]
    fade = int(3.0 * audio.SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return audio.normalize(out, 0.9), total


# ====================================================================== scenes
def vgrad(c1, c2, w=W, h=H):
    a = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8), "RGB")


class Snow:
    def __init__(self, rng, n=260):
        self.layers = []
        for depth, count, size, speed in ((0.4, int(n * .5), (1.5, 3), 25), (0.7, int(n * .32), (3, 5), 45), (1.0, int(n * .18), (5, 8), 75)):
            self.layers.append((np.column_stack([rng.uniform(0, W, count), rng.uniform(0, H, count),
                                                 rng.uniform(*size, count), rng.uniform(0, 6, count)]), speed))

    def draw(self, d, t, y_max=H):
        for pts, speed in self.layers:
            ys = (pts[:, 1] + t * speed) % (H + 20) - 10
            xs = (pts[:, 0] + np.sin(t * 0.6 + pts[:, 3]) * 30 + t * speed * 0.15) % W
            for x, y, r in zip(xs, ys, pts[:, 2]):
                if y < y_max:
                    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))


def tree(d, cx, base, h, rng, lights):
    d.rectangle([cx - h * 0.05, base - h * 0.08, cx + h * 0.05, base], fill=(90, 55, 30))
    tiers = 4
    for i in range(tiers):
        top = base - h * (0.25 + 0.75 * (i + 1) / tiers)
        bot = base - h * (0.08 + 0.62 * i / tiers)
        w = h * (0.42 - 0.08 * i)
        d.polygon([(cx - w, bot), (cx + w, bot), (cx, top)], fill=(26, 105 - 4 * i, 58), outline=(18, 70, 40))
        for k in range(9 - i):
            u = rng.uniform(0.1, 0.9)
            y = top + (bot - top) * rng.uniform(0.35, 0.95)
            half = w * (y - top) / (bot - top)
            lights.append((cx - half + 2 * half * u, y, int(rng.integers(0, 6)), rng.uniform(0, 6)))
    return base - h


def star_shape(cx, cy, r, rot=0):
    pts = []
    for i in range(10):
        rr = r if i % 2 == 0 else r * 0.45
        a = math.radians(-90 + i * 36 + rot)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


class Village:
    name = "Snowy Village"

    def __init__(self, rng):
        skies = [((8, 14, 45), (48, 70, 130)), ((18, 12, 48), (92, 62, 132)), ((4, 28, 50), (30, 100, 128))]
        top, bot = skies[int(rng.integers(0, len(skies)))]
        self.bg = vgrad(top, bot)
        d = ImageDraw.Draw(self.bg)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, 520), rng.uniform(1, 3.2), rng.uniform(0, 6)) for _ in range(180)]
        self.moon = (rng.uniform(1250, 1700), rng.uniform(150, 260))
        mx, my = self.moon
        glow = Image.new("L", (W, H), 0)
        ImageDraw.Draw(glow).ellipse([mx - 190, my - 190, mx + 190, my + 190], fill=90)
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        self.bg.paste(Image.new("RGB", (W, H), (255, 250, 225)), (0, 0), glow)
        d = ImageDraw.Draw(self.bg)
        d.ellipse([mx - 85, my - 85, mx + 85, my + 85], fill=(255, 250, 228))
        ph = rng.uniform(0, 6)
        for col, base, amp, fq in (((150, 170, 205), 590, 50, 0.004), ((200, 215, 240), 660, 35, 0.006)):
            pts = [(x, base + amp * math.sin(x * fq + ph)) for x in range(0, W + 20, 20)]
            d.polygon(pts + [(W, H), (0, H)], fill=col)
        # village
        self.windows = []
        x = 60
        while x < W - 120:
            hw, hh = rng.uniform(130, 210), rng.uniform(130, 200)
            base = 735 + rng.uniform(-12, 12)
            col = [(120, 60, 50), (70, 80, 110), (110, 90, 60), (80, 50, 70), (60, 90, 80)][int(rng.integers(0, 5))]
            d.rectangle([x, base - hh, x + hw, base], fill=col, outline=(30, 25, 35), width=3)
            d.polygon([(x - 18, base - hh + 4), (x + hw + 18, base - hh + 4), (x + hw / 2, base - hh - hw * 0.55)],
                      fill=(240, 245, 255), outline=(170, 180, 205))
            for wy in (base - hh * 0.72, base - hh * 0.38):
                for wx in (x + hw * 0.18, x + hw * 0.6):
                    self.windows.append((wx, wy, hw * 0.22, hh * 0.2, rng.uniform(0, 6)))
            x += hw + rng.uniform(30, 120)
        d.polygon([(0, 745), (W, 735), (W, H), (0, H)], fill=(236, 242, 252))
        self.lights = []
        self.tree_top = tree(d, 1500 if mx < 1450 else 420, 800, 500, rng, self.lights)
        self.tree_x = 1500 if mx < 1450 else 420
        for gx in (-120, -40, 60, 130):
            c = [(200, 50, 60), (50, 110, 200), (230, 180, 50), (70, 160, 90)][int(rng.integers(0, 4))]
            d.rectangle([self.tree_x + gx - 30, 762, self.tree_x + gx + 30, 810], fill=c, outline=(255, 255, 255), width=3)
            d.line([self.tree_x + gx, 762, self.tree_x + gx, 810], fill=(255, 255, 255), width=6)
        self.snow = Snow(rng)
        self.sleigh_t = rng.uniform(15, 40)

    def frame(self, t, pulse):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        for x, y, r, ph in self.stars:
            a = 0.55 + 0.45 * math.sin(t * 1.7 + ph)
            c = int(150 + 105 * a)
            rr = r * (0.7 + 0.5 * a)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(c, c, int(c * 0.92)))
        for wx, wy, ww, wh, ph in self.windows:
            g = int(185 + 40 * math.sin(t * 2.3 + ph))
            d.rectangle([wx, wy, wx + ww, wy + wh], fill=(255, g, 110))
        # sleigh silhouette across the moon every ~45 s
        st = (t - self.sleigh_t) % 45
        if st < 9:
            mx, my = self.moon
            sx = -200 + st / 9 * (W + 400)
            sy = my + 40 - 60 * math.sin(st / 9 * math.pi)
            sil = (25, 30, 55)
            for k in range(4):
                rx = sx + 95 + k * 55
                d.ellipse([rx - 22, sy - 10, rx + 22, sy + 8], fill=sil)
                d.line([rx + 18, sy - 6, rx + 30, sy - 26], fill=sil, width=5)
                d.line([rx - 12, sy + 6, rx - 18, sy + 24], fill=sil, width=4)
                d.line([rx + 12, sy + 6, rx + 18, sy + 24], fill=sil, width=4)
            d.polygon([(sx - 60, sy - 5), (sx + 40, sy - 5), (sx + 55, sy - 30), (sx + 60, sy + 15), (sx - 60, sy + 15)], fill=sil)
            d.line([sx + 40, sy + 2, sx + 95, sy], fill=sil, width=2)
        for x, y, ci, ph in self.lights:
            on = math.sin(t * 2.2 + ph) > -0.3
            c = LIGHTS[ci] if on else (70, 70, 70)
            r = 7 + (4 * pulse if on else 0)
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        d.polygon(star_shape(self.tree_x, self.tree_top + 10, 34 + 6 * pulse, t * 15), fill=(255, 225, 90))
        self.snow.draw(d, t)
        return img


class Fireplace:
    name = "Cozy Fireplace"

    def __init__(self, rng):
        walls = [((92, 30, 30), (52, 16, 18)), ((30, 52, 44), (16, 30, 26)), ((48, 38, 70), (26, 20, 40))]
        top, bot = walls[int(rng.integers(0, len(walls)))]
        self.bg = vgrad(top, bot)
        d = ImageDraw.Draw(self.bg)
        for x in range(0, W, 60):   # wallpaper stripes
            d.line([x, 0, x, 700], fill=tuple(min(255, int(c * 1.12)) for c in top), width=2)
        d.rectangle([0, 700, W, 760], fill=(70, 42, 28))            # wainscot
        d.rectangle([0, 760, W, H], fill=(58, 34, 22))               # floor
        for x in range(0, W, 160):
            d.line([x, 760, x - 80, H], fill=(48, 28, 18), width=3)
        d.ellipse([500, 900, 1420, 1080], fill=(120, 30, 34))         # rug
        # window
        self.win = (110, 170, 470, 600)
        x0, y0, x1, y1 = self.win
        d.rectangle([x0 - 16, y0 - 16, x1 + 16, y1 + 16], fill=(230, 225, 210))
        win_bg = vgrad((10, 18, 50), (40, 60, 110), x1 - x0, y1 - y0)
        self.bg.paste(win_bg, (x0, y0))
        d.ellipse([x1 - 120, y0 + 40, x1 - 50, y0 + 110], fill=(255, 250, 225))
        d.polygon([(x0, y1 - 60), (x0 + 150, y1 - 90), (x1, y1 - 50), (x1, y1), (x0, y1)], fill=(225, 235, 250))
        # fireplace
        fx0, fx1, fy0, fy1 = 720, 1200, 330, 760
        d.rectangle([fx0 - 60, fy0 - 40, fx1 + 60, fy0], fill=(110, 70, 45))   # mantel
        d.rectangle([fx0, fy0, fx1, fy1], fill=(140, 60, 45))
        for yy in range(fy0, fy1, 32):
            off = 0 if (yy // 32) % 2 else 32
            for xx in range(fx0 + off, fx1, 64):
                d.rectangle([xx, yy, xx + 60, yy + 28], outline=(110, 45, 35), width=2)
        self.hearth = (fx0 + 90, fy0 + 140, fx1 - 90, fy1)
        hx0, hy0, hx1, hy1 = self.hearth
        d.rounded_rectangle([hx0, hy0, hx1, hy1 + 20], radius=60, fill=(25, 12, 10))
        d.rectangle([hx0 + 40, hy1 - 40, hx1 - 40, hy1 - 20], fill=(80, 45, 25))   # logs
        for i, c in enumerate([(200, 40, 50), (40, 120, 70), (220, 200, 200)]):
            sx = fx0 + 40 + i * 150
            d.rectangle([sx, fy0, sx + 50, fy0 + 70], fill=c)
            d.polygon([(sx, fy0 + 70), (sx + 50, fy0 + 70), (sx + 80, fy0 + 110), (sx + 30, fy0 + 110)], fill=c)
            d.rectangle([sx - 4, fy0, sx + 54, fy0 + 16], fill=(250, 250, 250))
        # garland
        for x in range(fx0 - 60, fx1 + 60, 26):
            d.ellipse([x - 16, fy0 - 52, x + 16, fy0 - 26], fill=(30, 100, 55))
        self.lights = []
        self.tree_x = 1580
        self.tree_top = tree(d, self.tree_x, 900, 640, rng, self.lights)
        for gx in (-180, -60, 70, 170):
            c = [(200, 50, 60), (50, 110, 200), (230, 180, 50), (160, 80, 180)][int(rng.integers(0, 4))]
            d.rectangle([self.tree_x + gx - 45, 850, self.tree_x + gx + 45, 920], fill=c, outline=(255, 240, 200), width=3)
            d.line([self.tree_x + gx, 850, self.tree_x + gx, 920], fill=(255, 240, 200), width=8)
        self.snow = Snow(rng, n=120)
        self.rng = np.random.default_rng(int(rng.integers(0, 1e9)))
        self.glow = Image.new("L", (W, H), 0)
        hx0, hy0, hx1, hy1 = self.hearth
        ImageDraw.Draw(self.glow).ellipse([hx0 - 250, hy0 - 120, hx1 + 250, hy1 + 260], fill=70)
        self.glow = self.glow.filter(ImageFilter.GaussianBlur(90))

    def frame(self, t, pulse):
        img = self.bg.copy()
        flick = 0.85 + 0.15 * math.sin(t * 9) * math.sin(t * 3.3 + 1)
        img.paste(Image.new("RGB", (W, H), (255, 150, 60)), (0, 0), self.glow.point(lambda v: int(v * flick)))
        d = ImageDraw.Draw(img)
        # window snow
        x0, y0, x1, y1 = self.win
        for i in range(40):
            sx = x0 + ((i * 97 + t * 20 * (1 + i % 3)) % (x1 - x0))
            sy = y0 + ((i * 53 + t * 40 * (1 + i % 2)) % (y1 - y0 - 60))
            d.ellipse([sx - 3, sy - 3, sx + 3, sy + 3], fill=(255, 255, 255))
        d.line([(x0 + x1) / 2, y0, (x0 + x1) / 2, y1], fill=(230, 225, 210), width=12)
        d.line([x0, (y0 + y1) / 2, x1, (y0 + y1) / 2], fill=(230, 225, 210), width=12)
        # fire
        hx0, hy0, hx1, hy1 = self.hearth
        cx, base = (hx0 + hx1) / 2, hy1 - 40
        for layer, (col, scale) in enumerate([((255, 110, 30), 1.0), ((255, 170, 40), 0.72), ((255, 235, 140), 0.42)]):
            pts = [(cx - 150 * scale, base)]
            for k in range(9):
                u = k / 8
                x = cx - 150 * scale + 300 * scale * u
                hgt = (150 + 80 * math.sin(t * 7 + k * 1.7 + layer)) * scale * (1 - abs(u - 0.5) * 1.2)
                pts.append((x, base - max(hgt, 10)))
            pts.append((cx + 150 * scale, base))
            d.polygon(pts, fill=col)
        for x, y, ci, ph in self.lights:
            on = math.sin(t * 2.2 + ph) > -0.3
            c = LIGHTS[ci] if on else (70, 70, 70)
            r = 8 + (4 * pulse if on else 0)
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        d.polygon(star_shape(self.tree_x, self.tree_top + 12, 40 + 6 * pulse, t * 15), fill=(255, 225, 90))
        return img


SCENES = [Village, Fireplace]


# ====================================================================== lyric layout
def layout_line(draw, line, size, max_w=1440):
    full = " ".join(p[0] for p in line["pieces"])
    while size > 50 and draw.textlength(full, font=font(SERIF, size)) > max_w:
        size -= 2
    if size <= 50:
        size = 54
    f = font(SERIF, size)
    words, cur = [], []
    for text, beat, end in line["pieces"]:
        cur.append((text, beat))
        if end:
            words.append(cur)
            cur = []
    if cur:
        words.append(cur)
    sp = draw.textlength(" ", font=f)
    widths = [sum(draw.textlength(p, font=f) for p, _ in w) for w in words]
    rows, row, rw = [], [], 0
    for w, ww in zip(words, widths):
        if row and rw + sp + ww > max_w:
            rows.append(row)
            row, rw = [], 0
        row.append((w, ww))
        rw += (sp if rw else 0) + ww
    if row:
        rows.append(row)
    placed = []
    for ri, r in enumerate(rows):
        total = sum(ww for _, ww in r) + sp * (len(r) - 1)
        x = W / 2 - total / 2
        for w, ww in r:
            for p, beat in w:
                pw = draw.textlength(p, font=f)
                placed.append(dict(text=p, x=x, w=pw, row=ri, beat=beat))
                x += pw
            x += sp
    text = " ".join("".join(p for p, _ in w) for w in words)
    return dict(pieces=placed, rows=len(rows), size=size, text=text)


# ====================================================================== main
def make(out_dir: Path, rng, ledger, channel="holiday_long", song_key=None, lead=None, scene=None):
    if song_key is None:
        cands = [f"{s}|{l}" for s in SONGS for l in LEADS]
        song_key, lead = ledger.pick_fresh(channel, cands, rng).split("|")
    song = SONGS[song_key]
    lead = lead or str(rng.choice(list(LEADS)))
    transpose = song.get("transpose", 0) + int(rng.integers(-1, 2))
    arr = Arrangement(song, rng, lead, transpose)
    mix, total = render_audio(arr, rng, lead, transpose, song["feel"])
    Scene = SCENES[int(rng.integers(0, len(SCENES)))] if scene is None else {"village": Village, "fireplace": Fireplace}[scene]
    sc = Scene(rng)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    layouts = [layout_line(probe, ln, 70) if ln["pieces"] else None for ln in arr.lines]
    line_times = [(arr.t(ln["start"]), arr.t(ln["end"])) for ln in arr.lines]
    sec_times = [(arr.t(b), lab) for b, lab in arr.sections]
    beat_times = np.array([arr.t(k) for k in range(int(arr.end_beat) + 1)])
    end_t = arr.t(arr.end_beat)
    band = Image.new("RGBA", (W, 240), (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle([200, 10, W - 200, 230], radius=36, fill=(8, 10, 32, 205),
                                           outline=(255, 215, 120, 220), width=3)
    title = song["title"]

    def frame(t):
        k = np.searchsorted(beat_times, t) - 1
        pulse = max(0.0, 1 - (t - beat_times[k]) / 0.3) if k >= 0 else 0.0
        img = sc.frame(t, pulse)
        d = ImageDraw.Draw(img)
        # title card
        if t < 6.5:
            a = min(1.0, t / 0.8, (6.5 - t) / 1.0)
            if a > 0:
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                od.rounded_rectangle([360, 330, W - 360, 640], radius=50, fill=(10, 12, 28, int(170 * a)))
                od.text((W / 2, 440), title, font=font(SERIF2, 104), fill=(255, 225, 140, int(255 * a)), anchor="mm")
                od.text((W / 2, 560), f"Christmas Carol with Lyrics  ·  {LEADS[lead]} Sing-Along",
                        font=font(SERIF, 44), fill=(255, 255, 255, int(255 * a)), anchor="mm")
                img.paste(ov, (0, 0), ov)
                d = ImageDraw.Draw(img)
        # lyric band
        img.paste(band, (0, H - 250), band)
        d = ImageDraw.Draw(img)
        li = None
        for i, (a0, a1) in enumerate(line_times):
            nxt = line_times[i + 1][0] if i + 1 < len(line_times) else a1 + 3
            if a0 - 0.6 <= t < nxt - 0.6:
                li = i
        sec = [lab for st, lab in sec_times if st <= t + 0.6]
        if sec:
            lab = sec[-1]
            lw = d.textlength(lab, font=font(SERIF, 34)) + 50
            d.rounded_rectangle([W / 2 - lw / 2, H - 268, W / 2 + lw / 2, H - 224], radius=22, fill=(150, 30, 40),
                                outline=(255, 215, 120), width=2)
            d.text((W / 2, H - 246), lab, font=font(SERIF, 34), fill=(255, 240, 210), anchor="mm")
        if t < line_times[0][0] - 0.6:
            d.text((W / 2, H - 140), "~ Get ready to sing ~", font=font(SERIF, 64), fill=(255, 255, 255), anchor="mm")
        elif li is not None:
            ln, lay = arr.lines[li], layouts[li]
            if lay is None:
                d.text((W / 2, H - 140), "~ Instrumental ~", font=font(SERIF, 64), fill=(220, 225, 255), anchor="mm")
            else:
                f = font(SERIF, lay["size"])
                rh = lay["size"] * 1.15
                top = H - 150 - rh * lay["rows"] / 2 - (14 if lay["rows"] > 1 else 0)
                cur = None
                for p in lay["pieces"]:
                    pt = arr.t(p["beat"])
                    sung = t >= pt
                    if sung:
                        cur = (p, pt)
                    d.text((p["x"], top + rh * (p["row"] + 0.5)), p["text"], font=f, anchor="lm",
                           fill=(255, 210, 90) if sung else (255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
                if cur is not None:
                    p, pt = cur
                    ph = min(max((t - pt) / 0.32, 0), 1)
                    bx = p["x"] + p["w"] / 2
                    by = top + rh * p["row"] - 8 - 26 * math.sin(math.pi * ph)
                    d.ellipse([bx - 12, by - 12, bx + 12, by + 12], fill=(255, 90, 90), outline=(255, 255, 255), width=3)
                nl = next((layouts[j] for j in range(li + 1, len(layouts)) if layouts[j] is not None), None)
                if nl is not None and li + 1 < len(layouts) and layouts[li + 1] is not None:
                    d.text((W / 2, H - 58), layouts[li + 1]["text"], font=font(SERIF, 36), fill=(180, 190, 230), anchor="mm")
        if t > end_t + 0.8:
            a = min(1.0, (t - end_t - 0.8) / 1.0)
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            od = ImageDraw.Draw(ov)
            od.rounded_rectangle([460, 300, W - 460, 620], radius=50, fill=(10, 12, 28, int(180 * a)))
            od.text((W / 2, 420), "Merry Christmas!", font=font(SERIF2, 110), fill=(255, 120, 120, int(255 * a)), anchor="mm")
            od.text((W / 2, 540), "Thanks for singing along", font=font(SERIF, 48), fill=(255, 255, 255, int(255 * a)), anchor="mm")
            img.paste(ov, (0, 0), ov)
        return img

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"carol-{song_key}-{lead}-{Scene.__name__.lower()}"
    wav = out_dir / f"{stem}.wav"
    audio.write_wav(wav, mix)
    mp4 = out_dir / f"{stem}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "23", "-maxrate", "3500k", "-bufsize", "7000k", "-pix_fmt", "yuv420p", "-g", "48",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    wav.unlink()
    ledger.add(channel, f"{song_key}|{lead}", title=title)
    # ---------------- metadata
    sung = []
    for part_name, vk in song["form"]:
        if vk is not None and vk not in [s[0] for s in sung]:
            sung.append((vk, song["verses"][vk]))
    lyr_text = "\n\n".join("\n".join(" ".join(w.replace("-", "").replace("=", "-") for w in l.split() if w != "_")
                                     for l in lines) for _, lines in sung)
    mins, secs = divmod(int(total), 60)
    titles = [f"{title} 🎄 Christmas Carol with Lyrics | {LEADS[lead]} Sing-Along",
              f"{title} (Lyrics) 🎅 Cozy {LEADS[lead]} Christmas Carol",
              f"{title} – Christmas Sing-Along with Lyrics ❄️ {Scene.name}"]
    vt = str(rng.choice(titles))[:100]
    desc = (f"{vt}\n\nSing along to the classic Christmas carol \"{title}\" with easy-to-follow lyrics, "
            f"a gentle {LEADS[lead].lower()} arrangement and a {Scene.name.lower()} animation. Full song, {mins}:{secs:02d}.\n\n"
            f"🎵 {song['credit']}. Public domain; arranged and animated for this channel.\n\n"
            f"LYRICS\n{lyr_text}\n\n#christmascarols #christmasmusic #singalong #lyrics #christmas")
    return {"file": str(mp4), "title": vt, "description": desc[:4900], "duration": total,
            "tags": ["christmas carols", "christmas songs with lyrics", title.lower(), "sing along", "karaoke",
                     "christmas music", "carols", LEADS[lead].lower(), "christmas lyrics", "holiday music"],
            "category_id": "10", "made_for_kids": False}


def compilation(out_dir: Path, metas, rng):
    """Join rendered songs into one long video with chapters."""
    out_dir.mkdir(parents=True, exist_ok=True)
    listfile = out_dir / "concat.txt"
    listfile.write_text("".join(f"file '{Path(m['file']).resolve()}'\n" for m in metas))
    total = sum(m["duration"] for m in metas)
    mins = int(round(total / 60))
    out = out_dir / f"carol-compilation-{mins}min.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy",
                    "-movflags", "+faststart", str(out)], check=True)
    listfile.unlink()
    t, chapters = 0.0, []
    for m in metas:
        mm, ss = divmod(int(t), 60)
        chapters.append(f"{mm}:{ss:02d} {m['title'].split(' 🎄')[0].split(' (Lyrics)')[0].split(' –')[0]}")
        t += m["duration"]
    title = f"Christmas Carols with Lyrics 🎄 {mins} Minutes of Sing-Along Classics"
    desc = (f"{title}\n\nA cozy {mins}-minute collection of classic public-domain Christmas carols with on-screen lyrics.\n\n"
            "CHAPTERS\n" + "\n".join(chapters) + "\n\n#christmascarols #christmasmusic #singalong #lyrics")
    return {"file": str(out), "title": title, "description": desc, "duration": total,
            "tags": ["christmas carols", "christmas songs with lyrics", "christmas music playlist", "sing along",
                     "christmas compilation", "carols with lyrics"], "category_id": "10", "made_for_kids": False}


def make_compilation(out_dir: Path, rng, ledger, channel="holiday_long", n=6, scene=None):
    """Render n different carols (one shared scene style) and join them into one long video."""
    parts_dir = out_dir / "_parts"
    keys = [str(k) for k in rng.permutation(list(SONGS))[:n]]
    scene = scene or str(rng.choice(["village", "fireplace"]))
    parts = []
    for k in keys:
        lead = str(rng.choice(list(LEADS)))
        parts.append(make(parts_dir, rng, ledger, channel=channel + ":comp", song_key=k, lead=lead, scene=scene))
    comp = compilation(out_dir, parts, rng)
    for p in parts:
        Path(p["file"]).unlink(missing_ok=True)
    parts_dir.rmdir()
    return comp
