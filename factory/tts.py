"""Free text-to-speech with automatic fallback.

Order: edge-tts (free Microsoft neural voices, needs internet)
       -> Piper (free offline neural voices, set PIPER_MODEL=/path/voice.onnx)
       -> espeak-ng (always available, robotic; last resort only).
Returns mono float32 numpy audio at 44.1 kHz.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .audio import SR

CACHE = Path(os.environ.get("TTS_CACHE", Path(__file__).resolve().parent.parent / "data" / "tts_cache"))
CACHE.mkdir(parents=True, exist_ok=True)
_warned = set()


def _decode(path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def _edge(text, voice, rate, pitch, out):
    if not shutil.which("edge-tts"):
        return False
    r = subprocess.run(["edge-tts", "--voice", voice, f"--rate={rate}", f"--pitch={pitch}",
                        "--text", text, "--write-media", str(out)], capture_output=True, timeout=60)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 1000


def _piper(text, out):
    model = os.environ.get("PIPER_MODEL")
    if not model or not shutil.which("piper"):
        return False
    r = subprocess.run(["piper", "--model", model, "--output_file", str(out)], input=text.encode(),
                       capture_output=True, timeout=120)
    return r.returncode == 0 and out.exists()


def _espeak(text, out, female=True):
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if not exe:
        raise RuntimeError("No TTS engine available. Install edge-tts (pip) or espeak-ng (apt).")
    subprocess.run([exe, "-v", "en-us+f3" if female else "en-us", "-s", "150", "-w", str(out), text], check=True)
    return True


def speak(text: str, voice="en-US-AnaNeural", rate="+0%", pitch="+0Hz") -> np.ndarray:
    key = hashlib.sha1(f"{text}|{voice}|{rate}|{pitch}".encode()).hexdigest()[:16]
    cached = CACHE / f"{key}.npy"
    if cached.exists():
        return np.load(cached)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        engine = None
        for name, fn, ext in (("edge", lambda o: _edge(text, voice, rate, pitch, o), "mp3"),
                              ("piper", lambda o: _piper(text, o), "wav"),
                              ("espeak", lambda o: _espeak(text, o), "wav")):
            out = d / f"v.{ext}"
            try:
                if fn(out):
                    engine = name
                    break
            except Exception:
                continue
        if engine is None:
            raise RuntimeError("All TTS engines failed")
        if engine == "espeak" and "espeak" not in _warned:
            _warned.add("espeak")
            print("[tts] WARNING: using robotic espeak fallback; edge-tts unavailable (no internet?)")
        audio = _decode(out)
    # trim silence at edges
    idx = np.where(np.abs(audio) > 0.01)[0]
    if len(idx):
        audio = audio[max(0, idx[0] - 800): idx[-1] + 2000]
    if engine != "espeak" and os.environ.get("TTS_NO_CACHE") != "1":
        np.save(cached, audio)
    return audio
