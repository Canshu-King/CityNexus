"""Two-way proof for the landing gate's new EXPOSURE NO-GROW arm.

Arm semantics being tested: a candidate may REMOVE Q64 cells, must not ADD one.  So the proof needs
both a case that must stay silent and a case that must speak, and the speaking case must be a real
re-growth of a shape the line already banned (an exception sentence in `data-*`, i.e. the exact Q71
defect ORD-0339 removed), not a made-up string.

Nothing is pushed and no work tree is touched: the poisoned commit is built with `hash-object` +
`read-tree`/`update-index` in a throwaway index, so it exists only as a local dangling object.

  python cmdr_exposure_arm_selftest_r1.py [--out FILE]
"""
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "D:/moodle/CityNexus"
LINE = "origin/mirror/integration-frontend-apple-pass1"
VICTIM = "frontend/src/components/ProductErrorBoundary.tsx"
# The regression to plant is a real one the line already banned: the pre-ORD-0323 version of this file put
# the reply's sentence into JSX text and into the 原因编号 slot -- cells the AST ruler does report.  I
# deliberately do NOT use a data-* attribute as the poison
# The planted file is one where the tip holds NO cells, so a reintroduced sink grows the count and
# cannot be mistaken for a line shift (PlanWithAiSheet would have: same rule, same count, moved lines).: this run measured that r6 cannot see attribute
# positions at all, so that fixture would prove nothing about the arm's teeth (see the blind-spot probe).
OLD_SHAPES = "09dffbb70c151e6734221d6d3d69d88775a1fbd0"
sys.path.insert(0, HERE)


def git_bin(*args, **kw):
    env = dict(os.environ)
    if kw.get("idx"):
        env["GIT_INDEX_FILE"] = kw["idx"]
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, timeout=300, env=env,
                       input=kw.get("data"))
    if p.returncode:
        raise SystemExit("git %s rc %d: %s" % (" ".join(args[:2]), p.returncode,
                                               p.stderr.decode("utf-8", "replace")[:300]))
    return p.stdout.decode("utf-8", "replace").strip()


def poison_commit(tip):
    """Put back a shape the authoritative line has already banned, and which the ruler CAN see.

    The first version of this fixture planted the Q71 defect (an exception sentence into
    `data-error-message`) and the ruler counted NOTHING -- that is a finding about the instrument, not
    about this fixture: r6 reads text positions, not attribute positions (see the DISCOVERY note).  So the
    poison here is the pre-ORD-0323 `PlanWithAiSheet.tsx`, whose `{copy.body}` /
    `{result.failureReason.text}` are cells the ruler does report and which ORD-0323 removed.
    """
    def show(rev):
        return subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, VICTIM)],
                              capture_output=True, timeout=300).stdout
    raw, old = show(tip), show(OLD_SHAPES)
    if not old:
        raise SystemExit("FIXTURE BROKEN: no %s:%s to plant" % (OLD_SHAPES[:12], VICTIM))
    if raw == old:
        raise SystemExit("VACUOUS FIXTURE: the pre-ORD-0323 file is identical to the tip's")
    new = old
    blob = git_bin("hash-object", "-w", "--stdin", data=new)
    if blob == git_bin("rev-parse", "%s:%s" % (tip, VICTIM)):
        raise SystemExit("VACUOUS FIXTURE: hash-object returned the pre-existing blob")
    idx = os.path.join(tempfile.mkdtemp(prefix="cnx_exp_arm_"), "idx")
    git_bin("read-tree", tip, idx=idx)
    git_bin("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, VICTIM), idx=idx)
    tree = git_bin("write-tree", idx=idx)
    return git_bin("commit-tree", tree, "-p", tip,
                   "-m", "SELFTEST poison: exception sentence back into data-* (Q71)"), tree, blob


def attribute_blind_spot(tip, cells_tip, exposure_cells):
    """Measure the instrument's known hole, so it is a stated limit and not a silent one.

    ORD-0339 removed a reply's sentence from `data-error-name` / `data-error-message` because Q71 says an
    attribute is in the DOM.  Planting that same violation back here shows whether the AST ruler can see
    it: if the cell count does not move, Q71 is enforced ONLY by the per-order e2e witnesses, and any
    "no new cells" verdict from my door must be read with that sentence attached.
    """
    victim = "frontend/src/features/setup/JourneyTrialSetup.tsx"
    raw = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (tip, victim)],
                         capture_output=True, timeout=300).stdout
    if b"data-error-message=" in raw:
        return {"status": "FIXTURE_UNUSABLE_TIP_ALREADY_HAS_IT"}
    anchor = b'          role="alert"\n'
    if raw.count(anchor) != 1:
        return {"status": "FIXTURE_UNUSABLE_ANCHOR_COUNT_%d" % raw.count(anchor)}
    blob = git_bin("hash-object", "-w", "--stdin",
                   data=raw.replace(anchor, anchor + b'          data-error-message={sealedDemoDetail?.message ?? ""}\n'))
    idx = os.path.join(tempfile.mkdtemp(prefix="cnx_exp_bs_"), "idx")
    git_bin("read-tree", tip, idx=idx)
    git_bin("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, victim), idx=idx)
    commit = git_bin("commit-tree", git_bin("write-tree", idx=idx), "-p", tip,
                     "-m", "SELFTEST blind-spot probe: exception sentence into data-error-message")
    cells = exposure_cells(commit, "expst_blind")
    return {"status": "MEASURED", "commit": commit, "cells_before": len(cells_tip),
            "cells_after": len(cells), "added": sorted(cells - cells_tip),
            "ruler_can_see_attribute_position": bool(cells - cells_tip)}


def shift_commit(tip):
    """A fixture that must NOT be refused: an older copy of a file whose cells are the SAME rule and the
    SAME count as the tip's, only at different line numbers (ORD-0323 shortened the file by two lines).
    Refusing this would teach lanes that touching any file above a flagged sink is forbidden."""
    victim = "frontend/src/features/planning/PlanWithAiSheet.tsx"
    show = lambda rev: subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (rev, victim)],
                                       capture_output=True, timeout=300).stdout
    raw, old = show(tip), show(OLD_SHAPES)
    if not old or raw == old:
        return None
    blob = git_bin("hash-object", "-w", "--stdin", data=old)
    idx = os.path.join(tempfile.mkdtemp(prefix="cnx_exp_shift_"), "idx")
    git_bin("read-tree", tip, idx=idx)
    git_bin("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, victim), idx=idx)
    return git_bin("commit-tree", git_bin("write-tree", idx=idx), "-p", tip,
                   "-m", "SELFTEST shift-only: same cells, moved lines")


def main():
    out_path = ""
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    import importlib
    gate = importlib.import_module("preflight_and_land_r1")
    tip = git_bin("fetch", "origin", "--quiet") or ""
    tip = git_bin("rev-parse", LINE)
    cells_tip = gate.exposure_cells(tip, "expst_tip")
    pois, ptree, pblob = poison_commit(tip)
    cells_pois = gate.exposure_cells(pois, "expst_pois")
    added = sorted(cells_pois - cells_tip)
    removed = sorted(cells_tip - cells_pois)

    checks = []

    def chk(name, ok, reading):
        checks.append({"arm": name, "holds": bool(ok), "reading": reading})

    chk("tip baseline is not empty (a zero-cell line would make any add/removal test vacuous)",
        len(cells_tip) > 0, "%d cells on the line" % len(cells_tip))
    chk("poison ADDS a cell the line already banned (arm has teeth)",
        any("ProductErrorBoundary.tsx" in a for a in added), "added=%s" % added[:6])
    chk("poison does not silently remove anything",
        len(removed) == 0, "removed=%s" % removed[:4])
    chk("the added cell is the same file I poisoned", pblob == git_bin("rev-parse", "%s:%s" % (pois, VICTIM)),
        "poison blob round-trips")
    chk("re-running the ruler on the tip is stable (instrument determinism)",
        gate.exposure_cells(tip, "expst_tip_again") == cells_tip, "%d cells, same set" % len(cells_tip))
    # the negative direction for the door's own wording: the arm must not fire on the tip against itself
    chk("arm is silent when candidate == tip (no self-flagging)",
        sorted(gate.exposure_cells(tip, "expst_self") - cells_tip) == [], "delta empty")

    blind = attribute_blind_spot(tip, cells_tip, gate.exposure_cells)
    shift = shift_commit(tip)
    shift_added = shift_growth = None
    if shift:
        cells_shift = gate.exposure_cells(shift, "expst_shift")
        ct = gate.exposure_counts(cells_tip)
        cs = gate.exposure_counts(cells_shift)
        shift_added = sorted(cells_shift - cells_tip)
        shift_growth = {k: v - ct.get(k, 0) for k, v in cs.items() if v > ct.get(k, 0)}
        chk("shift-only fixture is NOT refused (line moves are not new exposure)",
            shift_added != [] and shift_growth == {},
            "line-exact added=%s growth=%s" % (shift_added[:4], shift_growth))
    else:
        chk("shift-only fixture available", False, "fixture could not be built (file identical?)")
    report = {"DISCOVERY_attribute_blind_spot": blind,
              "shift_fixture": {"commit": shift, "line_exact_added": shift_added,
                                "growth": shift_growth},
              "tool": "preflight_and_land_r1.py --exposure-arm", "ruler_file": gate.EXPOSURE_RULER,
              "ruler_blob_claimed": gate.EXPOSURE_RULER_BLOB,
              "ruler_blob_actual": hashlib.sha1(open(os.path.join(HERE, gate.EXPOSURE_RULER), "rb").read()
                                                if os.path.isfile(os.path.join(HERE, gate.EXPOSURE_RULER))
                                                else b"").hexdigest() if False else None,
              "tip": tip, "poison_commit": pois, "poison_tree": ptree, "victim": VICTIM,
              "tip_cells": len(cells_tip), "poison_cells": len(cells_pois),
              "added": added, "removed": removed, "checks": checks}
    # Prove the published ruler blob still matches the file the door actually runs, if it is retrievable.
    rc = subprocess.run(["git", "-C", REPO, "cat-file", "-e", gate.EXPOSURE_RULER_BLOB + "^{blob}"],
                        capture_output=True, timeout=120).returncode
    if rc == 0:
        have = git_bin("rev-parse", gate.EXPOSURE_RULER_BLOB)
        local = hashlib.sha1(b"blob %d\0" % len(open(os.path.join(HERE, gate.EXPOSURE_RULER), "rb").read())
                             + open(os.path.join(HERE, gate.EXPOSURE_RULER), "rb").read()).hexdigest()
        report["ruler_blob_actual"] = local
        report["ruler_blob_matches_published"] = (local == have)
        checks.append({"arm": "the ruler the door runs == the published r6 blob",
                       "holds": local == have, "reading": "%s vs %s" % (local[:12], have[:12])})
    else:
        report["ruler_blob_actual"] = "PUBLISHED_BLOB_NOT_IN_THIS_OBJECT_STORE"
    report["n_checks"] = len(checks)
    report["n_holds"] = sum(1 for c in checks if c["holds"])
    report["all_holds"] = report["n_holds"] == report["n_checks"]
    print(json.dumps({"overall": "GREEN" if report["all_holds"] else "RED", "arms": checks,
                      "tip_cells": report["tip_cells"], "poison_cells": report["poison_cells"],
                      "added": added[:8], "removed": removed[:8],
                      "ruler": [report.get("ruler_blob_claimed"), report.get("ruler_blob_actual"),
                                report.get("ruler_blob_matches_published")]},
                     ensure_ascii=False, indent=1))
    if out_path:
        io.open(out_path, "w", encoding="utf-8", newline="\n").write(json.dumps(report, ensure_ascii=False, indent=1))
        print("out=%s (%d B)" % (out_path, os.path.getsize(out_path)))
    return 0 if report["all_holds"] else 1


if __name__ == "__main__":
    sys.exit(main())
