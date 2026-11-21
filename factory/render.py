"""Frame-by-frame rendering to a vertical 1080x1920 MP4 via ffmpeg, plus drawing helpers."""
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
# Keep important content out of the Shorts UI (title/caption bottom, buttons right).
SAFE_TOP, SAFE_BOTTOM, SAFE_RIGHT = 160, 1520, 940


@lru_cache(maxsize=64)
def font(name: str, size: int):
    return ImageFont.truetype(str(FONTS / name), size)


def render_video(out_path, duration, draw_frame, audio_wav, fps=FPS, crf=21):
    """draw_frame(t) -> PIL.Image (RGB, W x H). Streams frames into ffmpeg."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-i", str(audio_wav), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out_path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(duration * fps)
    for i in range(n):
        img = draw_frame(i / fps)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out_path


# ---------------------------------------------------------------- drawing helpers
def vgradient(c1, c2, w=W, h=H):
    a = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(c1)[None, None, :] * (1 - a) + np.array(c2)[None, None, :] * a)
    return Image.fromarray(np.repeat(arr, w, axis=1).astype(np.uint8), "RGB")


def wrap(text, fnt, max_w, draw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=fnt) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(draw, text, cx, cy, fname, size, fill=(255, 255, 255), stroke=(0, 0, 0), sw=None,
               max_w=900, line_gap=1.12, min_size=40):
    """Centered, wrapped, outlined text that shrinks to fit 4 lines max."""
    while True:
        f = font(fname, size)
        lines = wrap(text, f, max_w, draw)
        if len(lines) <= 4 or size <= min_size:
            break
        size -= 6
    sw = sw if sw is not None else max(3, size // 12)
    lh = size * line_gap
    y = cy - lh * len(lines) / 2
    for ln in lines:
        draw.text((cx, y + lh / 2), ln, font=f, fill=fill, anchor="mm", stroke_width=sw, stroke_fill=stroke)
        y += lh
    return len(lines) * lh


def fit_size(draw, text, fname, size, max_w, min_size=30):
    """Largest font size <= size that keeps `text` on one line within max_w."""
    while size > min_size and draw.textlength(text, font=font(fname, size)) > max_w:
        size -= 4
    return size


def silhouette(draw_fn, cx, cy, box, color):
    """Run draw_fn(draw, x, y) on a transparent layer and return (RGBA layer, paste xy) flattened to one color."""
    layer = Image.new("RGBA", (box * 2, box * 2), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(layer), box, box)
    solid = Image.new("RGBA", layer.size, tuple(color) + (255,))
    solid.putalpha(layer.getchannel("A").point(lambda v: 255 if v > 20 else 0))
    return solid, (int(cx - box), int(cy - box))


def ease_out_back(x):
    x = min(max(x, 0), 1)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def clamp01(x):
    return min(max(x, 0.0), 1.0)
