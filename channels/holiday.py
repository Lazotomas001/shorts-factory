"""Holiday music channel: Christmas sing-along Shorts with karaoke lyrics.

Public-domain carols, arranged and synthesized from scratch each time with a different
instrument, key, tempo and animated winter scene.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from factory import audio
from factory.audio import midi, Mix, CHORDS
from factory.render import W, H, render_video, vgradient, font, fit_size, text_block, clamp01, ease_out_back
from channels.carols import SONGS

FONT = "ComicNeue-Bold.otf"
LEADS = {"music_box": "Music Box", "celesta": "Celesta", "bell": "Bells", "piano": "Piano"}
SKIES = [((10, 20, 60), (40, 70, 140)), ((25, 15, 55), (90, 60, 140)), ((5, 35, 55), (30, 110, 130)),
         ((20, 25, 45), (70, 80, 120))]
LIGHT_COLS = [(255, 70, 70), (255, 210, 60), (90, 200, 255), (120, 255, 120), (255, 140, 220)]


# ------------------------------------------------------------------ music
def chord_tones(name, transpose):
    if name == "N":
        return None
    root = name[0]
    rest = name[1:]
    acc = 0
    if rest[:1] in ("#", "b"):
        acc = 1 if rest[0] == "#" else -1
        rest = rest[1:]
    q = "m" if rest.startswith("m") else ("7" if "7" in rest else "")
    r = midi(root + "3") + acc + transpose
    return r, [r + 12 + i for i in CHORDS[q]]


def arrange(song, rng, transpose, speed, lead_name):
    """Returns (audio, notes, line_spans, total_seconds, faster_at)."""
    lead = audio.INSTRUMENTS[lead_name]
    spb0 = 60 / (song["bpm"] * speed)
    meter = song["meter"]
    sections = list(zip(song["sections"], song["chords"]))
    plan = [(s, c, 1.0) for s, c in sections]
    if song.get("repeat_faster"):
        plan += [(s, c, 1.18) for s, c in sections]
    low = min(midi(n[0]) for sec in song["sections"] for ln in sec for n in ln)
    octave = 12 if low + transpose < 62 else 0
    # timeline in seconds
    t = 0.6
    intro_beats = meter * (2 if meter == 3 else 1)
    count_in = []
    for b in range(intro_beats):
        count_in.append(t + b * spb0)
    t += intro_beats * spb0
    notes, chords, line_spans, faster_at = [], [], [], None
    for si, (sec, chs, sp) in enumerate(plan):
        spb = spb0 / sp
        if sp > 1 and faster_at is None:
            faster_at = t
            t += meter * spb  # one bar break, bells only
        ct = t
        for beats, name in chs:
            chords.append((ct, beats * spb, name))
            ct += beats * spb
        for ln in sec:
            ls = t
            for p, b, syl in ln:
                notes.append({"t": t, "d": b * spb, "m": midi(p) + transpose + octave, "syl": syl, "line": len(line_spans)})
                t += b * spb
            line_spans.append((ls, t))
    end = t
    total = end + 3.2
    mix = Mix(total)
    # lead
    for n in notes:
        mix.note(lead, n["m"], n["t"], n["d"] * 0.95, 0.5)
    # harmony: soft pad + bass
    for ct, dur, name in chords:
        ch = chord_tones(name, transpose)
        if not ch:
            continue
        root, tones = ch
        for m in tones[:3]:
            mix.note(audio.pad, m, ct, dur * 0.98, 0.07)
        mix.note(audio.pluck_bass, root, ct, min(dur, spb0 * 2), 0.32)
        if dur >= 4 * spb0 * 0.8:
            mix.note(audio.pluck_bass, root + 7, ct + dur / 2, dur / 2, 0.22)
    # final chord ring
    final = chord_tones(song["chords"][-1][-1][1], transpose)
    if final:
        for m in final[1]:
            mix.note(audio.bell, m + 12, end, 2.0, 0.12)
    # percussion
    if song["bells"]:
        bt = 0.6
        while bt < end + 0.01:
            mix.add(audio.sleigh_bells(0.25, rng), bt, 0.18)
            bt += spb0 / (1.18 if faster_at and bt >= faster_at else 1)
    else:
        for ct, dur, name in chords:
            mix.add(audio.bell(audio.hz(84 + transpose), 0.5), ct, 0.05)
    for b in count_in:
        mix.add(audio.sleigh_bells(0.3, rng), b, 0.35)
    out = audio.reverb(mix.buf, 2.2, 0.3)[: int(total * audio.SR)]
    fade = int(1.5 * audio.SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return audio.normalize(out, 0.9), notes, line_spans, total, faster_at, count_in


# ------------------------------------------------------------------ visuals
class WinterScene:
    def __init__(self, rng):
        top, bot = SKIES[int(rng.integers(0, len(SKIES)))]
        self.bg = vgradient(top, bot)
        d = ImageDraw.Draw(self.bg)
        self.stars = [(rng.uniform(0, W), rng.uniform(0, 800), rng.uniform(1.5, 4), rng.uniform(0, 6)) for _ in range(90)]
        mx, my = rng.uniform(150, 350), rng.uniform(420, 560)
        for r, a in ((120, 30), (95, 60)):
            d.ellipse([mx - r, my - r, mx + r, my + r], fill=(255, 250, 220) if r < 100 else (60, 70, 120))
        d.ellipse([mx - 80, my - 80, mx + 80, my + 80], fill=(255, 248, 215))
        ph = rng.uniform(0, 6)
        for col, base, amp, fq in (((200, 215, 240), 1020, 40, 0.005), ((235, 242, 255), 1080, 30, 0.008)):
            pts = [(x, base + amp * math.sin(x * fq + ph)) for x in range(0, W + 20, 20)]
            d.polygon(pts + [(W, H), (0, H)], fill=col)
        # house
        hx = rng.uniform(120, 260)
        d.rectangle([hx - 110, 880, hx + 110, 1040], fill=(150, 60, 50), outline=(80, 30, 30), width=5)
        d.polygon([(hx - 140, 885), (hx + 140, 885), (hx, 770)], fill=(245, 248, 255), outline=(180, 190, 210))
        self.windows = [(hx - 70, 920, hx - 20, 970), (hx + 20, 920, hx + 70, 970)]
        d.rectangle([hx - 22, 980, hx + 22, 1040], fill=(90, 50, 30))
        # tree
        self.tree = (rng.uniform(700, 800), 1050)
        tx, ty = self.tree
        d.rectangle([tx - 25, ty - 40, tx + 25, ty + 10], fill=(100, 60, 30))
        self.lights = []
        for i, (w, top_y, bot_y) in enumerate(((210, 760, 1000), (170, 640, 860), (125, 530, 730))):
            d.polygon([(tx - w, bot_y), (tx + w, bot_y), (tx, top_y)], fill=(30, 120, 60), outline=(20, 80, 40))
            for k in range(7):
                u = (k + 0.5) / 7
                y = top_y + (bot_y - top_y) * (0.35 + 0.6 * ((k * 0.37) % 1))
                half = w * (y - top_y) / (bot_y - top_y)
                self.lights.append((tx - half * 0.85 + 2 * half * 0.85 * u, y, k + i))
        for gx, gc in ((tx - 150, (220, 60, 60)), (tx + 120, (60, 120, 220)), (tx - 40, (240, 190, 50))):
            d.rectangle([gx - 40, 1010, gx + 40, 1080], fill=gc, outline=(255, 255, 255), width=4)
            d.line([gx, 1010, gx, 1080], fill=(255, 255, 255), width=8)
        rng_s = np.random.default_rng(int(rng.integers(0, 1e9)))
        n = int(rng.integers(120, 220))
        self.snow = np.column_stack([rng_s.uniform(0, W, n), rng_s.uniform(0, H, n), rng_s.uniform(3, 10, n),
                                     rng_s.uniform(0, 6, n)])

    def draw(self, t, beat_pulse=0.0):
        img = self.bg.copy()
        d = ImageDraw.Draw(img)
        for x, y, r, ph in self.stars:
            a = 0.5 + 0.5 * math.sin(t * 2 + ph)
            rr = r * (0.6 + 0.6 * a)
            c = int(160 + 95 * a)
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(c, c, int(c * 0.9)))
        for wx in self.windows:
            g = int(200 + 40 * math.sin(t * 3))
            d.rectangle(wx, fill=(255, g, 110))
        tx, ty = self.tree
        for i, (x, y, k) in enumerate(self.lights):
            on = (int(t * 2.5) + k) % 3 != 0
            c = LIGHT_COLS[(k + i) % len(LIGHT_COLS)] if on else (60, 60, 60)
            r = 11 + (5 * beat_pulse if on else 0)
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        sr = 46 + 10 * beat_pulse
        sx, sy = tx, 520
        pts = []
        for i in range(10):
            rr = sr if i % 2 == 0 else sr * 0.45
            a = math.radians(-90 + i * 36 + t * 20)
            pts.append((sx + rr * math.cos(a), sy + rr * math.sin(a)))
        d.polygon(pts, fill=(255, 220, 60), outline=(255, 250, 200))
        s = self.snow
        ys = (s[:, 1] + t * s[:, 2] * 18) % (H + 20) - 10
        xs = (s[:, 0] + np.sin(t * 0.8 + s[:, 3]) * 25) % W
        for x, y, r in zip(xs, ys, s[:, 2]):
            r = r * 0.8
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
        return img, d


def build_lyric_layout(draw, notes, n_lines):
    """Per line: rows of words; each word is a list of pieces with note times; computed x positions."""
    layouts = []
    for li in range(n_lines):
        words, cur = [], []
        for n in [x for x in notes if x["line"] == li]:
            if n["syl"] == "~":
                continue
            syl = n["syl"]
            cont = syl.endswith("-") or syl.endswith("=")
            cur.append((syl.rstrip("-").replace("=", "-"), n["t"]))
            if not cont:
                words.append(cur)
                cur = []
        if cur:
            words.append(cur)
        text = " ".join("".join(p for p, _ in w) for w in words)
        size = 96
        fnt = font(FONT, size)
        rows, row, row_w = [], [], 0
        max_w = 900
        sp = draw.textlength(" ", font=fnt)
        for w in words:
            ww = draw.textlength("".join(p for p, _ in w), font=fnt)
            if row and row_w + sp + ww > max_w:
                rows.append(row)
                row, row_w = [], 0
            row.append(w)
            row_w += (sp if row_w else 0) + ww
        rows.append(row)
        placed = []
        for ri, row in enumerate(rows):
            total = sum(draw.textlength("".join(p for p, _ in w), font=fnt) for w in row) + sp * (len(row) - 1)
            x = W / 2 - total / 2
            for w in row:
                for p, nt in w:
                    pw = draw.textlength(p, font=fnt)
                    placed.append({"text": p, "x": x, "w": pw, "row": ri, "t": nt})
                    x += pw
                x += sp
        layouts.append({"pieces": placed, "rows": len(rows), "size": size, "text": text})
    return layouts


def make(out_dir: Path, rng, ledger, channel="holiday", song_key=None):
    lead = str(rng.choice(list(LEADS)))
    if song_key is None:
        cands = [f"{s}|{l}" for s in SONGS for l in LEADS]
        song_key, lead = ledger.pick_fresh(channel, cands, rng).split("|")
    song = SONGS[song_key]
    transpose = int(rng.integers(-2, 3))
    speed = float(rng.uniform(0.94, 1.06))
    mix, notes, spans, total, faster_at, count_in = arrange(song, rng, transpose, speed, lead)
    if total > 59 and song.get("repeat_faster"):  # keep Shorts under a minute
        song = {**song, "repeat_faster": False}
        mix, notes, spans, total, faster_at, count_in = arrange(song, rng, transpose, speed, lead)
    scene = WinterScene(rng)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    layouts = build_lyric_layout(probe, notes, len(spans))
    note_times = np.array([n["t"] for n in notes])
    title_text = song["title"]
    end_t = spans[-1][1]

    def frame(t):
        k = np.searchsorted(note_times, t) - 1
        pulse = 0.0
        if k >= 0:
            pulse = max(0.0, 1 - (t - note_times[k]) / 0.25)
        img, d = scene.draw(t, pulse)
        # title
        ts = fit_size(d, title_text, FONT, 104, 900)
        d.text((W / 2, 230), title_text, font=font(FONT, ts), fill=(255, 235, 120), anchor="mm",
               stroke_width=8, stroke_fill=(140, 20, 30))
        d.text((W / 2, 335), "Sing-Along  *  " + LEADS[lead] + " Version", font=font(FONT, 48), fill=(255, 255, 255),
               anchor="mm", stroke_width=4, stroke_fill=(30, 30, 60))
        # count-in
        if t < spans[0][0]:
            left = sum(1 for b in count_in if b > t)
            label = "Ready?" if left > 3 else (str(left) if left > 0 else "Sing!")
            d.rounded_rectangle([290, 1140, 790, 1360], radius=40, fill=(15, 20, 45), outline=(255, 215, 90), width=5)
            text_block(d, label, W / 2, 1250, FONT, 150, fill=(255, 255, 255), stroke=(140, 20, 30), sw=10)
        if faster_at and faster_at <= t < faster_at + 60 / song["bpm"] * song["meter"] * 1.2:
            text_block(d, "Now FASTER!", W / 2, 680, FONT, 130, fill=(255, 90, 90), stroke=(255, 255, 255), sw=10)
        # lyrics panel
        li = next((i for i, (a, b) in enumerate(spans) if a - 0.35 <= t < (spans[i + 1][0] - 0.35 if i + 1 < len(spans) else b + 0.5)), None)
        if li is not None:
            lay = layouts[li]
            rows = lay["rows"]
            row_h = lay["size"] * 1.15
            top = 1250 - row_h * rows / 2
            d.rounded_rectangle([40, top - 50, W - 40, top + row_h * rows + 50], radius=40, fill=(15, 20, 45),
                                outline=(255, 215, 90), width=5)
            fnt = font(FONT, lay["size"])
            cur_piece = None
            for p in lay["pieces"]:
                y = top + row_h * (p["row"] + 0.5)
                sung = t >= p["t"]
                if sung:
                    cur_piece = p
                d.text((p["x"], y), p["text"], font=fnt, anchor="lm", fill=(255, 215, 70) if sung else (255, 255, 255),
                       stroke_width=3, stroke_fill=(0, 0, 0))
            if cur_piece is not None:
                ph = clamp01((t - cur_piece["t"]) / 0.3)
                bx = cur_piece["x"] + cur_piece["w"] / 2
                by = top + row_h * cur_piece["row"] - 18 - 30 * math.sin(math.pi * ph)
                d.ellipse([bx - 16, by - 16, bx + 16, by + 16], fill=(255, 80, 80), outline=(255, 255, 255), width=4)
            # next line preview
            if li + 1 < len(spans):
                nxt = layouts[li + 1]["text"]
                text_block(d, nxt, W / 2, top + row_h * rows + 105, FONT, 54, fill=(35, 45, 95),
                           stroke=(255, 255, 255), sw=4, max_w=900)
        if t > end_t + 0.3:
            p = ease_out_back(clamp01((t - end_t - 0.3) / 0.6))
            text_block(d, "Merry Christmas!", W / 2, 700, FONT, int(140 * max(p, 0.05)), fill=(255, 90, 90),
                       stroke=(255, 255, 255), sw=10)
        return img

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"holiday-{song_key}-{lead}"
    wav = out_dir / f"{stem}.wav"
    audio.write_wav(wav, mix)
    mp4 = render_video(out_dir / f"{stem}.mp4", total, frame, wav)
    wav.unlink()
    ledger.add(channel, f"{song_key}|{lead}", title=song["title"])
    titles = [f"{song['title']} 🎄 Christmas Sing-Along with Lyrics ({LEADS[lead]})",
              f"Sing {song['title']}! 🎅 Easy Lyrics for Kids & Families",
              f"{song['title']} – Cozy {LEADS[lead]} Christmas Karaoke ❄️"]
    title = str(rng.choice(titles))
    desc = (f"{title}\n\nSing along to the classic carol \"{song['title']}\" ({song['year']}, public domain), "
            f"arranged as an original {LEADS[lead].lower()} version with bouncing-ball lyrics and a snowy winter scene.\n\n"
            "#shorts #christmas #christmassongs #singalong #christmasmusic")
    return {"file": str(mp4), "title": title[:100], "description": desc,
            "tags": ["christmas songs", "christmas carols", "sing along", "karaoke", "lyrics", song["title"].lower(),
                     "christmas music", "holiday music", LEADS[lead].lower()],
            "category_id": "10"}
