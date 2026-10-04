# -*- coding: utf-8 -*-
"""Prove the floor: run the OLD publisher and the NEW one with an empty file list and compare their answers.

Nothing here publishes. The old publisher is copied to a temp file with its manifest emptied and its receipt path
pointed at the temp dir, so it can neither push nor overwrite a published receipt; the new one is asked the same
question through its own decision function. The point of the run is the pair of exit codes: the old door called an
empty publication a pass, the new one refuses.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
OLD = "publish_hook_r1.py"
PY = sys.executable
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")
for _k in ("http_proxy", "https_proxy"):
    ENV[_k] = ""


def old_with_empty_manifest():
    s = io.open(os.path.join(WORK, OLD), encoding="utf-8").read()
    i = s.index("NEW = [")
    j = s.index("]", i) + 1
    s = s[:i] + "NEW = []" + s[j:]
    k = s.index('RECEIPT = "')
    m = s.index('"', k + 11)
    s = s[:k] + 'RECEIPT = r"%s"' % os.path.join(tempfile.gettempdir(), "cnx_old_publisher_empty.json") + s[m + 1:]
    compile(s, "<old>", "exec")
    return s


def run(path):
    r = subprocess.run([PY, path], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=WORK, timeout=1800)
    out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    return {"rc": r.returncode, "line": (out[-1] if out else "")[:300]}


def main():
    old_path = os.path.join(tempfile.gettempdir(), "cnx_old_publisher_empty.py")
    io.open(old_path, "w", encoding="utf-8", newline="\n").write(old_with_empty_manifest())
    old = run(old_path)
    os.remove(old_path)
    # the new door: same question, asked through its own CLI with an empty manifest
    r = subprocess.run([PY, os.path.join(WORK, "lane_publisher_r1.py"), "--slug", "evidence/does-not-matter",
                        "--files", "", "--message", "x"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, cwd=WORK, timeout=900)
    lines = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    new = {"rc": r.returncode, "line": (lines[-1] if lines else "")[:300]}
    here = "lane_publisher_r1.py"
    d = subprocess.run([PY, os.path.join(WORK, "lane_publisher_r1.py"), "--decide-only"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=WORK, timeout=900)
    decide = json.loads((d.stdout or "").strip().splitlines()[-1])
    dry = subprocess.run([PY, os.path.join(WORK, "lane_publisher_r1.py"), "--slug", "evidence/probe",
                          "--files", "lane_publisher_r1.py", "--message", "x", "--dry-run"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         env=ENV, cwd=WORK, timeout=900)
    codes = {k: sorted(r["code"] for r in v["refusals"]) for k, v in decide.items()}
    doc = {"old_publisher_empty_manifest": old, "new_publisher_empty_manifest": new,
           "decision_table": decide, "refusal_codes": codes,
           "dry_run": {"rc": dry.returncode, "line": (dry.stdout or "").strip()[:200]},
           "arms_pass": bool(old["rc"] == 0 and new["rc"] == 5
                             and "MISSING_FILE" in codes["missing"]
                             and "EMPTY_MANIFEST" in codes["empty"]
                             and codes["empty_shelf"] == ["NOTHING_ON_SHELF"]
                             and decide["empty_shelf"]["exit_code"] == 7
                             and decide["valid_manifest_pre"]["exit_code"] == 0
                             and dry.returncode == 0),
           "reading": "the old door returns %d (a pass) for an empty publication; the new door returns %d "
                      "(EMPTY_MANIFEST) and %d for a missing file" % (old["rc"], new["rc"],
                                                                      decide["missing"]["exit_code"])}
    io.open(os.path.join(WORK, "publisher_fix_proof_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps(doc, ensure_ascii=False)[:700])
    return 0 if doc["arms_pass"] else 7


raise SystemExit(main())
