"""Remembers what each channel already published so videos don't repeat (helps with
YouTube's 'inauthentic / repetitive content' rules and keeps viewers interested)."""
import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "data" / "history.json"


class Ledger:
    def __init__(self, path=PATH):
        self.path = Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {}

    def used(self, channel):
        return {e["key"] for e in self.data.get(channel, [])}

    def recent(self, channel, n=10):
        return [e["key"] for e in self.data.get(channel, [])[-n:]]

    def add(self, channel, key, **info):
        self.data.setdefault(channel, []).append(
            {"key": key, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **info})
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=1))

    def pick_fresh(self, channel, candidates, rng):
        """Pick a candidate key not used before; if all used, the least-recently used."""
        used = self.used(channel)
        fresh = [c for c in candidates if c not in used]
        if fresh:
            return fresh[int(rng.integers(0, len(fresh)))]
        order = [e["key"] for e in self.data.get(channel, [])]
        return min(candidates, key=lambda c: max(i for i, k in enumerate(order) if k == c))
