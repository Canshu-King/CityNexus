# -*- coding: utf-8 -*-
"""Round-3 run record: are the arms sitting on those derived-inventory lists green as shipped?

Also names the tree shape they need. Two arms in those files read sibling files under `review/`, so on a
sparse export that omits that root they read as defects; they are not. The same trap cost this census one
false report in round one, so it is recorded here rather than quietly worked around.
"""
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
OUT = os.path.join(HERE, "census_r3_run_r1.json")
TIP = "569b8472b134e5562ef396e38681870b9c26536a"
FILES = ["tests/test_qoder_ord0402_recycle_bin.py", "tests/test_qoder_ord0434_share_grants.py",
         "tests/test_qoder_ord0444_collections.py", "tests/test_qoder_ord0476_checkins.py",
         "tests/test_qoder_ord0496_calendar_export.py", "tests/test_qoder_ord0332_error_receipt.py",
         "tests/test_qoder_ord0296_write_deadline.py", "tests/test_qoder_ord0479_dictionary_key_shape.py"]
READERS = ["tests/test_qoder_ord0402_recycle_bin.py", "tests/test_qoder_ord0496_calendar_export.py"]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)


def sh(*a, cwd=WT):
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=ENV, cwd=cwd, timeout=900)
    return (r.stdout or "").strip()


def main():
    roots = sh("git", "sparse-checkout", "list").split()
    sibs = sh("git", "ls-files", "review/ord0402-readouts", "review/ord0496").splitlines()
    reads = []
    for rel in READERS:
        lines = io.open(os.path.join(BACKEND, rel.replace("/", os.sep)), encoding="utf-8",
                        errors="replace").read().splitlines()
        hits = [(i, l.strip()[:140]) for i, l in enumerate(lines, 1) if "review/" in l]
        if hits:
            reads.append({"file": "backend/" + rel, "first_line_with_review_path": hits[0][0],
                          "text": hits[0][1], "such_lines": len(hits)})
    r = subprocess.run([PY, "-m", "pytest"] + FILES +
                       ["-p", "no:cacheprovider", "-q", "--tb=no", "-rf"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=3600)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    doc = {"tip": TIP, "sparse_roots": roots, "review_in_sparse": "review" in roots,
           "tracked_review_siblings": len(sibs), "sibling_sample": [s.rsplit("/", 1)[-1] for s in sibs[:3]],
           "arms_reading_siblings": reads,
           "pytest_files": len(FILES), "pytest_rc": r.returncode,
           "pytest_summary": (tail[-1] if tail else "")[:160],
           "failed_arms": sorted({l.split("::")[-1].split(" ")[0] for l in out.splitlines()
                                  if l.startswith("FAILED")})}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"roots": roots, "sibs": len(sibs), "summary": doc["pytest_summary"],
                      "failed": doc["failed_arms"], "readers": len(reads)}, ensure_ascii=False))


raise SystemExit(main())
