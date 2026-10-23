"""Burst the AMap walking door to catch the raw infocode the product's own receipt throws away.

Why: at 18:14 the running stack asked five hops inside 200 ms; four answered, one came back
AMAP_QUOTA_EXCEEDED, and the card told the traveller 「地图服务今天的查询次数已经用完」.  The stored receipt
keeps only the mapped reason code (backend/app/agent/goal_amap.py:36), so nothing on hand can say whether
that was a daily limit or a per-second one -- and the two need different words and different fixes.

Writes the provider's own fields verbatim.  Never writes the key.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = os.environ.get("AMAP_WEB_KEY") or os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or ""
OUT = sys.argv[1] if len(sys.argv) > 1 else "D:/moodle/_cmdr_amap_burst-1.txt"
# A short city pair that answered OK at 15:34 (故宫 -> 景山), so a refusal here can only be the door, not the pair.
PAIR = {"origin": "116.397,39.919", "destination": "116.397,39.933"}
lines = []


def ask(label):
    query = dict(PAIR)
    query["key"] = KEY
    url = "https://restapi.amap.com/v5/direction/walking?" + urllib.parse.urlencode(query)
    started = time.time()
    try:
        with urllib.request.urlopen(url, timeout=15) as response:  # noqa: S310 - fixed host, key from env
            body = json.loads(response.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - the point is to report what the door did
        return {"label": label, "transport_error": type(error).__name__}
    return {"label": label, "t_ms": round((time.time() - started) * 1000),
            "status": body.get("status"), "infocode": body.get("infocode"), "info": body.get("info"),
            "route_present": isinstance(body.get("route"), dict)}


lines.append("amap_key_present=%s run_at=%s pair=%s" % (
    bool(KEY), datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"), "故宫->景山"))
if not KEY:
    lines.append("NO_KEY_IN_ENVIRONMENT -- nothing was asked, so nothing is concluded")
else:
    burst = [ask("burst_%02d" % i) for i in range(1, 9)]
    lines.append("BURST_8_NO_DELAY " + json.dumps(burst, ensure_ascii=False))
    time.sleep(4)
    lines.append("AFTER_4S_PAUSE " + json.dumps([ask("after_pause")], ensure_ascii=False))
    codes = sorted({str(row.get("infocode")) for row in burst})
    lines.append("burst_infocodes=%s refused=%d" % (",".join(codes), sum(1 for row in burst if row.get("status") != "1")))

with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(lines) + "\n")
for line in lines:
    print(line[:900])
