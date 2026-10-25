"""What an anonymous caller can read from one journey, as facts for a daylight ruling."""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

API = "http://127.0.0.1:60391"
JOURNEY = "2e9cd67d-10ca-4ecd-920b-76c81a350c71"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/anon-journey-read-1.txt"
lines: list[str] = []


def note(v: str) -> None:
    lines.append(v)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")


def get(path: str, token: str | None = None) -> tuple[int, dict | list | None]:
    request = urllib.request.Request(API + path)
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=15) as answer:
            raw = answer.read().decode("utf-8", "replace")
            try:
                return answer.status, json.loads(raw)
            except ValueError:
                return answer.status, None
    except urllib.error.HTTPError as error:
        return error.code, None
    except Exception:  # noqa: BLE001
        return 0, None


paths = [
    f"/api/v1/journeys/{JOURNEY}",
    f"/api/v1/journeys/{JOURNEY}/plans",
    f"/api/v1/journeys/{JOURNEY}/events",
    f"/api/v1/journeys/{JOURNEY}/members/me",
    f"/api/v1/journeys/{JOURNEY}/twin",
    f"/api/v1/journeys/{JOURNEY}/experience",
]
for path in paths:
    status, body = get(path)
    kind = type(body).__name__ if body is not None else "none"
    keys = sorted(body.keys()) if isinstance(body, dict) else []
    count = len(body) if isinstance(body, list) else None
    note("ANON %-55s http_status=%s type=%s keys=%s count=%s" % (path, status, kind, json.dumps(keys, ensure_ascii=False), count))

status, body = get(f"/api/v1/journeys/{JOURNEY}", token="not.a.valid.token")
note("BAD_TOKEN journey http_status=%s" % status)
note("VERDICT " + json.dumps({
    "journey_anonymous": get(f"/api/v1/journeys/{JOURNEY}")[0],
    "plans_anonymous": get(f"/api/v1/journeys/{JOURNEY}/plans")[0],
    "experience_anonymous": get(f"/api/v1/journeys/{JOURNEY}/experience")[0],
}, ensure_ascii=False))
