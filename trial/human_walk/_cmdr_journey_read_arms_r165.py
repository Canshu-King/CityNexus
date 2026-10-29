"""Measure whether a bare journey id still opens a private journey on the live canary stack.

The open observation (#333) said an unauthenticated GET on /api/v1/journeys/{id} answered 200.  That
claim has a generation.  This instrument re-measures it on whatever the tip stack is serving right
now, with three credential arms, and writes the statuses to a tracked receipt.  It only reads.
"""

import io
import json
import sqlite3
import sys
import urllib.error
import urllib.request

STACK = "http://127.0.0.1:60364/api/v1/journeys/"
TIP_DB = "E:/_cmdr_tip_113_data/citynexus_v3_rescue_113.db"
RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bv165-journey-read-arms.txt"


def pick_journey():
    connection = sqlite3.connect("file:%s?mode=ro" % TIP_DB, uri=True)
    try:
        row = connection.execute(
            "select id, status from journeys order by rowid desc limit 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise SystemExit("ABORT the tip canary database has no journey row to read")
    return str(row[0]), str(row[1])


def arm(opener, url, headers):
    request = urllib.request.Request(url, headers=headers)
    try:
        with opener.open(request, timeout=10) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            keys = sorted(body.keys()) if isinstance(body, dict) else ["<not-an-object>"]
            return {
                "status": response.status,
                "top_key_count": len(keys),
                "carries_title": "title" in keys,
                "carries_traveler_id": "traveler_id" in keys,
            }
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "body_head": exc.read().decode("utf-8", "replace")[:90].replace("\n", " ")}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    journey_id, journey_status = pick_journey()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    arms = [
        ("no credential", {}),
        ("bogus bearer", {"Authorization": "Bearer not-a-real-token-bv165"}),
        ("sixty-four-zero bearer", {"Authorization": "Bearer " + "0" * 64}),
    ]
    lines = [
        "PRIVATE JOURNEY READ ARMS bv165 (read-only)",
        "STACK %s" % STACK,
        "JOURNEY %s db_status=%s" % (journey_id, journey_status),
    ]
    for label, headers in arms:
        result = arm(opener, STACK + journey_id, headers)
        lines.append("ARM %s -> %s" % (label, json.dumps(result, ensure_ascii=False)))
    statuses = [json.loads(line.split("-> ", 1)[1])["status"] for line in lines if line.startswith("ARM ")]
    lines.append("ALL_ARMS_401 %s" % all(code == 401 for code in statuses))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
