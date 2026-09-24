"""ORD-0271-B: rewrite the readings slices to exclude every line already published in segment `runtime1`.

Segment `runtime1` published `ord0271b_readings.jsonl` at a moment when the file held two duplicate sanity
readings plus the first, Q8(b)-rejected control reading. Those three lines are already fixed in the published
blob, so the per-round slices must not contain them - otherwise the same reading would exist under two
coordinates with no note saying which is which. The rule is read from the published index itself: whatever that
blob contained is excluded, and the exclusion is printed rather than assumed.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
SRC = BASE / "ord0271b_readings.jsonl"
PUBLISHER = Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\publish_evidence.py")
API, BRANCH = "Canshu-King/CityNexus", "commander/control"
PUBLISHED = "evidence/ord0271-B-verifier-v4/ord0271b_readings.jsonl"
PUBLISHED_BLOB = "c69be25ea9036cdb"  # the row printed when segment runtime1 was read back


def blob40(d: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(d) + d).hexdigest()


def published_labels() -> tuple[set, str]:
    spec = importlib.util.spec_from_file_location("cmdr_publish", PUBLISHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    code, meta = mod.call("GET", f"/repos/{API}/contents/{PUBLISHED}?ref={BRANCH}")
    if code != 200 or not isinstance(meta, dict) or not meta.get("content"):
        raise SystemExit(f"ABORT: cannot read back the published readings file ({code})")
    b = base64.b64decode(meta["content"])
    if not blob40(b).startswith(PUBLISHED_BLOB):
        raise SystemExit(f"ABORT: published blob {blob40(b)[:16]} is not the coordinate I recorded")
    rows = [json.loads(l) for l in b.decode("utf-8").splitlines() if l.strip()]
    return {(r.get("label"), r.get("sha256")) for r in rows}, blob40(b)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    already, pub_blob = published_labels()
    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    excluded = [r["label"] for r in rows if (r.get("label"), r.get("sha256")) in already]
    fresh = [r for r in rows if (r.get("label"), r.get("sha256")) not in already]
    out = []
    for n in (1, 2, 3):
        keep = [r for r in fresh
                if str(r.get("label", "")).startswith((f"mutant{n}_", f"control{n}_"))]
        body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in keep)
        p = BASE / f"ord0271b_readings_round{n}.jsonl"
        p.write_bytes(body.encode("utf-8"))
        out.append({"file": p.name, "lines": len(keep), "bytes": p.stat().st_size,
                    "blob40": blob40(p.read_bytes()), "labels": [r["label"] for r in keep]})
    print(json.dumps({"published_file_blob40": pub_blob, "lines_already_published": len(excluded),
                      "excluded_labels": excluded, "slices": out,
                      "fresh_lines_total": len(fresh)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
