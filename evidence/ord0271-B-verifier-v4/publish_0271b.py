"""Publish one segment of ORD-0271-B and read every row back by its own 40-char blob.

Same shape as `publish_increment.py`, with three things changed deliberately:

* the target is a NEW path, `evidence/ord0271-B-verifier-v4/` - 0263's published blobs and the landed-generation
  segments are never written again, and 0271-A's evidence will get its own section rather than be mixed in here;
* the ruler coordinate tracked in the index is v4, while v3's published blob (`e9a4188f63e27bbbf8bfed35adfd554b9e8641d9`,
  21,703 B) is re-hashed from disk on every segment, so "the old ruler was not edited to make the new one fit"
  is a reading that repeats rather than a sentence I wrote once;
* the index is named after the segment, so an interrupted run can be resumed without overwriting what already
  landed.

Every row's verdict comes from its own GET read-back. A missing local file is reported, a failed read-back is
`PUBLISHED_UNPROVEN`, and nothing here decides a verdict - the ruler does that.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
PUBLISHER = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\publish_evidence.py")
API, BRANCH = "Canshu-King/CityNexus", "commander/control"
REPO_DIR = "evidence/ord0271-B-verifier-v4"
V3 = BASE / "tools" / "ord0263_verifier_v3.py"
V3_PUBLISHED_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"
V3_PUBLISHED_BYTES = 21703
V4 = BASE / "tools" / "ord0263_verifier_v4.py"
SUBJECT = ("ORD-0271-B HARNESS d291c9dc: verifier v4 and the dedicated single-variable counter-proof for the "
           "ORD-0263 fifth state")


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2:
        print("usage: publish_0271b.py <segment-label> <file> [file...]")
        return 2
    seg, names = argv[0], argv[1:]
    spec = importlib.util.spec_from_file_location("cmdr_publish", PUBLISHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rows = []
    for name in names:
        lp = BASE / name
        if not lp.is_file():
            rows.append({"local_file": name, "verdict": "MISSING_LOCAL_FILE"})
            print("  MISSING  ", name)
            continue
        data = lp.read_bytes()
        local = blob40(data)
        rp = f"{REPO_DIR}/{Path(name).name}"
        st = subprocess.run([sys.executable, str(PUBLISHER), str(lp), rp,
                             f"{SUBJECT} - segment {seg}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = ((st.stdout or "") + (st.stderr or "")).strip()
        time.sleep(1.5)
        code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
        if code == 200 and isinstance(meta, dict) and meta.get("content"):
            rb = base64.b64decode(meta["content"])
            agree = blob40(rb) == local and len(rb) == len(data)
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": code, "readback_bytes": len(rb), "readback_blob40": blob40(rb),
                         "verdict": "PROVEN" if agree else "BLOB_DIFFERS", "publisher_rc": st.returncode,
                         "publisher_tail": out.splitlines()[-1][:120] if out else ""})
            print(f"  {'PROVEN ' if agree else 'DIFFERS'} {Path(name).name:46s} {len(data):>9,} B {local[:16]}")
        else:
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": str(code), "verdict": "PUBLISHED_UNPROVEN",
                         "publisher_rc": st.returncode,
                         "publisher_tail": out.splitlines()[-1][:190] if out else ""})
            print(f"  UNPROVEN {name}: {code} :: {out.splitlines()[-1][:150] if out else ''}")

    v3b = V3.read_bytes()
    v4b = V4.read_bytes() if V4.is_file() else b""
    proven = sum(1 for r in rows if r["verdict"] == "PROVEN")
    idx = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "segment": seg, "lane": "HARNESS d291c9dc", "subject": SUBJECT,
           "rulers": {"v3": {"file": "tools/ord0263_verifier_v3.py", "bytes": len(v3b),
                             "blob40": blob40(v3b), "published_blob40": V3_PUBLISHED_BLOB,
                             "published_bytes": V3_PUBLISHED_BYTES,
                             "unchanged": blob40(v3b) == V3_PUBLISHED_BLOB and len(v3b) == V3_PUBLISHED_BYTES},
                      "v4": {"file": "tools/ord0263_verifier_v4.py", "bytes": len(v4b),
                             "blob40": blob40(v4b) if v4b else None,
                             "present": bool(v4b)}},
           "files_requested": len(names), "proven_by_40char_readback": proven,
           "not_proven": [r["local_file"] for r in rows if r["verdict"] != "PROVEN"],
           "older_segments_untouched": True, "rows": rows}
    OUT = BASE / f"ord0271B_{seg}_index.json"
    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    data = OUT.read_bytes()
    local = blob40(data)
    rp = f"{REPO_DIR}/{OUT.name}"
    subprocess.run([sys.executable, str(PUBLISHER), str(OUT), rp,
                    f"{SUBJECT} - segment {seg} index"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    time.sleep(1.5)
    code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
    rbb = base64.b64decode(meta["content"]) if code == 200 and isinstance(meta, dict) and meta.get("content") else b""
    ok_idx = blob40(rbb) == local
    print(f"  {'PROVEN ' if ok_idx else 'UNPROVEN'} {OUT.name} {len(data):,} B {local[:16]}")
    print(f"segment {seg}: PROVEN {proven}/{len(names)} plus the index: {ok_idx} "
          f"| v3 unchanged: {idx['rulers']['v3']['unchanged']}")
    return 0 if proven == len(names) and ok_idx else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
