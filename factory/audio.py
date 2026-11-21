"""Tiny offline music + sound-effect synthesizer (numpy only, no samples, no licensing)."""
import wave
import numpy as np

SR = 44100
_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(note: str) -> int:
    """'C#5' -> 73. Middle C = C4 = 60."""
    name, rest = note[0].upper(), note[1:]
    acc = 0
    while rest and rest[0] in "#b":
        acc += 1 if rest[0] == "#" else -1
        rest = rest[1:]
    return 12 * (int(rest) + 1) + _NOTE[name] + acc


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _env(n, attack=0.005, decay=1.0, release=0.05):
    t = np.arange(n) / SR
    e = np.exp(-t / max(decay, 1e-3))
    a = int(attack * SR)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    r = min(int(release * SR), n)
    if r > 0:
        e[-r:] *= np.linspace(1, 0, r)
    return e


# ---------------------------------------------------------------- instruments
def music_box(f, dur):
    t = _t(dur + 0.6)
    s = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 6)
         + 0.2 * np.sin(2 * np.pi * f * 2.0 * t))
    return s * _env(len(t), 0.002, 0.55, 0.05)


def celesta(f, dur):
    t = _t(dur + 0.5)
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 8) \
        + 0.15 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 4)
    return s * _env(len(t), 0.003, 0.7, 0.08)


def bell(f, dur):
    t = _t(dur + 1.2)
    parts = [(1, 1, 1.2), (2.76, .5, .6), (5.4, .25, .35), (0.5, .3, 1.5), (8.93, .1, .2)]
    s = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / d) for r, a, d in parts)
    return s * _env(len(t), 0.001, 99, 0.1)


def piano(f, dur):
    t = _t(dur + 0.4)
    s = sum((0.6 ** k) * np.sin(2 * np.pi * f * (k + 1) * (1 + 0.0004 * k * k) * t)
            * np.exp(-t * (1.5 + k)) for k in range(6))
    return s * _env(len(t), 0.004, 2.0, 0.1) * np.where(t < dur, 1, np.exp(-(t - dur) * 12))


def pluck_bass(f, dur):
    t = _t(dur + 0.2)
    s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 5)
    return s * _env(len(t), 0.01, 0.9, 0.08) * np.where(t < dur, 1, np.exp(-(t - dur) * 20))


def pad(f, dur):
    t = _t(dur + 0.4)
    s = sum(np.sin(2 * np.pi * f * d * t) for d in (0.996, 1.0, 1.004, 2.0 * 1.002)) / 3
    a = np.minimum(1, t / 0.35)
    rel = np.where(t < dur, 1, np.clip(1 - (t - dur) / 0.4, 0, 1))
    return s * a * rel


INSTRUMENTS = {"music_box": music_box, "celesta": celesta, "bell": bell, "piano": piano}


# ---------------------------------------------------------------- effects
def sleigh_bells(dur, rng):
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    # crude high-pass: difference filter, then jingle partials
    hp = np.diff(noise, prepend=0) * 0.5
    t = np.arange(n) / SR
    jingle = sum(np.sin(2 * np.pi * fr * t + rng.uniform(0, 6)) for fr in (5200, 6900, 8100, 9600)) * 0.15
    return (hp + jingle) * _env(n, 0.002, 0.07, 0.01)


def pop(rng=None):
    t = _t(0.12)
    f = 300 + 900 * np.exp(-t * 40)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.001, 0.05, 0.01)


def ding(f=1318.5):
    return bell(f, 0.3) * 0.6 + bell(f * 1.5, 0.3) * 0.3


def tick():
    t = _t(0.04)
    return np.sin(2 * np.pi * 2000 * t) * _env(len(t), 0.0005, 0.008, 0.005)


def whoosh(rng, dur=0.35):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    k = 60
    x = np.convolve(x, np.ones(k) / k, mode="same")
    return x * np.sin(np.linspace(0, np.pi, n)) * 3


def fanfare():
    out = np.zeros(int(1.2 * SR))
    for i, m in enumerate([72, 76, 79, 84]):
        s = celesta(hz(m), 0.25 if i < 3 else 0.6)
        st = int(i * 0.12 * SR)
        out[st:st + len(s)] += s[: len(out) - st]
    return out


# ---------------------------------------------------------------- mixing
class Mix:
    def __init__(self, seconds):
        self.buf = np.zeros(int(seconds * SR) + SR)

    def add(self, sig, at, gain=1.0):
        st = int(at * SR)
        if st >= len(self.buf):
            return
        end = min(len(self.buf), st + len(sig))
        self.buf[st:end] += sig[: end - st] * gain

    def note(self, inst, m, at, dur, gain=1.0):
        self.add(inst(hz(m), dur), at, gain)


def reverb(x, seconds=1.8, wet=0.25, seed=1):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x * (1 - wet) + y * wet


def duck(music, voice, amount=0.75, smooth=0.15):
    """Lower `music` wherever `voice` is active."""
    env = np.abs(voice)
    k = int(smooth * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 6, 0, 1)
    return music * (1 - amount * env)


def normalize(x, peak=0.89):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * peak


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype(np.int16)
    stereo = np.repeat(data[:, None], 2, axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


# ---------------------------------------------------------------- background loop
CHORDS = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10]}
DEGREE = {"I": (0, ""), "ii": (2, "m"), "iii": (4, "m"), "IV": (5, ""), "V": (7, ""), "vi": (9, "m")}


def cheerful_loop(seconds, rng, key=None, bpm=None, inst=None):
    """Original, randomly generated happy backing track (arpeggios + bass)."""
    key = key if key is not None else int(rng.integers(0, 7))
    bpm = bpm or int(rng.integers(104, 128))
    inst = INSTRUMENTS[inst or rng.choice(["music_box", "celesta", "piano"])]
    prog = [["I", "V", "vi", "IV"], ["I", "IV", "V", "I"], ["I", "vi", "IV", "V"], ["vi", "IV", "I", "V"]][
        int(rng.integers(0, 4))]
    pattern = [[0, 1, 2, 1], [0, 2, 1, 2], [0, 1, 2, 3 % 3]][int(rng.integers(0, 3))]
    beat = 60 / bpm
    mix = Mix(seconds)
    t, bar = 0.0, 0
    while t < seconds:
        root, q = DEGREE[prog[bar % 4]]
        tones = [60 + key + root + i for i in CHORDS[q]]
        mix.note(pluck_bass, 36 + key + root, t, beat * 2, 0.5)
        mix.note(pluck_bass, 36 + key + root + 7, t + beat * 2, beat * 2, 0.35)
        for i in range(8):
            m = tones[pattern[i % 4]] + (12 if i >= 4 else 0)
            mix.note(inst, m, t + i * beat / 2, beat / 2, 0.22)
        t += beat * 4
        bar += 1
    out = reverb(mix.buf, 1.2, 0.2)[: int(seconds * SR)]
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    return normalize(out, 0.5)
