#!/usr/bin/env python3
"""Shorts Factory command line.

  python run.py make --channel kids --count 3        # render videos into outbox/
  python run.py daily                                 # what the scheduler runs: make + upload/queue for every channel
  python run.py trends --channel kids                 # trend report (needs YT_API_KEY)
  python run.py auth --channel kids --secret client_secret.json   # one-time, on your computer
  python run.py grow-quiz --n 30                      # optional: AI-suggested quiz questions for you to approve
"""
import argparse
import importlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from factory.ledger import Ledger  # noqa: E402

OUTBOX = ROOT / "outbox"


def load_config():
    return yaml.safe_load((ROOT / "channels.yaml").read_text())["channels"]


def in_season(cfg, today=None):
    if "season" not in cfg:
        return True
    today = today or date.today()
    md = today.strftime("%m-%d")
    a, b = cfg["season"]
    return a <= md <= b if a <= b else (md >= a or md <= b)


def make(key, cfg, count, ledger, seed=None, out_sub=None, **kw):
    mod = importlib.import_module(f"channels.{cfg['module']}")
    out_dir = out_sub or (OUTBOX / date.today().isoformat() / key)
    metas = []
    for i in range(count):
        rng = np.random.default_rng(seed + i if seed is not None else None)
        meta = mod.make(out_dir, rng, ledger, channel=key, **{**cfg.get("make_args", {}), **kw})
        meta["made_for_kids"] = cfg.get("made_for_kids", False)
        meta["channel"] = key
        metas.append(meta)
        print(f"[{key}] made {Path(meta['file']).name}: {meta['title']}")
    return out_dir, metas


def write_sheet(out_dir, metas, cfg):
    (out_dir / "manifest.json").write_text(json.dumps(metas, indent=1, ensure_ascii=False))
    lines = [f"# Upload sheet – {cfg.get('name', '')} – {date.today()}", "",
             f"Audience: **{'Yes, it is made for kids' if cfg.get('made_for_kids') else 'No, not made for kids'}**  ",
             "Altered/synthetic content: **No** (animated, not realistic)", ""]
    for m in metas:
        lines += [f"## {Path(m['file']).name}", "", f"**Title:** {m['title']}", "", "**Description:**", "```",
                  m["description"], "```", f"**Tags:** {', '.join(m['tags'])}", ""]
    (out_dir / "UPLOAD_SHEET.md").write_text("\n".join(lines))


def cmd_daily(args):
    from factory import youtube
    cfgs, ledger = load_config(), Ledger()
    for key, cfg in cfgs.items():
        if args.channel and key != args.channel:
            continue
        if not cfg.get("enabled") or not in_season(cfg):
            print(f"[{key}] skipped (disabled or out of season)")
            continue
        out_dir, metas = make(key, cfg, cfg.get("per_day", 1), ledger)
        mod = importlib.import_module(f"channels.{cfg['module']}")
        if hasattr(mod, "make_compilation") and date.today().weekday() in cfg.get("compilation_weekdays", []):
            comp = mod.make_compilation(out_dir, np.random.default_rng(), ledger, channel=key,
                                        n=cfg.get("compilation_songs", 6))
            comp["made_for_kids"], comp["channel"], comp["large"] = cfg.get("made_for_kids", False), key, True
            metas.append(comp)
            print(f"[{key}] made compilation {Path(comp['file']).name}")
        token = os.environ.get(f"YT_REFRESH_TOKEN_{key.upper()}")
        if cfg.get("upload_mode") == "api" and token:
            slots = youtube.schedule_slots(len(metas), cfg.get("publish_hours_utc", [15]))
            for m, slot in zip(metas, slots):
                vid = youtube.upload(m, token, publish_at=slot, made_for_kids=cfg.get("made_for_kids", False))
                m["video_id"], m["publish_at"] = vid, slot.isoformat()
                Path(m["file"]).unlink()
                print(f"[{key}] uploaded {vid}, publishes {slot:%Y-%m-%d %H:%M} UTC")
        write_sheet(out_dir, metas, cfg)


def cmd_make(args):
    cfgs, ledger = load_config(), Ledger()
    kw = {}
    if args.format:
        kw["fmt" if cfgs[args.channel]["module"] == "kids" else "song_key"] = args.format
    if args.compilation:
        mod = importlib.import_module(f"channels.{cfgs[args.channel]['module']}")
        out_dir = OUTBOX / date.today().isoformat() / args.channel
        comp = mod.make_compilation(out_dir, np.random.default_rng(args.seed), ledger, channel=args.channel, n=args.count)
        comp["made_for_kids"] = cfgs[args.channel].get("made_for_kids", False)
        write_sheet(out_dir, [comp], cfgs[args.channel])
        print("made", comp["file"])
        return
    out_dir, metas = make(args.channel, cfgs[args.channel], args.count, ledger, seed=args.seed, **kw)
    write_sheet(out_dir, metas, cfgs[args.channel])


def cmd_trends(args):
    from factory import youtube
    key = os.environ.get("YT_API_KEY") or sys.exit("Set YT_API_KEY (free key from Google Cloud console).")
    cfg = load_config()[args.channel]
    rows = youtube.research(cfg["trend_queries"], key, days=args.days)
    out = ROOT / "reports" / f"trends-{args.channel}-{date.today()}.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(youtube.report_markdown(rows))
    print(f"Wrote {out} ({len(rows)} videos analysed)")


def cmd_auth(args):
    from factory import youtube
    token = youtube.authorize(args.secret)
    print(f"\nSave this as GitHub secret  YT_REFRESH_TOKEN_{args.channel.upper()} :\n\n{token}\n")


def cmd_check_auth(args):
    """Verify the GitHub secrets work: prints which channel the refresh token belongs to."""
    from factory import youtube
    for key in load_config():
        token = os.environ.get(f"YT_REFRESH_TOKEN_{key.upper()}")
        if not token:
            print(f"[{key}] no refresh token secret set")
            continue
        try:
            resp = youtube._service(token).channels().list(part="snippet", mine=True).execute()
            for ch in resp.get("items", []):
                print(f"[{key}] OK -> channel '{ch['snippet']['title']}' ({ch['id']})")
        except Exception as e:  # noqa: BLE001
            print(f"[{key}] FAILED: {type(e).__name__}: {str(e)[:300]}")


def cmd_grow_quiz(args):
    from factory import llm
    from channels.quiz import load_bank
    bank = load_bank()
    path = ROOT / "data" / "quiz_extra.json"
    extra = json.loads(path.read_text()) if path.exists() else []
    new = llm.quiz_questions(args.n, [q["q"] for q in bank + extra])
    start = len(bank) + len(extra)
    for i, q in enumerate(new):
        q.update({"id": f"x{start + i:04d}", "approved": False})
    path.write_text(json.dumps(extra + new, indent=1, ensure_ascii=False))
    print(f"Added {len(new)} questions to {path}. Fact-check them, then set \"approved\": true.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("daily"); d.add_argument("--channel"); d.set_defaults(fn=cmd_daily)
    m = sub.add_parser("make"); m.add_argument("--channel", required=True); m.add_argument("--count", type=int, default=1)
    m.add_argument("--format", help="kids: counting|colors|shadow; holiday/holiday_long: song key, e.g. silent_night")
    m.add_argument("--seed", type=int); m.add_argument("--compilation", action="store_true")
    m.set_defaults(fn=cmd_make)
    t = sub.add_parser("trends"); t.add_argument("--channel", required=True); t.add_argument("--days", type=int, default=30)
    t.set_defaults(fn=cmd_trends)
    a = sub.add_parser("auth"); a.add_argument("--channel", required=True); a.add_argument("--secret", default="client_secret.json")
    a.set_defaults(fn=cmd_auth)
    c = sub.add_parser("check-auth"); c.set_defaults(fn=cmd_check_auth)
    g = sub.add_parser("grow-quiz"); g.add_argument("--n", type=int, default=30); g.set_defaults(fn=cmd_grow_quiz)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
