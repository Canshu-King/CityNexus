"""Inventory: which session ids have appeared in ledger block headers that call themselves "车道 Q" / "lane Q"?

This is the recurring name<->id collision, counted instead of asserted. Read-only: it only reads first lines of
already-inserted blocks and the current ledger. Output feeds a bus post so the commander can pin one id per name.
"""
import collections
import glob
import io
import json
import os
import re
import time

INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROC = os.path.join(INBOX, "_processed")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
ID_PAT = re.compile(r"\b[0-9a-f]{8}\b")
HERE = os.path.dirname(os.path.abspath(__file__))
sys_path = None


def headers(path):
    try:
        first = io.open(path, encoding="utf-8", errors="replace").read().splitlines()[0]
    except Exception:
        return None
    return first.strip() if first.startswith("### ") else None


def main():
    # 只有能对上会话表的 8 位串才算「车道 id」；形如 0598e4d1 的短 sha 与 id 同形，按形状分不出来，
    # 所以拿 patrol/wake_names.py 的 ID8 当唯一花名册，对不上的单独列成「非表内 8 位串」。
    import sys
    sys.path.insert(0, HERE)
    import wake_names as WN
    roster = set(WN.ID8)
    pat = re.compile(r"车道 Q|（lane Q\)|\(lane Q\)|· lane Q")
    by_name = collections.defaultdict(collections.Counter)
    offroster = collections.Counter()
    files = 0
    for p in glob.glob(os.path.join(PROC, "*")):
        h = headers(p)
        if not h:
            continue
        files += 1
        if pat.search(h):
            ids = ID_PAT.findall(h)
            for i in ids:
                if i in roster:
                    by_name["Q"][i] += 1
                else:
                    offroster[i] += 1
            if not ids:
                by_name["Q"]["(块头无 id)"] += 1
    # and the live ledger, same measure
    live = collections.Counter()
    live_off = collections.Counter()
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
    for l in lines:
        if l.startswith("### ") and pat.search(l):
            for i in ID_PAT.findall(l):
                (live if i in roster else live_off)[i] += 1
            if not ID_PAT.findall(l):
                live["(块头无 id)"] += 1
    out = {"blocks_scanned": files,
           "ids_claiming_Q_in_processed": dict(by_name["Q"]),
           "non_roster_8hex_in_those_headers": dict(offroster),
           "ids_claiming_Q_in_live_ledger": dict(live),
           "roster_names_of_those_ids": {k: WN.ID8.get(k) for k in by_name["Q"]},
           "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    io.open(os.path.join(HERE, "q_name_inventory.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print("blocks scanned=%d  roster=%d ids" % (files, len(roster)))
    print("在自称「车道 Q / lane Q」的块头里，出现过的在册会话 id：")
    for k, v in sorted(by_name["Q"].items(), key=lambda x: -x[1]):
        print("   %-14s %-12s %d 次" % (k, WN.ID8.get(k, "?"), v))
    print("同批块头里对不上花名册的 8 位串（多半是短 sha，不是 id）：%s" % dict(offroster))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
