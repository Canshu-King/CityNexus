# -*- coding: utf-8 -*-
"""Census round 3, counter-arm: one legitimate contract add - which arms go red, and is any of them a defect?

The census classifies an equality against a set the product may widen again as drift-prone. That is a claim
about a future red, so here it is produced rather than argued: `429` is added to the documented responses of
`GET /api/v1/journeys/{journey_id}/checkins` in THIS lane's export. No product behaviour changes - the door
still answers exactly as it did - so every arm that now reddens is reddening on paperwork, and the block has
to say which ones and with what message.

The mutation is reverted in the same process, and the revert is checked by sha256 of the file bytes, not by
undoing the edit. If the restore does not hash back to the before value this script exits 7 and says so.
"""
import hashlib
import io
import json
import os
import subprocess

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
YAML = os.path.join(WT, "contracts", "openapi.yaml")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors\census_r3_counterarm_r1.json"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)
TIP = "569b8472b134e5562ef396e38681870b9c26536a"
FILES = ["tests/test_qoder_ord0402_recycle_bin.py", "tests/test_qoder_ord0434_share_grants.py",
         "tests/test_qoder_ord0444_collections.py", "tests/test_qoder_ord0476_checkins.py",
         "tests/test_qoder_ord0496_calendar_export.py", "tests/test_qoder_ord0332_error_receipt.py",
         "tests/test_qoder_ord0503_member_doors.py", "tests/test_v192_shadow_trial_gate.py"]


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(label):
    r = subprocess.run([PY, "-m", "pytest"] + FILES + ["-p", "no:cacheprovider", "-q", "--tb=no", "-rf"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=3600)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    return {"label": label, "rc": r.returncode, "summary": (tail[-1] if tail else "")[:160],
            "failed_arms": sorted({l.split(" - ")[0].replace("FAILED ", "").strip()
                                   for l in out.splitlines() if l.startswith("FAILED")})}


def main():
    before = io.open(YAML, "rb").read()
    tip_bytes = subprocess.run(["git", "-C", WT, "show", "%s:contracts/openapi.yaml" % TIP],
                               capture_output=True, env=ENV, timeout=600).stdout
    same_raw = sha(before) == sha(tip_bytes)
    same_lf = sha(before.replace(b"\r\n", b"\n")) == sha(tip_bytes.replace(b"\r\n", b"\n"))
    if not same_lf:
        print(json.dumps({"abort": "the file under mutation is not the tip's content"}, ensure_ascii=False))
        return 6
    clean = run("before_the_add")
    text = before.decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = [l.rstrip("\r") for l in text.split("\n")]
    path_at = next(i for i, l in enumerate(lines)
                   if l.strip() == "/journeys/{journey_id}/checkins:")
    post_at = next(i for i in range(path_at, len(lines)) if lines[i] == "    post:")
    add = ["        '429':", "          description: >-",
           "            Too many stamp reads from one traveller in a minute: a service limit on this door, "
           "not a", "            refusal of the trip", "          content:",
           "            application/json:",
           "              schema: {$ref: '#/components/schemas/ErrorEnvelope'}"]
    mutated = nl.join(lines[:post_at] + add + lines[post_at:]).encode("utf-8")
    io.open(YAML, "wb").write(mutated)
    try:
        red = run("after_a_legitimate_429_add")
        words = []
        for arm in red["failed_arms"]:
            r = subprocess.run([PY, "-m", "pytest", arm, "-p", "no:cacheprovider", "-q", "--tb=long"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=ENV, cwd=BACKEND, timeout=900)
            o = (r.stdout or "") + (r.stderr or "")
            hit = [l.strip() for l in o.splitlines()
                   if "AssertionError" in l or l.strip().startswith("assert ")]
            words.append({"arm": arm, "what_it_says": (hit[-1] if hit else "")[:220]})
    finally:
        io.open(YAML, "wb").write(before)
    after = io.open(YAML, "rb").read()
    restored = sha(after) == sha(before)
    doc = {"tip": TIP, "contract_sha256_before": sha(before), "contract_sha256_after_restore": sha(after),
           "restored_byte_equal": restored,
           "disk_equals_tip_blob_byte_for_byte": same_raw, "disk_equals_tip_content_lf_normalised": same_lf,
           "line_ending_in_file": repr(nl), "inserted_before_line": post_at + 1,
           "mutation": "add a '429' response to "
           "GET /api/v1/journeys/{journey_id}/checkins in contracts/openapi.yaml (this lane's export only, "
           "0 product bytes, reverted in the same process)",
           "runs": {"clean": clean, "mutated": red},
           "newly_red": sorted(set(red["failed_arms"]) - set(clean["failed_arms"])),
           "red_before_too": sorted(set(red["failed_arms"]) & set(clean["failed_arms"])),
           "what_each_red_says": words}
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"clean": clean["summary"], "mutated": red["summary"],
                      "newly_red": doc["newly_red"], "restored": restored}, ensure_ascii=False))
    return 0 if (restored and doc["newly_red"]) else 7


raise SystemExit(main())
