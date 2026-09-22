#!/usr/bin/env python3
"""Print every Issue #1 bus comment above a watermark, in ascending order, with its full body.

Usage: bus_new.py <min_id_exclusive> [--repo Owner/Slug] [--max N]

Why this exists: the patrol prints a truncated index, and twice now I have reasoned about the
bus from a partial listing. This tool answers exactly one question - "what arrived since the
comment I already read" - and it prints the whole body so nothing is paraphrased from a header.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_DEFAULT = "Canshu-King/CityNexus-Workspace"
ISSUE = 1


TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"


def token() -> str:
    try:
        tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if tok:
            return tok
    except OSError:
        pass
    out = subprocess.run(
        ["git", "credential-fill"],
        input="https://github.com\n\n",
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    for line in out.splitlines():
        if line.startswith("password="):
            return line[len("password="):].strip()
    raise SystemExit("NO_TOKEN: neither the patrol token file nor credential-fill produced one")


def get(url: str, tok: str, attempts: int = 4) -> tuple[list | dict, dict]:
    """Fetch with retries: this gateway truncates big paged bodies, and a half-read page must
    never be reported as "no new comments"."""

    last: Exception | None = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + tok,
            "Accept": "application/vnd.github+json",
            "User-Agent": "citynexus-commander-patrol",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
            return json.loads(raw.decode("utf-8")), dict(r.headers)
        except Exception as exc:  # noqa: BLE001
            last = exc
            import time as _t

            _t.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"FETCH_FAILED after {attempts} attempts: {type(last).__name__}: {last}")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("usage: bus_new.py <min_id_exclusive> [--repo R] [--max N] [--tail]")
    watermark = int(sys.argv[1])
    repo = REPO_DEFAULT
    tail = False
    if "--repo" in sys.argv:
        repo = sys.argv[sys.argv.index("--repo") + 1]
    if "--tail" in sys.argv:
        tail = True

    tok = token()
    state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_bus_watermark.json")
    # Arbiter 5775473121 §3: do NOT rely on "the last N pages happen to be enough".  Persist the
    # watermark (id + its created_at) and page forward from `since=<created_at>` until an empty
    # page, then keep only id > watermark.  A day with 301 new comments can no longer hide one.
    per = 100
    since = None
    if os.path.isfile(state_path):
        try:
            with open(state_path, encoding="utf-8") as fh:
                st = json.load(fh)
            since = st.get("last_seen_created_at")
        except Exception:  # noqa: BLE001
            since = None

    seen: dict[int, dict] = {}
    page = 1
    pages_walked = 0
    while True:
        url = (f"https://api.github.com/repos/{repo}/issues/{ISSUE}/comments"
               f"?per_page={per}&page={page}&sort=created&direction=asc")
        if since:
            url += f"&since={since}"
        batch, _ = get(url, tok)
        pages_walked += 1
        if not batch:
            break
        for c in batch:
            seen[int(c["id"])] = c
        if len(batch) < per or pages_walked > 40:  # 40 pages = 4000 comments is a sane ceiling
            break
        page += 1

    newer = [c for cid, c in sorted(seen.items()) if cid > watermark]
    print(f"repo={repo} mode={'since-walk' if since else 'full-walk'} pages_walked={pages_walked} "
          f"per_page={per} cached={len(seen)} above_{watermark}={len(newer)}")
    if newer:
        try:
            with open(state_path, "w", encoding="utf-8", newline="\n") as fh:
                json.dump({"last_seen_id": max(seen), "last_seen_created_at": seen[max(seen)]["created_at"]},
                          fh, ensure_ascii=False, indent=2)
        except Exception:  # noqa: BLE001
            pass
    for c in newer:
        print("\n" + "=" * 72)
        print(f"id={c['id']} at={c['created_at']} user={c['user']['login']} len={len(c['body'])}")
        print(c["body"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
