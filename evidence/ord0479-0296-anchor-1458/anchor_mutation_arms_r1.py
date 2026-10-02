# -*- coding: utf-8 -*-
"""ORD-0479/0296 re-anchoring - do the two arms still bite, and do they still ignore movement?

The order says to stop anchoring on row numbers. A change like that is only worth landing if it keeps the
defect-detection power, so each arm is tested in both directions on a private export tree:

  GREEN-under-movement  - shift the site up and down; a row-number anchor would go red for nothing.
  RED-under-substance   - rename the named const, drop the dictionary key, or restate the lock wait at
                          request-path scale in a file the old test had never heard of.

Every mutation is applied to one file at a time and reverted by `git checkout -- <path>`, then the file is
re-hashed against the tip blob, so the tree the readings came from is provably the tip's tree afterwards.
"""
import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
BACKEND = os.path.join(WT, "backend")
TIP = "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)
ENV["NO_PROXY"] = "*"

PANEL = "frontend/src/features/shared/SharedJourneyPanel.tsx"
NEW_APP_FILE = "backend/app/qoder_anchor_probe_r1.py"

MUTATIONS = [
    {"id": "M0_control", "expect": "green", "why": "both arms as shipped on this tip",
     "target": None, "run": ["tests/test_qoder_ord0479_dictionary_key_shape.py",
                             "tests/test_qoder_ord0296_write_deadline.py"]},
    {"id": "M1_site_moves", "expect": "green",
     "why": "the site moves by four lines: an anchor that names a row cannot tell this from a defect",
     "target": PANEL,
     "apply": lambda t: t.replace("export const REFUSAL_KEY",
                                  "\n\n\n\nexport const REFUSAL_KEY", 1),
     "run": ["tests/test_qoder_ord0479_dictionary_key_shape.py"]},
    {"id": "M2_const_renamed", "expect": "red",
     "why": "the named const the exemption is identified by disappears - the reading must fail, not follow",
     "target": PANEL,
     "apply": lambda t: t.replace("export const REFUSAL_KEY", "export const REFUSAL_KEY_RENAMED", 1),
     "run": ["tests/test_qoder_ord0479_dictionary_key_shape.py"]},
    {"id": "M3_key_no_longer_a_dictionary_key", "expect": "red",
     "why": "the row stops being a translation-table value, so the forgiveness no longer applies",
     "target": PANEL,
     "apply": lambda t: t.replace('token_unknown: "shared.refusedTokenUnknown"',
                                  'token_unknown: "shared.notADictionaryKeyAtAll"', 1),
     "run": ["tests/test_qoder_ord0479_dictionary_key_shape.py"]},
    {"id": "M4_second_lock_wait_at_scale", "expect": "red",
     "why": "a request-path-scale wait restated inline in a file the old frozen name list never named",
     "target": NEW_APP_FILE, "create": True,
     "body": '"""probe"""\nENGINE_ARGS = {"timeout": 60}\n\n\ndef pragma():\n'
             '    return "PRAGMA busy_timeout = 45000"\n',
     "run": ["tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"]},
    {"id": "M5_short_worker_wait_in_a_new_file", "expect": "green",
     "why": "a worker's own sub-second wait in a brand new file must not be read as a second source",
     "target": NEW_APP_FILE, "create": True,
     "body": '"""probe"""\n\n\ndef pragma():\n    return "PRAGMA busy_timeout = 800"\n',
     "run": ["tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"]},
]


def git(*a):
    r = subprocess.run(["git", "-C", WT] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=600)
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


def tip_blob(rel):
    rc, out, err = git("rev-parse", "%s:%s" % (TIP, rel))
    return out if rc == 0 and out else None


def hash_object(rel):
    rc, out, err = git("hash-object", rel)
    if rc != 0:
        return None
    return out.split()[0]


def restore(rel, created):
    if created:
        p = os.path.join(WT, rel.replace("/", os.sep))
        if os.path.exists(p):
            os.remove(p)
        return
    git("checkout", "--", rel)


def run_pytest(args):
    r = subprocess.run([PY, "-m", "pytest"] + args + ["-p", "no:cacheprovider", "-q", "--tb=line"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()][-1:] if out.strip() else [""]
    failed = sorted({l.split("::")[-1].split(" ")[0] for l in out.splitlines() if l.startswith("FAILED")})
    return {"rc": r.returncode, "summary": tail[0][:160], "failed_arms": failed}


def main():
    os.makedirs(HERE, exist_ok=True)
    rows = []
    for mut in MUTATIONS:
        rel = mut.get("target")
        created = False
        if rel:
            if mut.get("create"):
                created = True
                path = os.path.join(WT, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                io.open(path, "w", encoding="utf-8", newline="\n").write(mut["body"])
            else:
                path = os.path.join(WT, rel.replace("/", os.sep))
                text = io.open(path, encoding="utf-8").read()
                io.open(path, "w", encoding="utf-8", newline="\n").write(mut["apply"](text))
        res = run_pytest(mut["run"])
        verdict = "red" if res["rc"] != 0 else "green"
        rows.append({"id": mut["id"], "expect": mut["expect"], "got": verdict, "met": verdict == mut["expect"],
                     "why": mut["why"], "target": rel, "pytest": res})
        if rel:
            restore(rel, created)
        back = hash_object(rel) if rel and not created else None
        if rel and not created:
            rows[-1]["restored_equal_to_tip_blob"] = (back == tip_blob(rel))
        process = {"id": mut["id"], "got": verdict, "met": rows[-1]["met"]}
        print(json.dumps(process, ensure_ascii=False))
    status = git("status", "--porcelain")[1]
    doc = {"tip": TIP, "arms_run": len(rows), "all_expectations_met": all(r["met"] for r in rows),
           "tree_clean_after": status == "", "git_status_after": status, "runs": rows}
    io.open(os.path.join(HERE, "anchor_mutation_arms_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"all_met": doc["all_expectations_met"], "tree_clean": doc["tree_clean_after"],
                      "git_status_after": status}, ensure_ascii=False))
    return 0 if doc["all_expectations_met"] and doc["tree_clean_after"] else 5


raise SystemExit(main())
