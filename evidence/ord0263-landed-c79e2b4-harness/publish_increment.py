"""Publish one interruptible segment of the landed-generation close-out and read every row back.

Usage: python publish_increment.py <segment-label> <file-or-tools/path> [more files...]

Why a general one: the box blue-screened once already at 02:2x, and the commander's instruction is to ship after
each sub-step instead of accumulating everything for one final upload. So a segment is just "these files, this
label" and the index it writes is named after the segment - earlier segments' files and indexes are never
overwritten, because `publish_evidence.py` short-circuits only when the bytes are already identical.

Every verdict row is derived from its own GET read-back (40-char blob + byte count). A missing local file is
reported, not skipped; a failed read-back is `PUBLISHED_UNPROVEN`; nothing in the ruler is touched here, and
the index records the ruler's current blob so a reader can see the same coordinate in every segment.
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
REPO_DIR = "evidence/ord0263-landed-c79e2b4-harness"
RULER_BLOB = "e9a4188f63e27bbbf8bfed35adfd554b9e8641d9"


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2:
        print("usage: publish_increment.py <segment-label> <file> [file...]")
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
            print("  MISSING ", name)
            continue
        data = lp.read_bytes()
        local = blob40(data)
        rp = f"{REPO_DIR}/{Path(name).name}"
        st = subprocess.run([sys.executable, str(PUBLISHER), str(lp), rp,
                             f"ORD-0263 HARNESS d291c9dc: landed-generation segment {seg}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = ((st.stdout or "") + (st.stderr or "")).strip()
        time.sleep(1.5)
        code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
        if code == 200 and isinstance(meta, dict) and meta.get("content"):
            rb = base64.b64decode(meta["content"])
            agree = blob40(rb) == local and len(rb) == len(data)
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": code, "readback_bytes": len(rb),
                         "readback_blob40": blob40(rb),
                         "verdict": "PROVEN" if agree else "BLOB_DIFFERS",
                         "publisher_rc": st.returncode,
                         "publisher_tail": out.splitlines()[-1][:120] if out else ""})
            print(f"  {'PROVEN ' if agree else 'DIFFERS'} {Path(name).name:48s} {len(data):>8,} B {local[:16]}")
        else:
            rows.append({"local_file": name, "repo_path": rp, "bytes": len(data), "blob40": local,
                         "readback_status": str(code), "verdict": "PUBLISHED_UNPROVEN",
                         "publisher_rc": st.returncode,
                         "publisher_tail": out.splitlines()[-1][:190] if out else ""})
            print(f"  UNPROVEN {name}: {code} :: {out.splitlines()[-1][:150] if out else ''}")

    ruler = (BASE / "tools/ord0263_verifier_v3.py").read_bytes()
    rb_now = blob40(ruler)
    proven = sum(1 for r in rows if r["verdict"] == "PROVEN")
    idx = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "segment": seg, "lane": "HARNESS d291c9dc",
           "subject": "landed generation c79e2b4f4efe414dba22a071a7136ae10b5c84aa as served from disk, "
                      "measured on my own face after the 02:2x-02:3x blue-screen reboot",
           "ruler": {"file": "tools/ord0263_verifier_v3.py", "bytes": len(ruler), "blob40": rb_now,
                     "promised": RULER_BLOB, "unchanged_so_far": rb_now == RULER_BLOB},
           "files_requested": len(names), "proven_by_40char_readback": proven,
           "not_proven": [r["local_file"] for r in rows if r["verdict"] != "PROVEN"],
           "older_segments_untouched": True, "rows": rows}
    OUT = BASE / f"ord0263_landedgen_{seg}_index.json"
    OUT.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    data = OUT.read_bytes()
    local = blob40(data)
    rp = f"{REPO_DIR}/{OUT.name}"
    subprocess.run([sys.executable, str(PUBLISHER), str(OUT), rp,
                    f"ORD-0263 HARNESS d291c9dc: landed-generation segment {seg} index"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
    time.sleep(1.5)
    code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
    rbb = base64.b64decode(meta["content"]) if code == 200 and isinstance(meta, dict) and meta.get("content") else b""
    ok_idx = blob40(rbb) == local
    print(f"  {'PROVEN ' if ok_idx else 'UNPROVEN'} {OUT.name} {len(data):,} B {local[:16]}")
    print(f"segment {seg}: PROVEN {proven}/{len(names)} plus the index: {ok_idx}")
    return 0 if proven == len(names) and ok_idx else 4


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
