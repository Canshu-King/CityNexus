# -*- coding: utf-8 -*-
"""CMDR 02:45 line 10, re-measured on the 19:45 tip: the reshaped exemption and both arms over one injection set.

The ruling says the single-source cell takes 包含式 + 具名扩容白名单, that cell only. The old shape exempted a
file by its BASE NAME (`Path(rel).name == "write_deadline.py"`), which lets anything sharing that name at any
other path walk under the ruler; the new shape carries a named path whitelist, requires a member that is
named to actually state a number, and leaves the floor half and the `offenders` half untouched.

Every state runs twice over the same injected tree - once with the arm as it stands on the line's chain
(blob 395662e3) and once with the reshaped arm - because "the old shape had a hole" is a claim about a
reading the old arm never produced. Both sides must report, so the pair is what is recorded, not one side.

  Q0 no injection            - both arms green (the pair is comparable).
  Q1 same name, other path   - `app/db/deep/write_deadline.py` stating 90000. Old arm green (the hole),
                               new arm red on the unsourced line.
  Q2 named expansion         - the same file, its path written into the whitelist: new arm green.
  Q3 whitelist rotted        - path whitelisted, file states no number: new arm red on the rot line.
  Q4 sub-floor consumer copy - CMDR 18:34's own case, both arms red (nothing regressed).
  Q5 worker at floor scale   - both arms red.
  Q6 new 800 ms worker       - both arms green (the legitimate half is still not swallowed).
  Q7 family                  - both files whole on the reshaped arm.

Injections are created or edited in this lane's export only, reverted in the same process, and the revert is
checked by hash-object against the tip blob.
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
TIP = "b7bb40ee90619c0febc667394279bd3c8a1d835d"
PRE = "f8c95bfb"  # this branch before the reshape - the 18:34 arm as re-cut on the 19:45 tip
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


def main():
    pre_text = git("show", "%s:%s" % (PRE, ARM))[1] + "\n"
    new_text = read(ARM)
    reshaped_blob = local(ARM)
    assert reshaped_blob != blob(ARM, PRE), "the reshape did not land in the tree"
    texts = {"pre_arm": pre_text, "reshaped": new_text}
    rows = []

    def one(pid, expect, arms, setup, note):
        per_arm = {}
        for label in arms:
            write(ARM, texts[label])
            created = setup()
            res = run([NODE])
            per_arm[label] = {"expect": expect[label], "got": res["verdict"],
                              "met": res["verdict"] == expect[label], "pytest": res}
            for rel in created:
                p = os.path.join(WT, rel.replace("/", os.sep))
                if os.path.exists(p):
                    os.remove(p)
            git("checkout", "--", MAIN)
            git("checkout", "--", STAY)
        write(ARM, texts["reshaped"])
        rows.append({"id": pid, "note": note, "arms": per_arm,
                     "all_met": all(v["met"] for v in per_arm.values())})
        print(json.dumps({"id": pid, "met": rows[-1]["all_met"],
                          "per_arm": {k: [v["got"], v["pytest"]["bitting_line"]]
                                      for k, v in per_arm.items()}}, ensure_ascii=False))

    def s_none():
        return []

    def s_deep_number():
        write(DEEP, DEEP_WITH_NUMBER)
        return [DEEP]

    def s_deep_no_number():
        write(DEEP, DEEP_WITHOUT_NUMBER)
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

    one("Q0_no_injection", {"pre_arm": "green", "reshaped": "green"}, list(texts), s_none,
        "both arms on the tree as it stands, so the pair below is comparable")
    one("Q1_same_name_other_path", {"pre_arm": "green", "reshaped": "red"}, list(texts), s_deep_number,
        "app/db/deep/write_deadline.py stating 90000: exempt by basename, not by path")
    write(ARM, texts["reshaped"])
    write(DEEP, DEEP_WITH_NUMBER)
    tmp = texts["reshaped"].replace(WHITELIST_LINE, WIDENED)
    write(ARM, tmp)
    res = run([NODE])
    os.remove(os.path.join(WT, DEEP.replace("/", os.sep)))
    write(ARM, texts["reshaped"])
    rows.append({"id": "Q2_named_expansion", "note": "the same file with its path written into the whitelist",
                 "arms": {"reshaped": {"expect": "green", "got": res["verdict"], "met": res["verdict"] == "green",
                                       "pytest": res}}, "all_met": res["verdict"] == "green"})
    print(json.dumps({"id": "Q2_named_expansion", "got": res["verdict"]}, ensure_ascii=False))

    write(ARM, texts["reshaped"].replace(WHITELIST_LINE, WIDENED))
    write(DEEP, DEEP_WITHOUT_NUMBER)
    res = run([NODE])
    os.remove(os.path.join(WT, DEEP.replace("/", os.sep)))
    write(ARM, texts["reshaped"])
    rows.append({"id": "Q3_whitelist_rotted", "note": "path whitelisted but states no number",
                 "arms": {"reshaped": {"expect": "red", "got": res["verdict"], "met": res["verdict"] == "red",
                                       "pytest": res}}, "all_met": res["verdict"] == "red"})
    print(json.dumps({"id": "Q3_whitelist_rotted", "got": res["verdict"],
                      "bitting_line": res["bitting_line"]}, ensure_ascii=False))

    one("Q4_sub_floor_consumer_copy", {"pre_arm": "red", "reshaped": "red"}, list(texts), s_main_copy,
        "CMDR 18:34's own case - 1200 ms in a file that already asks settings")
    one("Q5_worker_at_floor", {"pre_arm": "red", "reshaped": "red"}, list(texts), s_stay_floor,
        "a worker wait raised to request-path scale")
    one("Q6_new_worker_below", {"pre_arm": "green", "reshaped": "green"}, list(texts), s_new_worker,
        "a brand new 800 ms worker wait stays legitimate")
    fam = run(FAMILY)
    rows.append({"id": "Q7_family", "note": "both ruler files whole on the reshaped arm",
                 "arms": {"reshaped": {"expect": "green", "got": fam["verdict"],
                                       "met": fam["verdict"] == "green", "pytest": fam}},
                 "all_met": fam["verdict"] == "green"})
    print(json.dumps({"id": "Q7_family", "got": fam["verdict"], "summary": fam["summary"]},
                     ensure_ascii=False))

    st = subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True,
                        text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
    lines = [l for l in (st.stdout or "").splitlines() if l.strip()]
    # the reshaped arm is the candidate itself and is still uncommitted at this point; the review/ area is
    # this lane's line-ending noise; anything else would be an injection that did not get reverted
    allowed = (ARM,)
    expected_dirt = [l for l in lines if any(l[3:].endswith(a) for a in allowed)]
    outside = [l for l in lines if not l[3:].startswith("review/")
               and not any(l[3:].endswith(a) for a in allowed)]
    product_clean = all(local(p) == blob(p) for p in (MAIN, STAY, "backend/app/db/write_deadline.py"))
    doc = {"tip": TIP, "pre_arm_blob": blob(ARM, PRE), "reshaped_arm_blob": reshaped_blob,
           "arm_written_back_to_reshaped": local(ARM) == reshaped_blob,
           "whitelist_as_shipped": ["app/db/write_deadline.py"],
           "states": len(rows), "all_met": all(r["all_met"] for r in rows),
           "product_files_byte_identical_to_tip": product_clean,
           "dirt_lines": len(lines), "dirt_outside_review_area": len(outside),
           "dirt_outside_review_area_lines": outside,
           "expected_dirt_candidate_not_yet_committed": expected_dirt, "runs": rows,
           "reading": "the exemption moves from basename to a named path whitelist; Q1 is the hole the old "
                      "shape had (old arm green on it, reshaped arm red), Q2 is the ruled expansion channel, "
                      "Q3 keeps a named-but-empty whitelist from passing"}
    io.open(os.path.join(HERE, "g4_shape_probe_r3.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"all_met": doc["all_met"], "product_clean": product_clean,
                      "reshaped_blob": doc["reshaped_arm_blob"], "dirt_out": len(outside),
                      "states": doc["states"]}, ensure_ascii=False))
    return 0 if (doc["all_met"] and product_clean and not outside) else 7


raise SystemExit(main())
