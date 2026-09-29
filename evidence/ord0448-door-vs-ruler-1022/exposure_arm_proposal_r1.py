"""The exposure arm ORD-0448's readings support, as a tested drop-in next to the door.

Why this is a neighbour file and not an edit to `preflight_and_land_r5.py`: the order authorised a
keying change *if* the path-cache hypothesis were confirmed. It was not (two runs identical, a planted
file wiped before the run), so the door's arithmetic stays exactly as the commander wrote it and I keep
0 product bytes plus 0 gate bytes. What the readings DO support is (a) a strictly more specific
comparison the door already has in hand and throws away, and (b) one number the receipt never printed.

Every run first re-verifies the pinned ruler with the door's own blob arithmetic (preflight_and_land_r5.py:138),
so an arm measured against a drifted ruler cannot be mistaken for the door's behaviour.

Verdicts reported for one tip/candidate pair:
  * `door_as_written`      - the door's own set-of-"file:line|rule" bucketing (the number it refuses on);
  * `by_cell_identity`     - per-`cell_id` COUNT growth, using the identity the r7b ruler emits;
  * `identity_set_only`    - the tempting weaker arm: does a NEW identity appear? Reported to show what it
                            would have let through, not offered as a gate;
  * `cells_already_on_the_line_in_touched_files` - what the commander asked and the receipt never said:
                            how many cells the tip ALREADY carries in the files this candidate edits.
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
DOOR = os.path.join(REF, "preflight_and_land_r5.py")
RULER = os.path.join(REF, "ui_exposure_taint_ast_r7b.cjs")
PINNED_BLOB = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"  # preflight_and_land_r5.py:43
REPO = "D:/moodle/CityNexus"
NUL = chr(0).encode()
KEYRX = re.compile(r"^(.+):(\d+)\|(.+)$")

TIP = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
R3 = "6c466ce267bf196827054584afeb3f533677fe7b"
R4 = "6336b0e4e1bab3ae17e4ce4b1a96e2696541ef56"
R4_LANDED = "527f471b6d009d8ef8fead5d32ad455005ac281b"


def blob_of(path):
    """Git blob id over the raw bytes -- the same arithmetic the door uses to pin the ruler."""
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest()


def _git(args):
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy="] + args,
                       capture_output=True, timeout=900,
                       env=dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*"))
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace")


def measure(rev, tag, fresh=False):
    """Cells the pinned ruler finds in `rev`:frontend/src, with the identity the door discards.

    Cached to cells_<tag>.json and reused only when the cached rev AND the cached ruler blob both match,
    because a number read off a substituted ruler is not the same measurement.
    """
    cache = os.path.join(WORK, "cells_%s.json" % tag)
    ruler_blob = blob_of(RULER)
    if ruler_blob != PINNED_BLOB:
        raise SystemExit("ruler identity drift: %s is blob %s, door pins %s" %
                         (os.path.basename(RULER), ruler_blob, PINNED_BLOB))
    if os.path.isfile(cache) and not fresh:
        doc = json.load(io.open(cache, encoding="utf-8"))
        if doc["rev"] == rev and doc["ruler_blob"] == ruler_blob:
            return doc
    scratch = os.path.join(WORK, "_exp_%s" % tag)
    if os.path.isdir(scratch):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", scratch], timeout=600)
    os.makedirs(scratch, exist_ok=True)
    rc, err = _git(["-C", REPO, "rev-parse", rev])
    assert rc == 0 and err.strip() == rev, "rev %s not in the repo: %s" % (rev[:12], err[:120])
    tar = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, rev, scratch),
                         shell=True, capture_output=True, timeout=900)
    assert tar.returncode == 0, (tar.stderr[:200], err[:200])
    js = os.path.join(scratch, "ruler.json")
    r = subprocess.run(["node", RULER, "--tree", os.path.join(scratch, "frontend", "src"),
                        "--out", js], capture_output=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert os.path.isfile(js), "ruler wrote no output rc=%s %s" % (r.returncode, r.stderr[:300])
    out = json.load(io.open(js, encoding="utf-8"))
    cells = []
    for h in out.get("hits", []):
        base = str(h["file"]).split("/")[-1]
        cells.append({"key": "%s:%s|%s" % (base, h["line"], h.get("rule")),
                      "id": h.get("cell_id"), "file": base, "line": h["line"],
                      "rule": h.get("rule"),
                      "sink_shape": (h.get("structural") or {}).get("sink_shape")})
    doc = {"rev": rev, "tag": tag, "ruler": os.path.basename(RULER), "ruler_blob": ruler_blob,
           "cells_total_reported": out.get("cells_total"), "cells": cells}
    io.open(cache, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    shutil_rmtree(scratch)
    return doc


def shutil_rmtree(path):
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path], timeout=600)


def bucket(keys):
    """The door's own bucketing (preflight_and_land_r5.py:109-115), reimplemented so both views share a source."""
    out = {}
    for key in keys:
        m = KEYRX.match(key)
        k = "%s|%s" % (m.group(1), m.group(3)) if m else key
        out[k] = out.get(k, 0) + 1
    return out


def counted(seq):
    out = {}
    for x in seq:
        out[x] = out.get(x, 0) + 1
    return out


def grow(base, cand):
    return {k: cand[k] - base.get(k, 0) for k in cand if cand[k] > base.get(k, 0)}


def touched_files(tip_rev, cand_rev):
    rc, so = _git(["-C", REPO, "diff", "--name-only", tip_rev, cand_rev])
    assert rc == 0, so[:200]
    return sorted({os.path.basename(ln) for ln in so.splitlines() if ln.strip()})


def verdict(tip_cells, cand_cells, touched):
    tk = [c["key"] for c in tip_cells]
    ck = [c["key"] for c in cand_cells]
    ti = [c["id"] for c in tip_cells]
    ci = [c["id"] for c in cand_cells]
    door_growth = grow(bucket(set(tk)), bucket(set(ck)))
    id_growth = grow(counted(ti), counted(ci))
    set_growth = sorted({c["id"] for c in cand_cells} - {c["id"] for c in tip_cells})
    return {
        "door_as_written_growth_by_file_and_rule": door_growth,
        "door_as_written_refused": bool(door_growth),
        "by_cell_identity_count_growth": id_growth,
        "by_cell_identity_refused": bool(id_growth),
        "identity_set_only_new_ids": set_growth,
        "identity_set_only_refused": bool(set_growth),
        "cells_already_on_the_line_in_touched_files":
            {f: len([c for c in tip_cells if c["file"] == f]) for f in touched},
        "candidate_touched_files": touched,
    }


def selftest(tip, r3, r4):
    """Four arms on the real pair plus two injected shapes; each must land on its expected verdict."""
    arms = []
    v3 = verdict(tip["cells"], r3["cells"], touched_files(TIP, R3))
    v4 = verdict(tip["cells"], r4["cells"], touched_files(TIP, R4))
    arms.append(("S1_r3_refused_by_both_strong_views",
                 v3["door_as_written_refused"] and v3["by_cell_identity_refused"], v3))
    arms.append(("S2_r4_not_refused_by_either_and_names_preexisting",
                 (not v4["door_as_written_refused"]) and (not v4["by_cell_identity_refused"])
                 and v4["cells_already_on_the_line_in_touched_files"].get(
                     "DestinationPreparationPanel.tsx", 0) >= 3, v4))
    arms.append(("S3_identity_set_arm_would_have_let_r3_through",
                 v3["identity_set_only_refused"] is False, v3))
    shifted = [dict(c, key=KEYRX.sub(lambda m: "%s:9%s|%s" % (m.group(1), m.group(2), m.group(3)),
                                     c["key"])) for c in tip["cells"]]
    vs = verdict(tip["cells"], shifted, touched_files(TIP, R4))
    arms.append(("S4_pure_line_shift_free_under_both",
                 not vs["door_as_written_refused"] and not vs["by_cell_identity_refused"], vs))
    dup = list(tip["cells"])
    c0 = dict(dup[0])
    c0["line"] = int(c0["line"]) + 10
    c0["key"] = "%s:%s|%s" % (c0["file"], c0["line"], c0["rule"])
    dup.append(c0)
    vd = verdict(tip["cells"], dup, touched_files(TIP, R4))
    arms.append(("S5_same_sink_rendered_twice_caught_by_both",
                 vd["door_as_written_refused"] and vd["by_cell_identity_refused"], vd))
    # the claim this arm file rests on: the scratch export is gone once the measurement is done,
    # so no later run can read a directory the earlier run left behind.
    leftovers = sorted(os.path.basename(p) for p in glob.glob(os.path.join(WORK, "_exp_*")))
    arms.append(("S6_no_scratch_export_survives_a_run", leftovers == [], {"dirs_matching_exp_star": leftovers}))
    ok = all(bool(p) for _n, p, _d in arms)
    return {"arms": [{"arm": n, "pass": bool(p), "detail": d} for n, p, d in arms],
            "ruler_blob": PINNED_BLOB,
            "tip_cells_total": tip["cells_total_reported"],
            "verdict": "SELFTEST_PASS" if ok else "SELFTEST_FAIL"}


def main():
    tip = measure(TIP, "tip")
    r3 = measure(R3, "r3")
    r4 = measure(R4, "r4")
    real = {"tip_rev": TIP, "r3_rev": R3, "r4_rev": R4,
            "r3_vs_tip": verdict(tip["cells"], r3["cells"], touched_files(TIP, R3)),
            "r4_vs_tip": verdict(tip["cells"], r4["cells"], touched_files(TIP, R4))}
    io.open(os.path.join(WORK, "arm_verdicts_real_pair.json"), "w", encoding="utf-8").write(
        json.dumps(real, ensure_ascii=False, indent=1))
    st = selftest(tip, r3, r4)
    io.open(os.path.join(WORK, "arm_selftest.json"), "w", encoding="utf-8").write(
        json.dumps(st, ensure_ascii=False, indent=1))
    for a in st["arms"]:
        print("%-46s %s" % (a["arm"], "PASS" if a["pass"] else "FAIL"))
    print(st["verdict"], "| tip cells_total", st["tip_cells_total"])
    print(json.dumps(real, ensure_ascii=False, indent=1)[:1400])
    return 0 if st["verdict"] == "SELFTEST_PASS" else 7


if __name__ == "__main__":
    sys.exit(main())
