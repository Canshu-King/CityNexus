"""ORD-0402 slice 2 -- manifest of the evidence set, computed from the files."""
import hashlib
import json
from pathlib import Path

SRC = Path("D:/moodle/_qoder_q_ord0402_evidence")
DEST = Path("D:/moodle/_qoder_q_ord0402/wt/review/evidence/ord0402")

PRODUCED_BY = {
    "trash_two_arms_r1.json": "review/ord0402/drive_trash_r1.mjs -- the four arms on this lane's private stack (:4302 UI over :8714 uvicorn)",
    "stack_receipt_r1.json": "review/ord0402/private_stack_r1.py up + review/ord0402/prove_ownership_r1.py -- pid/parent/netstat proof, the durable readback from the sqlite file, and the shadowed-path measurement",
    "copy_pair_candidate-9ebe351f.json": "review/ord0402/copy_pair_trash_r1.py against this lane's build (arm)",
    "copy_pair_tip-e5a571f8.json": "the same script against the generation the preview chain serves today (control)",
    "nav_entry_r1.json": "review/ord0402/nav_entry_r1.mjs -- the drawer entry: which node has a real box, where it lands, and what the breadcrumb says on /v8/trash",
}

files = []
for p in sorted(SRC.iterdir()):
    if p.name == "MANIFEST.json" or not p.is_file():
        continue
    b = p.read_bytes()
    e = {"path": f"review/evidence/ord0402/{p.name}", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    if p.name in PRODUCED_BY:
        e["produced_by"] = PRODUCED_BY[p.name]
    files.append(e)

manifest = {
    "order": "ORD-0402 slice 2",
    "lane": "Q (session 904a042d)",
    "product_commits": {
        "feature": "cfd980fd762eee1d94db764a3262ae2346951c45",
        "refusals_and_refresh": "4ba53c0196dabc9624ad4ca5d8d13110a44097e8",
        "outcome_structure_and_re_read": "9ebe351ffc3f3998323cdee9634aa5d094318adb",
    },
    "base_tip": "e5a571f89e5d210e3616bd6752b3c90746f9e588",
    "generations_compared": {
        "arm": "index-DpznOKkU.js served by this lane's :4302 from the git-archive snap",
        "control": "index-BDf7HG58.js served by the preview chain on :4781 (read only)",
    },
    "private_stack": {
        "uvicorn_port": 8714,
        "ui_port": 4302,
        "db_file": "D:/moodle/_qoder_q_ord0402/assembly/q0402_trash.db (created by this lane, deleted after the run)",
        "read_door": "review/ord0402/trash_door_assembly_r1.py -- this lane's assembly, NOT product code; ORD-0402 slice 1 has not landed",
        "write_door": "POST /api/v1/journeys/{id}/undelete, landed by ORD-0399",
    },
    "files": files,
    "file_count": len(files),
    "total_bytes": sum(f["bytes"] for f in files),
}
text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
(SRC / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "MANIFEST.json").write_text(text, encoding="utf-8", newline="\n")
print("files", manifest["file_count"], "bytes", manifest["total_bytes"])
