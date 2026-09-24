"""Restore a local tool file to the exact bytes that are already published, so local and external agree.

Used after a published tool is improved in place: the improvement gets a new name (it must not overwrite a
published evidence path), and the old name is put back to the bytes whose blob is already quoted in a published
index. The read-back blob is compared with the coordinate recorded at publish time, so this script cannot
silently write something else into that name.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
PUBLISHER = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\publish_evidence.py")
API, BRANCH = "Canshu-King/CityNexus", "commander/control"
DIR = "evidence/ord0271-B-verifier-v4"


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    local_name, expected16 = argv[0], argv[1]
    spec = importlib.util.spec_from_file_location("cmdr_publish", PUBLISHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rp = f"{DIR}/{local_name}"
    code, meta = mod.call("GET", f"/repos/{API}/contents/{rp}?ref={BRANCH}")
    if code != 200 or not isinstance(meta, dict) or not meta.get("content"):
        print(f"ABORT: {rp} not readable ({code})")
        return 3
    b = base64.b64decode(meta["content"])
    if not blob40(b).startswith(expected16):
        print(f"ABORT: published blob {blob40(b)} does not match the recorded coordinate {expected16}")
        return 4
    (BASE / "tools" / local_name).write_bytes(b)
    print(json.dumps({"restored": f"tools/{local_name}", "bytes": len(b), "blob40": blob40(b),
                      "matches_recorded": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
