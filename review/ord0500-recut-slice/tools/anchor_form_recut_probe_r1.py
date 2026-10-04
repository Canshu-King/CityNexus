"""Is the pending anchor-form hand still safe to land on the tip as it stands right now?

The cut replaces numeric `path:line` citations with name labels that live in `backend/app/main.py`.  A label
that no longer resolves -- or now resolves twice -- is not a cosmetic problem: the shipped comment would cite
a name the file does not contain, which is the defect this whole order exists to stop.  So the question is
asked with the order's own gate, fed the bytes that are actually on the published ref and the tip read at this
second, with nothing written anywhere.
"""
import json
import os
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
sys.path.insert(0, os.path.join(LANE, "tools"))
import anchor_form_gate_r26 as G
from anchor_form_apply_r26 import MANIFEST

REF = "refs/heads/review/newlane-ord0500-phone-anchor-form-r3"
AUDITED = "backend/tests/test_qoder_ord0500_journey_refusal.py"


def main():
    tip = G.live_tip()
    rc, out = G.git("ls-remote", "--refs", "origin", REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_REF_UNREADABLE " + REF)
    head = out.split()[0]
    rc2, blob = G.git("rev-parse", "%s:%s" % (head, AUDITED))
    if rc2:
        raise SystemExit("ABORT_AUDITED_PATH_MISSING " + blob[:120])
    body = G.blob_text(head, AUDITED)
    verdict, rows = G.judge(MANIFEST, tip, src=body)
    mainpy = G.blob_text(tip, "backend/app/main.py")
    out_rows = []
    for r in rows:
        out_rows.append({k: r.get(k) for k in ("check", "verdict", "label", "hits", "why")
                         if r.get(k) is not None})
    res = {"schema": "CNX_ANCHOR_FORM_RECUT_PROBE_V1", "tool": "anchor_form_recut_probe_r1",
           "live_tip": tip, "ref": REF, "ref_head": head, "audited_file": AUDITED,
           "shipped_blob": blob.strip(), "gate_verdict": verdict, "rows": out_rows,
           "mainpy_at_tip_len_bytes": len(mainpy), "worktree_written": False}
    dest = os.path.join(LANE, "evidence", "anchor_form_recut_probe_r1.json")
    json.dump(res, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({"live_tip": tip, "ref_head": head, "shipped_blob": blob.strip(),
                      "gate_verdict": verdict,
                      "rows": [(r.get("check"), r.get("verdict"), r.get("label"), r.get("hits"))
                               for r in rows]}, ensure_ascii=False, indent=1))
    print("WROTE " + dest)


if __name__ == "__main__":
    main()
