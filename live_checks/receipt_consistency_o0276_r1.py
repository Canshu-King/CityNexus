"""Recompute HJ-P3's ORD-0276 derived cells from the raw readings in its own receipt (14 arms).

Why: the receipt's `derived` block is what the verdict is written in, and `pages`/`store` are the raw
readings.  A cell is only worth signing if the declared field equals the value the raw readings give.
This does not judge whether the product is right - it judges whether this receipt's numbers are its
own.  r1 is the corrected version of a first pass that reported 11/12: three of my arms used key names
that do not exist in the artifact (`row_count`, `cursor`, `since`); the artifact uses
`rows_for_journey`, `cursor_x`, `since_newest`.  The judge was right, my probes were wrong, so the fix
here is to the checker, and the honest record is 11/12-then-14/14 with the three wrong keys named.

Usage: python receipt_consistency_o0276_r1.py [--path <local copy of the receipt>]
Exit 0 = all arms agree, 1 = at least one disagreement, 2 = the artifact itself is unreadable.
"""
import argparse
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BLOB = "3ec966e90bc14f20955ef3d10936a9ce5ca17f6b"   # evidence/ord0276-hjp3-cells/O0276-2505_readings.json


def arms(d):
    P, S, D, C = d["pages"], d["store"], d["derived"], d["client_derivation"]
    c1, c2, c3 = D["C1_ascending_truncation"], D["C2_pagination_readback"], D["C3_named_failure"]
    df = P["default"]
    eq = lambda name, a, b: (name, a == b, a, b)
    return [
        eq("A01 C1.returned_default == pages.default.events", c1["returned_default"], df["events"]),
        eq("A02 C1.returned_at_documented_max == pages.limit_200.events",
           c1["returned_at_documented_max"], P["limit_200"]["events"]),
        eq("A03 C1.rows_in_store == store.rows_for_journey", c1["rows_in_store"], S["rows_for_journey"]),
        eq("A04 C1.target_is_newest_row == store.newest_row_is_the_target",
           c1["target_is_newest_row"], S["newest_row_is_the_target"]),
        eq("A05 C1.target_present_in_store == store.target_present_in_store",
           c1["target_present_in_store"], S["target_present_in_store"]),
        eq("A06 newest row IS the target the pages cannot reach (rank == rows)",
           S["newest_row_is_the_target"], S["target_rank_from_oldest"] == S["rows_for_journey"]),
        eq("A07 C1.target_in_default_page == pages.default.target_in_page",
           c1["target_in_default_page"], df["target_in_page"]),
        eq("A08 C1.target_in_max_page == pages.limit_200.target_in_page",
           c1["target_in_max_page"], P["limit_200"]["target_in_page"]),
        eq("A09 C1.ordering_is_ascending == (default.first_event_id == limit_200.first_event_id)",
           c1["ordering_is_ascending_oldest_first"], df["first_event_id"] == P["limit_200"]["first_event_id"]),
        eq("A10 C2.limit_201_http == pages.limit_201.http", c2["limit_201_http"], P["limit_201"]["http"]),
        eq("A11 C2 undocumented params all return the default body (sha256)",
           [c2["offset_100_body_equals_default"], c2["cursor_body_equals_default"],
            c2["since_body_equals_default"], c2["page_2_body_equals_default"]],
           [P[k]["body_sha256"] == df["body_sha256"] for k in ("offset_100", "cursor_x", "since_newest", "page_2")]),
        eq("A12 POSITIVE CONTROL: limit=1 is honoured (so A11 is not 'every request is identical')",
           P["limit_1"]["events"] == 1 and P["limit_1"]["body_sha256"] != df["body_sha256"], True),
        eq("A13 C3.payload_top_level_keys == pages.default.top_level_keys",
           c3["payload_top_level_keys"], df["top_level_keys"]),
        eq("A14 C3 store-vs-page conclusion == client_derivation (found/null)",
           (c3["same_derivation_on_the_store"], c3["client_derivation_on_default_page"]),
           (C["store"], C["default"])),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="_incoming_o276.json")
    a = ap.parse_args()
    try:
        d = json.load(open(a.path, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print("ARTIFACT_UNREADABLE", type(exc).__name__, str(exc)[:120])
        return 2
    print(f"receipt: evidence/ord0276-hjp3-cells/O0276-2505_readings.json  blob {BLOB}")
    print(f"tree in receipt: {d.get('tree')}  run_id: {d.get('run_id')}")
    bad = 0
    for name, ok, got, wantv in arms(d):
        bad += 0 if ok else 1
        print(f"{'GREEN' if ok else 'RED  '}  {name}")
        if not ok:
            print(f"        declared-side {str(got)[:120]}  !=  raw-side {str(wantv)[:120]}")
    print(f"\narms={len(arms(d))} disagreements={bad}")
    print("INTERNAL_CONSISTENCY " + ("ALL_AGREE" if bad == 0 else "MISMATCH"))
    # what this does NOT prove
    print("SCOPE: recomputation inside one artifact only. It does not re-run the HTTP probes, "
          "does not confirm the store numbers came from the named db, and signs no product verdict "
          "(visibility verdict stays NO_PIXEL_READING as the lane itself wrote).")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
