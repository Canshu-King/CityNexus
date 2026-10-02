"""Lane state + the commander's canary trip, read back after the reboot -- one file, so the block's last
section cites an artifact instead of prose.

Nothing here starts or stops a process: netstat is a read, the two doors are GETs. The lane's own eight
private listeners (:4985-:4988 front, :8780-:8783 api) were started before the reboot; whether they survived
is measured, not assumed.

`undelete` is a POST that writes to the commander's verification asset, so it is named and NOT pressed.
"""
import io
import json
import re
import subprocess
import time
import urllib.request

EVIDENCE = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/ord0500-r6-rebase-preview/receipts"
OUT = "%s/lane_state_and_canary_r1.json" % EVIDENCE
LANE_PORTS = [4985, 4986, 4987, 4988, 8780, 8781, 8782, 8783]
CMDR_PORTS = [4783, 4787]
CANARY_ID = "22222222-2222-4222-8222-222222222222"


def netstat_rows():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stdout
    rows = []
    for line in out.splitlines():
        if "LISTENING" not in line:
            continue
        match = re.search(r":(\d+)\s+\S+\s+LISTENING\s+(\d+)", line)
        if match:
            rows.append({"port": int(match.group(1)), "pid": int(match.group(2)), "raw": line.strip()})
    return rows


def get(url):
    request = urllib.request.Request(url, headers={"NO_PROXY": "*"})
    with urllib.request.urlopen(request, timeout=25) as response:
        body = response.read()
    return {"http_status": response.status, "bytes": len(body), "content_type":
            response.headers.get("content-type"), "json": json.loads(body.decode("utf-8"))}


def main():
    rows = netstat_rows()
    listening = sorted({r["port"] for r in rows})
    lane_up = [p for p in LANE_PORTS if p in listening]
    cmdr_up = [p for p in CMDR_PORTS if p in listening]

    rb = get("http://127.0.0.1:4787/api/v1/recycle-bin/journeys")
    rows_list = rb["json"] if isinstance(rb["json"], list) else (
        rb["json"].get("items") or rb["json"].get("journeys") or [])
    canary = [r for r in rows_list if CANARY_ID in json.dumps(r)]
    sc = get("http://127.0.0.1:4787/api/v1/demo/scene")

    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "how_read": "netstat -ano filtered on LISTENING; two GETs against 127.0.0.1:4787, no POST, no auth",
        "lane_ports_checked": LANE_PORTS,
        "lane_ports_still_listening": lane_up,
        "lane_ports_gone": [p for p in LANE_PORTS if p not in lane_up],
        "commander_ports_listening": [{"port": p, "pid": [r["pid"] for r in rows if r["port"] == p]}
                                      for p in cmdr_up],
        "recycle_bin_journeys": {"http_status": rb["http_status"], "bytes": rb["bytes"],
                                 "rows": len(rows_list),
                                 "canary_rows": canary, "canary_hits": len(canary)},
        "demo_scene": {"http_status": sc["http_status"], "bytes": sc["bytes"],
                       "journey_id": sc["json"].get("journey_id"),
                       "journey_status": sc["json"].get("journey_status"),
                       "evidence_state": sc["json"].get("evidence_state"),
                       "demo_mode": sc["json"].get("demo_mode")},
        "undelete_door": "NAMED_NOT_PRESSED: POST /api/v1/journeys/{id}/undelete writes to the "
                         "commander's verification asset; pressing it is his call, not the lane's",
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    print("lane_listening=%s gone=%s commander=%s" % (lane_up, body["lane_ports_gone"], cmdr_up))
    print("recycle http_status=%s rows=%d canary_hits=%d deleted_at=%s"
          % (rb["http_status"], len(rows_list), len(canary),
             canary[0].get("deleted_at") if canary else "-"))
    print("scene http_status=%s journey_status=%s evidence_state=%s"
          % (sc["http_status"], sc["json"].get("journey_status"), sc["json"].get("evidence_state")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
