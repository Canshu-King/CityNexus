"""Fold the recycle-bin real-door readings into one receipt and prove the store was left as it was found.

The two arms each withdraw and restore through the product's own doors, so the honest closing question is
not "did the sentence paint" (that is in the arm files) but "is this lane's store back where it started".
This reads the doors again -- recycle-bin list, the trip itself, the footprint rows -- and compares against
the baseline recorded before anything was touched.
"""
import io
import json
import time
import urllib.request

EVID = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend/review/journey-in-bin-real-door"
OUT = "%s/receipts/journey_in_bin_summary_r1.json" % EVID
API = 8795


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "e766b154-journeyinbin-summary-r1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main():
    own = json.load(io.open("%s/receipts/journey_in_bin_ownership_r1.json" % EVID, encoding="utf-8"))
    journey = own["scene_journey_id"]
    rows = []
    for name in ("b-zh-CN", "b-en"):
        body = json.load(io.open("%s/readings/%s.json" % (EVID, name), encoding="utf-8"))
        rows.append({
            "file": "readings/%s.json" % name, "locale": body["locale"], "verdict": body["verdict"],
            "withdraw_status": body["delete_door_status"], "in_bin_after_withdrawal":
                body["door_after_delete"]["journey_in_bin"],
            "read_door_while_binned": body["door_after_delete"]["read_journey_status"],
            "stops_mounted": body["screen"]["stops"], "controls_mounted": body["screen"]["controls"],
            "tapped_stop": body["tapped_stop"], "door_status": body["post_answer"]["status"],
            "door_reason_code": body["post_answer"]["reason_code"],
            "door_message": body["post_answer"]["message"],
            "painted_notice": body["painted_notice"],
            "painted_equals_table_row": body["checks"]["sentence_painted_equals_the_tables_own_row"],
            "notices_count": body["notices_count"], "uuid_on_glass":
                not body["checks"]["no_uuid_reached_the_travellers_sentence"],
            "undelete_status": body["undelete_door_status"],
            "checks_failed": sorted(k for k, v in body["checks"].items()
                                    if v is False and k != "read_door_refuses_the_withdrawn_trip"),
        })
    read_status, _ = get("http://127.0.0.1:%d/api/v1/journeys/%s" % (API, journey))
    bin_status, bin_rows = get("http://127.0.0.1:%d/api/v1/recycle-bin/journeys" % API)
    stamp_status, stamps = get("http://127.0.0.1:%d/api/v1/journeys/%s/checkins" % (API, journey))
    body = {
        "taken_at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "measured_generation": own["built_from_sha"], "front": own["front"], "api": own["api"],
        "entry_asset": own["entry_asset"], "entry_served_bytes": own["entry_served_bytes"],
        "entry_served_sha1": own["entry_served_sha1"], "every_proof": own["every_proof"],
        "arms": rows,
        "arms_reached": len([r for r in rows if r["verdict"] == "REACHED"]),
        "painted_equals_table_rows": len([r for r in rows if r["painted_equals_table_row"]]),
        "door_named_the_code_times": len([r for r in rows
                                          if r["door_reason_code"] == "CHECKIN_JOURNEY_IN_RECYCLE_BIN"]),
        "store_after_the_run": {
            "file": "run/day31_bin_probe.db", "marker_city": own["marker_city"],
            "read_journey_status": read_status, "recycle_bin_status": bin_status,
            "recycle_bin_rows": len(bin_rows), "journey_in_bin": any(
                r.get("id") == journey for r in bin_rows),
            "checkin_rows": len(stamps),
            "baseline_recycle_bin_rows": own["baseline_recycle_bin_rows"],
            "baseline_read_journey_status": own["baseline_read_journey_status"],
            "back_to_baseline": read_status == own["baseline_read_journey_status"]
            and len(bin_rows) == own["baseline_recycle_bin_rows"] and len(stamps) == 0,
        },
        "product_facts_measured_not_claimed": {
            "read_door_still_answers_while_binned": all(r["read_door_while_binned"] == 200 for r in rows),
            "itinerary_still_mounts_stops_while_binned": all(r["stops_mounted"] > 0 for r in rows),
            "server_message_carries_a_cjk_word_in_english_prose": all(
                "找回" in (r["door_message"] or "") for r in rows),
        },
    }
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(body, handle, indent=1, ensure_ascii=False)
    printable = json.dumps({k: v for k, v in body.items() if k != "arms"}, ensure_ascii=False, indent=1)
    print(printable.encode("ascii", "replace").decode("ascii")[:1400])
    print("WROTE %s bytes=%d" % (OUT, len(json.dumps(body, ensure_ascii=False).encode("utf-8"))))
    return 0 if (body["arms_reached"] == 2 and body["store_after_the_run"]["back_to_baseline"]) else 3


if __name__ == "__main__":
    raise SystemExit(main())
