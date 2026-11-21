"""Build a narrated timeline: voice lines + sound effects + pauses, then mix with music."""
import numpy as np

from . import audio, tts


class Timeline:
    def __init__(self, voice="en-US-AnaNeural", rate="+0%", pitch="+0Hz"):
        self.voice, self.rate, self.pitch = voice, rate, pitch
        self.t = 0.4
        self.voice_clips = []   # (start, audio)
        self.sfx = []           # (start, audio, gain)
        self.segments = []      # dicts with start/end/kind/data

    def say(self, text, kind="say", gap=0.35, **data):
        clip = tts.speak(text, self.voice, self.rate, self.pitch)
        seg = {"start": self.t, "end": self.t + len(clip) / audio.SR, "kind": kind, "text": text, **data}
        self.voice_clips.append((self.t, clip))
        self.segments.append(seg)
        self.t = seg["end"] + gap
        return seg

    def hold(self, seconds, kind="hold", **data):
        seg = {"start": self.t, "end": self.t + seconds, "kind": kind, **data}
        self.segments.append(seg)
        self.t += seconds
        return seg

    def fx(self, sig, at=None, gain=0.6):
        self.sfx.append((self.t if at is None else at, sig, gain))

    @property
    def duration(self):
        return self.t + 0.6

    def at(self, t):
        """Segment active at time t (last one that started)."""
        cur = None
        for s in self.segments:
            if s["start"] <= t:
                cur = s
        return cur

    def talking(self, t):
        return any(s <= t <= s + len(c) / audio.SR for s, c in self.voice_clips)

    def mix(self, music=None, music_gain=0.35):
        n = int(self.duration * audio.SR)
        voice = np.zeros(n + audio.SR)
        for s, c in self.voice_clips:
            st = int(s * audio.SR)
            voice[st:st + len(c)] += c[: len(voice) - st]
        voice = voice[:n]
        voice = audio.normalize(voice, 0.85) if np.any(voice) else voice
        out = voice.copy()
        for s, sig, g in self.sfx:
            st = int(s * audio.SR)
            end = min(n, st + len(sig))
            if st < n:
                out[st:end] += sig[: end - st] * g
        if music is not None:
            m = np.resize(music, n)
            out += audio.duck(m, voice, 0.6) * music_gain
        return audio.normalize(out, 0.92)
