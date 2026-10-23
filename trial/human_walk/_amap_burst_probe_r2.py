"""How long does the AMap concurrency refusal actually last?  Retry the same hop at staged pauses.

Why this decides a product constant: the freeze wants to retry a rate-limited hop once, and "once" is only
honest if the pause is long enough to help.  Measured here rather than guessed: burst the door to get the
refusal, then ask the same hop again after 1, 2, 3 and 5 seconds and record which answer comes back.

Writes the provider's own fields.  Never writes the key.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = os.environ.get("AMAP_WEB_KEY") or os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or ""
OUT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_cmdr_amap_burst-2.txt"
PAIR = {"origin": "116.403,39.911", "destination": "116.397,39.933"}  # 王府井 -> 故宫, an in-city hop
lines = []


def ask(label):
    query = dict(PAIR)
    query["key"] = KEY
    url = "https://restapi.amap.com/v5/direction/walking?" + urllib.parse.urlencode(query)
    try:
        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 - fixed host, key from env
            body = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - the point is to report what the door did
        return {"label": label, "transport_error": type(error).__name__}
    return {"label": label, "status": body.get("status"), "infocode": body.get("infocode"),
            "info": body.get("info"), "route_present": isinstance(body.get("route"), dict)}


lines.append("amap_key_present=%s run_at=%s pair=%s" % (
    bool(KEY), datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "王府井->故宫"))
if not KEY:
    lines.append("NO_KEY_IN_ENVIRONMENT -- nothing was asked, so nothing is concluded")
else:
    burst = [ask("burst_%02d" % i) for i in range(1, 7)]
    lines.append("BURST_6 " + json.dumps(burst, ensure_ascii=False))
    tripped = [row for row in burst if row.get("status") != "1"]
    if not tripped:
        lines.append("NO_REFUSAL_IN_BURST -- the staged retries below are not a recovery measurement")
    else:
        elapsed = 0
        for delta in (1, 2, 3, 5):
            time.sleep(delta)
            elapsed += delta
            row = ask("at_%ds" % elapsed)
            lines.append("RETRY_AT_%ds %s" % (elapsed, json.dumps(row, ensure_ascii=False)))
        lines.append("refused_in_burst=%d" % len(tripped))

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(lines) + "\n")
for line in lines:
    print(line[:900])
