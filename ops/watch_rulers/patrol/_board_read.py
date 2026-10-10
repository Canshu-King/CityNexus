"""Compact project-progress readout from the state-board artifact (computed, not transcribed)."""
import collections
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.loads(io.open(os.path.join(HERE, "state_board_2020.json"), encoding="utf-8").read())
print("tool=%s ledger_blob=%s at=%s blocks_scanned=%d orders_seen=%d" % (
    d["tool"], d["ledger_blob"][:12], d.get("at_local"), d["blocks_scanned"], d["orders_seen"]))
po = d["per_order"]
cnt = collections.Counter(v.get("latest_status") for v in po.values())
print("latest_status counts:")
for k, n in cnt.most_common():
    print("   %-26s %d" % (k, n))
own = collections.Counter(v.get("owner_lane") for v in po.values())
print("owner_lane distinct=%d  top=%s" % (len(own), own.most_common(6)))

nums = sorted((int(k.split("-")[1]), k, v) for k, v in po.items())
print("\n从 ORD-%04d 到 ORD-%04d；最后 18 条按账本原话：" % (nums[0][0], nums[-1][0]))
for n, k, v in nums[-18:]:
    ev = v.get("evidence_blobs")
    ev = ev[:14] + "…" if isinstance(ev, str) and len(ev) > 14 else ev
    print("   %-10s %-16s owner=%-14s as_of=%-16s line=%s ev=%s" % (
        k, v.get("latest_status"), str(v.get("owner_lane"))[:14], str(v.get("as_of"))[:16],
        v.get("_status_source_line"), ev))
todo = [(k, v.get("latest_status")) for n, k, v in nums if v.get("latest_status") not in ("CLOSED", "DELIVERED", None)
        and n >= 380]
print("\n380 号以后仍未收口的条数=%d：%s" % (len(todo), todo))
