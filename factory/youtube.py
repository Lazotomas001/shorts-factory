"""YouTube Data API v3: one-time OAuth per channel, scheduled uploads, and trend research.

Costs nothing: the default quota (10,000 units/day plus a separate 100 uploads/day
bucket) is plenty for a few channels.

IMPORTANT: until your Google Cloud project passes YouTube's free API compliance audit,
YouTube locks every API-uploaded video as PRIVATE. Use upload mode "manual" until then
(see README).
"""
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def authorize(client_secret_file):
    """Run locally once per channel. Pick the channel's Brand Account in the browser."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    return creds.refresh_token


def _service(refresh_token):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=refresh_token, token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"], scopes=SCOPES)
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(meta, refresh_token, publish_at=None, made_for_kids=False):
    from googleapiclient.http import MediaFileUpload
    yt = _service(refresh_token)
    status = {"privacyStatus": "private" if publish_at else "public",
              "selfDeclaredMadeForKids": bool(made_for_kids),
              "containsSyntheticMedia": False}  # cartoons/graphics aren't "realistic" A/S content
    if publish_at:
        status["publishAt"] = publish_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    body = {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta.get("tags", [])[:30],
                        "categoryId": meta.get("category_id", "24")}, "status": status}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(meta["file"], chunksize=-1, resumable=True, mimetype="video/mp4"))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def schedule_slots(n, hours_utc, start=None):
    """Next n publish times from a list of daily UTC hours, at least 1h in the future."""
    start = start or datetime.now(timezone.utc) + timedelta(hours=1)
    out, day = [], start.replace(minute=0, second=0, microsecond=0)
    while len(out) < n:
        for h in sorted(hours_utc):
            slot = day.replace(hour=h)
            if slot > start and len(out) < n:
                out.append(slot)
        day += timedelta(days=1)
    return out


# ---------------------------------------------------------------- trend research
def _get(url, params):
    import urllib.parse
    import urllib.request
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=30) as r:
        return json.loads(r.read())


def research(queries, api_key, days=30, per_query=25):
    """Top recent Shorts per query, ranked by views/day. Uses ~100 units per query."""
    after = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    rows = []
    for q in queries:
        s = _get("https://www.googleapis.com/youtube/v3/search",
                 {"part": "snippet", "q": q, "type": "video", "videoDuration": "short", "order": "viewCount",
                  "publishedAfter": after, "maxResults": per_query, "key": api_key})
        ids = [i["id"]["videoId"] for i in s.get("items", [])]
        if not ids:
            continue
        v = _get("https://www.googleapis.com/youtube/v3/videos",
                 {"part": "snippet,statistics,contentDetails", "id": ",".join(ids), "key": api_key})
        for it in v.get("items", []):
            pub = datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00"))
            age = max((datetime.now(timezone.utc) - pub).total_seconds() / 86400, 0.5)
            views = int(it["statistics"].get("viewCount", 0))
            rows.append({"query": q, "title": it["snippet"]["title"], "channel": it["snippet"]["channelTitle"],
                         "views": views, "views_per_day": int(views / age), "duration": it["contentDetails"]["duration"],
                         "tags": it["snippet"].get("tags", [])[:15], "url": f"https://youtube.com/shorts/{it['id']}"})
    rows.sort(key=lambda r: -r["views_per_day"])
    return rows


def report_markdown(rows, top=40):
    words = Counter()
    for r in rows:
        for w in re.findall(r"[a-zA-Z']{3,}", r["title"].lower()):
            if w not in {"the", "and", "for", "with", "you", "your", "this", "shorts", "short"}:
                words[w] += 1
    tags = Counter(t.lower() for r in rows for t in r["tags"])
    lines = ["# Trend report", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}", "",
             "## Most common title words", ", ".join(f"{w} ({c})" for w, c in words.most_common(25)), "",
             "## Most common tags", ", ".join(f"{w} ({c})" for w, c in tags.most_common(25)), "",
             "## Top Shorts by views/day", "", "| views/day | views | title | channel |", "|---|---|---|---|"]
    for r in rows[:top]:
        title = r["title"].replace("|", "/")
        lines.append(f"| {r['views_per_day']:,} | {r['views']:,} | [{title}]({r['url']}) | {r['channel']} |")
    return "\n".join(lines)
