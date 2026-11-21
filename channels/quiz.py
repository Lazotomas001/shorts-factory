"""'Top performing' general channel, format #1: 3-question trivia quiz Shorts.

Questions come from data/quiz_bank.json (hand-checked) plus data/quiz_extra.json
(AI-suggested via `python run.py grow-quiz`, used only after you set "approved": true).
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import ImageDraw

from factory import audio
from factory.render import W, H, render_video, vgradient, text_block, font, fit_size, clamp01, ease_out_back
from factory.timeline import Timeline

DATA = Path(__file__).resolve().parent.parent / "data"
HEAD, BODY = "Anton-Regular.ttf", "ArchivoBlack-Regular.ttf"
VOICES = ["en-US-AndrewNeural", "en-US-ChristopherNeural", "en-US-EmmaNeural", "en-US-BrianNeural"]
THEMES = [((20, 10, 60), (90, 20, 120), (255, 200, 0)), ((5, 30, 60), (0, 110, 140), (0, 230, 200)),
          ((40, 5, 15), (140, 20, 50), (255, 120, 80)), ((10, 10, 10), (50, 50, 70), (120, 220, 255))]
HOOKS = ["Can you get all 3 right?", "Bet you can't get all 3!", "Quick quiz: 3 questions, 5 seconds each!",
         "Test your brain in 30 seconds!"]


def load_bank():
    bank = json.loads((DATA / "quiz_bank.json").read_text())
    extra = DATA / "quiz_extra.json"
    if extra.exists():
        bank += [q for q in json.loads(extra.read_text()) if q.get("approved")]
    return bank


def make(out_dir: Path, rng, ledger, channel="quiz", n_q=3, think=5):
    bank = load_bank()
    used = ledger.used(channel + ":q")
    fresh = [q for q in bank if q["id"] not in used] or bank
    idx = rng.permutation(len(fresh))[:n_q]
    qs = [fresh[i] for i in idx]
    for q in qs:
        opts = [q["a"]] + q["w"][:3]
        q["opts"] = [opts[i] for i in rng.permutation(len(opts))]
    tl = Timeline(voice=str(rng.choice(VOICES)), rate="+6%")
    hook = str(rng.choice(HOOKS))
    tl.say(hook, "hook", gap=0.2)
    for k, q in enumerate(qs):
        tl.fx(audio.whoosh(rng), gain=0.4)
        tl.say(f"Question {k + 1}. {q['q']}", "ask", gap=0.1, k=k)
        for s in range(think):
            tl.fx(audio.tick(), gain=0.6)
            tl.hold(1.0, "think", k=k, left=think - s)
        tl.fx(audio.ding(), gain=0.45)
        tl.say(f"It's {q['a']}!", "reveal", gap=0.35, k=k)
    tl.say("How many did you get? Comment your score!", "end", gap=0.3)
    music = audio.cheerful_loop(tl.duration, rng, inst="piano")
    mix = tl.mix(music, music_gain=0.18)
    top, bot, accent = THEMES[int(rng.integers(0, len(THEMES)))]
    bg = vgradient(top, bot)
    orbs = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(60, 180), rng.uniform(0, 6)) for _ in range(7)]

    def frame(t):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        for x, y, r, ph in orbs:
            yy = (y - t * 25) % (H + 400) - 200
            c = tuple(min(255, int(v * 1.35 + 12)) for v in bot)
            d.ellipse([x - r, yy - r, x + r, yy + r], outline=c, width=6)
        seg = tl.at(t) or tl.segments[0]
        kind = seg["kind"]
        d.text((W / 2, 230), "QUIZ TIME", font=font(HEAD, 120), fill=accent, anchor="mm", stroke_width=6,
               stroke_fill=(0, 0, 0))
        if kind == "hook":
            p = ease_out_back(clamp01((t - seg["start"]) / 0.5))
            text_block(d, hook, W / 2, 800, HEAD, int(120 * max(p, 0.1)), fill=(255, 255, 255), max_w=880)
        k = seg.get("k")
        if k is not None:
            q = qs[k]
            d.text((W / 2, 360), f"{k + 1} / {len(qs)}", font=font(BODY, 56), fill=(255, 255, 255), anchor="mm")
            d.rounded_rectangle([60, 430, W - 60, 760], radius=36, fill=(255, 255, 255))
            text_block(d, q["q"], W / 2, 595, BODY, 66, fill=(20, 20, 30), stroke=(255, 255, 255), sw=0, max_w=860)
            revealed = kind == "reveal"
            for i, o in enumerate(q["opts"]):
                y0 = 820 + i * 150
                ok = o == q["a"]
                if revealed:
                    fill = (40, 200, 90) if ok else (70, 70, 85)
                else:
                    fill = tuple(min(255, int(v * 1.6 + 30)) for v in top)
                d.rounded_rectangle([90, y0, W - 150, y0 + 120], radius=60, fill=fill, outline=(255, 255, 255), width=4)
                d.text((150, y0 + 60), "ABCD"[i], font=font(HEAD, 64), fill=accent, anchor="mm")
                sz = fit_size(d, o, BODY, 54, 680)
                d.text((210, y0 + 60), o, font=font(BODY, sz), fill=(255, 255, 255), anchor="lm")
                if revealed and ok:
                    pr = ease_out_back(clamp01((t - seg["start"]) / 0.4))
                    r = 40 * pr
                    cx = W - 220
                    d.ellipse([cx - r, y0 + 60 - r, cx + r, y0 + 60 + r], fill=(255, 255, 255))
                    if pr > 0.6:
                        d.line([cx - 18, y0 + 60, cx - 5, y0 + 75, cx + 22, y0 + 45], fill=(40, 200, 90), width=10)
            if kind in ("ask", "think"):
                total = think
                el = 0 if kind == "ask" else (think - seg["left"]) + (t - seg["start"])
                frac = clamp01(1 - el / total)
                d.rounded_rectangle([90, 1440, W - 280, 1480], radius=20, fill=(0, 0, 0))
                d.rounded_rectangle([90, 1440, 90 + (W - 370) * frac, 1480], radius=20, fill=accent)
                if kind == "think":
                    d.ellipse([W - 260, 1400, W - 140, 1520], fill=accent)
                    d.text((W - 200, 1460), str(seg["left"]), font=font(HEAD, 80), fill=(0, 0, 0), anchor="mm")
        if kind == "end":
            text_block(d, "How many did you get?", W / 2, 760, HEAD, 120, fill=(255, 255, 255), max_w=880)
            text_block(d, "Comment your score!", W / 2, 1000, HEAD, 90, fill=accent, max_w=880)
        return img

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "quiz-" + "-".join(q["id"] for q in qs)
    wav = out_dir / f"{stem}.wav"
    audio.write_wav(wav, mix)
    mp4 = render_video(out_dir / f"{stem}.mp4", tl.duration, frame, wav)
    wav.unlink()
    for q in qs:
        ledger.add(channel + ":q", q["id"])
    ledger.add(channel, stem)
    cats = sorted({q["cat"] for q in qs})
    title = f"{hook} 🧠 {' • '.join(c.title() for c in cats)} Quiz"
    return {"file": str(mp4), "title": title[:100],
            "description": f"{title}\n\nPause if you need more time! Answers are revealed after each timer.\n\n#shorts #quiz #trivia #brainteaser",
            "tags": ["quiz", "trivia", "general knowledge", "brain test", *cats], "category_id": "24"}
