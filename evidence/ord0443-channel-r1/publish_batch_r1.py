"""Publish this session's ORD-0443 / ORD-0432 evidence through the gate and record every blob.

Written as a file on purpose: a heredoc mangled the backslash paths on this shell and produced a
`evidence$3` target, which is exactly the kind of failure that would otherwise be reported as
"published".
"""
import json
import os
import pathlib
import re
import subprocess

P = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GATE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\publish_evidence_gated_r1.py"
E = pathlib.Path(r"D:\moodle\CityNexus-Hermes-Revival\evidence")
A_FILES = ["ORD0432_DELIVERY_r3.json", "ord0432_delivery_receipt_r3.py", "ORD0432_WITNESS_8711.json",
           "ORD0432_WITNESS_8712.json", "ORD0432_REVERSE_ARMS_rebased.json",
           "ORD0432_AGENT_LEG_rebased.json"]
B_FILES = ["ORD0443_RECEIPT_r2.md", "WB2API_DEEPSEEK_16TOK.json", "WB2API_RECHECK.json",
           "wb2api_deepseek_budget.py", "wb2api_recheck_r1.py", "shim_r2_patch.diff",
           "publish_batch_r1.py", "PUBLISHED_BLOBS.json"]
BATCH = [("ord0443-channel-r1", E / "0443", B_FILES)]

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
    env.pop(k, None)

blobs, fails = {}, []
for folder, base, files in BATCH:
    for name in files:
        local = base / name
        if not local.is_file():
            fails.append([folder, name, "missing locally"])
            continue
        r = subprocess.run([P, GATE, "--local", str(local), "--path", f"evidence/{folder}/{name}",
                            "--message", "lane a6b95d59: ORD-0443 gateway read-out + ORD-0432 rebase"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        dec = re.search(r'"decision": "(\w+)"', r.stdout or "")
        blob = re.search(r'"blob": "([0-9a-f]{40})"', r.stdout or "")
        read = re.search(r'"readback_blob": "([0-9a-f]{40})"', r.stdout or "")
        path = f"evidence/{folder}/{name}"
        if dec and blob and read and blob.group(1) == read.group(1):
            blobs[path] = blob.group(1)
        else:
            fails.append([folder, name, ((r.stdout or "") + (r.stderr or ""))[-260:]])

out = E / "0443" / "PUBLISHED_BLOBS_r2.json"
out.write_text(json.dumps({"blobs": blobs, "fails": fails}, ensure_ascii=False, indent=2),
               encoding="utf-8", newline="\n")
print("published", len(blobs), "| fails", len(fails))
for row in fails[:6]:
    print("FAIL", row[0], row[1], row[2][:200])
print("WROTE", out)
