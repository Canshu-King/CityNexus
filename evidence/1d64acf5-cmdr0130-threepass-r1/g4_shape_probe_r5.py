# -*- coding: utf-8 -*-
"""CMDR 02:45 line 10 measured over THREE arm generations, because the two-generation pair was built on a leg
that was not the line.

The previous two generations of this probe used `pre_arm` = the arm as it stood on my own branch before the
reshape (blob 395662e3c534229bc8492ea611b6c737257e6228).  That commit already carried the CMDR 18:34 sub-floor
predicate, so Q4 read red on both legs and the pair proved only that my reshape did not regress something I had
written myself.  The bytes the authoritative line actually carries are blob d3e21e9084a3589678d08f7b50afe5119b2b85b8,
and those have no sub-floor predicate at all - `grep -c consumer_writes` on them is 0.  So the leg that matters
for "the old shape had a hole" is the line's, and it is kept here beside my branch's, labelled by blob:

  line_arm    - the arm on the tip (basename exemption, no sub-floor rule)
  branch_pre  - my branch's pre-reshape commit (basename exemption, sub-floor rule present)
  reshaped    - the cell as ruled: named path whitelist + anti-rot guard + sub-floor rule

Expectations follow from what each leg's predicates can see, and the two states where the line is green while
the ruled cell is red are the holes, recorded as readings rather than argued:
  Q1 same name, other path (the basename hole)
  Q4 sub-floor consumer copy (the 18:34 hole CMDR named and the line still has)

Every state runs over the same injections; each injection is reverted and re-hashed, and the product files are
compared with the tip's blobs at the end.
"""
import io
import json
import os
import re
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = os.environ["CNX_PROBE_TIP"]  # the live authoritative sha, handed over by the driver that runs this probe
BRANCH_PRE = "c580cb5d"            # my branch before the reshape; its arm blob is 395662e3...
ARM = "backend/tests/test_qoder_ord0296_write_deadline.py"
NODE = ("tests/test_qoder_ord0296_write_deadline.py::"
        "test_G4_the_lock_wait_is_written_in_exactly_one_place")
FAMILY = ["tests/test_qoder_ord0296_write_deadline.py", "tests/test_qoder_ord0479_dictionary_key_shape.py"]
MAIN = "backend/app/main.py"
STAY = "backend/app/stay_generation_operations.py"
DEEP = "backend/app/db/deep/write_deadline.py"
NEW_WORKER = "backend/app/qoder_shape_probe_r1.py"
WHITELIST_LINE = '    SINGLE_SOURCE_FILES = {"app/db/write_deadline.py"}'
WIDENED = '    SINGLE_SOURCE_FILES = {"app/db/write_deadline.py", "app/db/deep/write_deadline.py"}'
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)
DEEP_WITH_NUMBER = ('"""probe: the same basename under a different path."""\n'
                    'DEEP_WAIT = "PRAGMA busy_timeout = 90000"\n')
DEEP_WITHOUT_NUMBER = ('"""probe: whitelisted but holding no number."""\n'
                       'DEEP_NOTE = "busy_timeout is the module\'s to decide"\n')
LINE, BRANCH, SHAPE = "line_arm", "branch_pre", "reshaped"


def git(*a, cwd=WT):
    r = subprocess.run(["git", "-C", cwd] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "").strip()


def blob(rel, rev=TIP):
    return git("rev-parse", "%s:%s" % (rev, rel))[1]


def local(rel):
    return git("hash-object", os.path.join(WT, rel.replace("/", os.sep)))[1]


def write(rel, text):
    p = os.path.join(WT, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    io.open(p, "w", encoding="utf-8", newline="\n").write(text)


def read(rel):
    return io.open(os.path.join(WT, rel.replace("/", os.sep)), encoding="utf-8").read()


def run(args, extra=()):
    r = subprocess.run([PY, "-m", "pytest"] + list(args) + list(extra) +
                       ["-p", "no:cacheprovider", "-q", "--tb=long"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    fired = [l.strip() for l in out.splitlines() if re.search(r"test_qoder_ord0296\S*:\d+:", l)]
    return {"rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
            "summary": (tail[-1] if tail else "")[:150], "bitting_line": (fired[0][:170] if fired else None)}


def leg_text(rev):
    """Materialise one leg by checking it out and reading it back.  `git show` in text mode strips
    and re-flips newlines, and a leg whose bytes are not the leg it names is worse than no leg, so
    each leg's blob is proved against the worktree here instead of assumed.  (`checkout <rev> --
    path` also moves the index, and the driver resets it before committing anything.)"""
    rc, _o = git("checkout", rev, "--", ARM)
    if rc != 0:
        raise SystemExit("ABORT: cannot materialise leg %s (rc %d)" % (rev, rc))
    t = read(ARM)
    if local(ARM) != blob(ARM, rev):
        raise SystemExit("ABORT: leg %s reads %s on disk, the object says %s"
                         % (rev, local(ARM), blob(ARM, rev)))
    return t


def main():
    blobs = {LINE: blob(ARM, TIP), BRANCH: blob(ARM, BRANCH_PRE), SHAPE: local(ARM)}
    texts = {SHAPE: read(ARM), LINE: leg_text(TIP), BRANCH: leg_text(BRANCH_PRE)}
    if len(set(blobs.values())) != 3:
        raise SystemExit("ABORT: two of the three legs are the same bytes %s" % json.dumps(blobs))
    if "consumer_writes" in texts[LINE] or "SINGLE_SOURCE_FILES" in texts[LINE]:
        raise SystemExit("ABORT: the tip's arm already carries the ruled cell - this pair would be vacuous")
    if "consumer_writes" not in texts[BRANCH]:
        raise SystemExit("ABORT: the branch_pre leg lost the sub-floor predicate; the leg is not the one I used")
    for label in (LINE, BRANCH, SHAPE):
        write(ARM, texts[label])
        if local(ARM) != blobs[label]:
            raise SystemExit("ABORT: writing leg %s back gives %s, expected %s"
                             % (label, local(ARM), blobs[label]))
    write(ARM, texts[SHAPE])
    rows = []

    def one(pid, expect, setup, note):
        per_leg = {}
        for label in (LINE, BRANCH, SHAPE):
            write(ARM, texts[label])
            created = setup()
            res = run([NODE])
            per_leg[label] = {"expect": expect[label], "got": res["verdict"],
                              "met": res["verdict"] == expect[label], "pytest": res}
            for rel in created:
                p = os.path.join(WT, rel.replace("/", os.sep))
                if os.path.exists(p):
                    os.remove(p)
            git("checkout", "--", MAIN)
            git("checkout", "--", STAY)
        write(ARM, texts[SHAPE])
        hole = [l for l in (LINE, BRANCH)
                if per_leg[l]["got"] == "green" and per_leg[SHAPE]["got"] == "red"]
        rows.append({"id": pid, "note": note, "arms": per_leg, "hole_in_this_leg": hole,
                     "all_met": all(v["met"] for v in per_leg.values())})
        print(json.dumps({"id": pid, "met": rows[-1]["all_met"], "hole_in_this_leg": hole,
                          "per_leg": {k: [v["got"], v["pytest"]["bitting_line"]]
                                      for k, v in per_leg.items()}}, ensure_ascii=False))

    def s_none():
        return []

    def s_deep_number():
        write(DEEP, DEEP_WITH_NUMBER)
        return [DEEP]

    def s_main_copy():
        src = read(MAIN)
        anchor = "PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms)"
        assert anchor in src, "main.py anchor moved"
        write(MAIN, src.rstrip("\n") + '\n\n\nSUB_SCALE_COPY = "PRAGMA busy_timeout = 1200"\n')
        import ast
        ast.parse(read(MAIN))
        return []

    def s_stay_floor():
        src = read(STAY)
        assert 'session.execute(text("PRAGMA busy_timeout = 1500"))' in src, "stay anchor moved"
        write(STAY, src.rstrip("\n") + '\n\n\nBIG_WORKER_WAIT = "PRAGMA busy_timeout = 90000"\n')
        import ast
        ast.parse(read(STAY))
        return []

    def s_new_worker():
        write(NEW_WORKER, '"""probe"""\n\n\ndef wait() -> str:\n    return "PRAGMA busy_timeout = 800"\n')
        return [NEW_WORKER]

    one("Q0_no_injection", {LINE: "green", BRANCH: "green", SHAPE: "green"}, s_none,
        "all three legs on the tree as it stands, so every pair below is comparable")
    one("Q1_same_name_other_path", {LINE: "green", BRANCH: "green", SHAPE: "red"}, s_deep_number,
        "app/db/deep/write_deadline.py stating 90000: exempt by basename, not by path")
    write(ARM, texts[SHAPE].replace(WHITELIST_LINE, WIDENED))
    write(DEEP, DEEP_WITH_NUMBER)
    res = run([NODE])
    os.remove(os.path.join(WT, DEEP.replace("/", os.sep)))
    write(ARM, texts[SHAPE])
    rows.append({"id": "Q2_named_expansion", "note": "the same file with its path written into the whitelist",
                 "arms": {SHAPE: {"expect": "green", "got": res["verdict"],
                                  "met": res["verdict"] == "green", "pytest": res}},
                 "hole_in_this_leg": [], "all_met": res["verdict"] == "green"})
    print(json.dumps({"id": "Q2_named_expansion", "got": res["verdict"]}, ensure_ascii=False))

    write(ARM, texts[SHAPE].replace(WHITELIST_LINE, WIDENED))
    write(DEEP, DEEP_WITHOUT_NUMBER)
    res = run([NODE])
    os.remove(os.path.join(WT, DEEP.replace("/", os.sep)))
    write(ARM, texts[SHAPE])
    rows.append({"id": "Q3_whitelist_rotted", "note": "path whitelisted but states no number",
                 "arms": {SHAPE: {"expect": "red", "got": res["verdict"],
                                  "met": res["verdict"] == "red", "pytest": res}},
                 "hole_in_this_leg": [], "all_met": res["verdict"] == "red"})
    print(json.dumps({"id": "Q3_whitelist_rotted", "got": res["verdict"],
                      "bitting_line": res["bitting_line"]}, ensure_ascii=False))

    one("Q4_sub_floor_consumer_copy", {LINE: "green", BRANCH: "red", SHAPE: "red"}, s_main_copy,
        "CMDR 18:34's own case - 1200 ms in a file that already asks settings; the line has no predicate "
        "for it at all, my branch's pre-reshape commit does")
    one("Q5_worker_at_floor", {LINE: "red", BRANCH: "red", SHAPE: "red"}, s_stay_floor,
        "a worker wait raised to request-path scale - every leg sees it")
    one("Q6_new_worker_below", {LINE: "green", BRANCH: "green", SHAPE: "green"}, s_new_worker,
        "a brand new 800 ms worker wait stays legitimate under all three")
    fam = run(FAMILY)
    rows.append({"id": "Q7_family", "note": "both ruler files whole on the ruled arm",
                 "arms": {SHAPE: {"expect": "green", "got": fam["verdict"],
                                  "met": fam["verdict"] == "green", "pytest": fam}},
                 "hole_in_this_leg": [], "all_met": fam["verdict"] == "green"})
    print(json.dumps({"id": "Q7_family", "got": fam["verdict"], "summary": fam["summary"]},
                     ensure_ascii=False))

    st = subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
    lines = [l for l in (st.stdout or "").splitlines() if l.strip()]
    outside = [l for l in lines if not l[3:].startswith("review/") and not l[3:].endswith(ARM)]
    product_clean = all(local(p) == blob(p) for p in (MAIN, STAY, "backend/app/db/write_deadline.py"))
    holes = sorted({r["id"] for r in rows for _l in r["hole_in_this_leg"] if _l == LINE})
    doc = {"tip": TIP, "arm_blobs": {"line_arm": blobs[LINE], "branch_pre": blobs[BRANCH],
                                     "reshaped": blobs[SHAPE]},
           "line_arm_blob": blobs[LINE], "branch_pre_arm_blob": blobs[BRANCH],
           "reshaped_arm_blob": blobs[SHAPE],
           "arm_written_back_to_ruled": local(ARM) == blobs[SHAPE],
           "line_arm_has_no_sub_floor_predicate": "consumer_writes" not in texts[LINE],
           "branch_pre_has_sub_floor_predicate": "consumer_writes" in texts[BRANCH],
           "whitelist_as_shipped": ["app/db/write_deadline.py"],
           "states": len(rows), "all_met": all(r["all_met"] for r in rows),
           "holes_open_on_the_line": holes,
           "product_files_byte_identical_to_tip": product_clean,
           "dirt_lines": len(lines), "dirt_outside_review_area": len(outside),
           "dirt_outside_review_area_lines": outside,
           "runs": rows,
           "reading": "the ruled cell closes two states the line is blind to: Q1 because the exemption is a "
                      "named path instead of a base name, Q4 because the sub-floor consumer predicate exists "
                      "at all. Both legs that miss them are reported with their own bytes, and the leg I used "
                      "as `pre` in the two earlier generations is here under its own name (branch_pre) so "
                      "those readings stay comparable instead of being re-labelled"}
    io.open(os.path.join(HERE, "g4_shape_probe_r5.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"all_met": doc["all_met"], "product_clean": product_clean,
                      "holes_open_on_the_line": holes, "arm_blobs": doc["arm_blobs"],
                      "dirt_out": len(outside), "states": doc["states"],
                      "arm_written_back": doc["arm_written_back_to_ruled"]}, ensure_ascii=False))
    return 0 if (doc["all_met"] and product_clean and not outside
                 and doc["arm_written_back_to_ruled"]) else 7


raise SystemExit(main())
