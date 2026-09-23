"""ORD-0263 landedgen teardown: stop my :4415/:8411 and delete the copy I made - by name, after the digests.

The copy under `landedgen/dist` exists only because the order asked me to measure the served bundle
without rebuilding it. Its tree digest and the two named assets' per-file sha256 are recorded in
`ord0263_landedgen_surface_receipt.json` and re-published with this teardown, so what I delete is a
digest-proven duplicate of a file that is still on disk behind the user's chain - not evidence.
The user's ports are observed with netstat and never signalled.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
MY_PORTS = (4415, 8411)
OBSERVED_ONLY = (4781, 4782, 8693, 4185, 8713, 4411, 4412)
LIVE_DIST = Path(r"D:\moodle\_qoder_preview_20260920\dist")
NAMED = [BASE / "landedgen" / "dist", BASE / "landedgen_preview.log", BASE / "landedgen_preview.pid",
         BASE / "landedgen_s4_answered.log", BASE / "landedgen_s3_silent.log"]


def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", errors="replace")


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == port})


def tree_bytes(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.exists() else 0


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    killed = {}
    for port in MY_PORTS:
        pids = listeners(port)
        for pid in pids:
            sh("powershell", "-NoProfile", "-Command",
               f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        killed[str(port)] = pids
    for _ in range(20):
        if not any(listeners(p) for p in MY_PORTS):
            break
        time.sleep(1)
    still = {str(p): listeners(p) for p in MY_PORTS}
    observed = {str(p): listeners(p) for p in OBSERVED_ONLY}

    freed = 0
    removed = []
    for target in NAMED:
        if target.is_dir():
            n = tree_bytes(target)
            removed.append({"path": str(target), "kind": "dir", "files": len(
                [f for f in target.rglob("*") if f.is_file()]), "bytes": n})
            freed += n
            shutil.rmtree(target, ignore_errors=True)
        elif target.is_file():
            n = target.stat().st_size
            removed.append({"path": str(target), "kind": "file", "bytes": n})
            freed += n
            target.unlink()
        else:
            removed.append({"path": str(target), "kind": "absent", "bytes": 0})

    def tree_digest(root: Path) -> tuple[int, int, str]:
        fs = sorted(p for p in root.rglob("*") if p.is_file())
        h = hashlib.sha256()
        tot = 0
        for p in fs:
            b = p.read_bytes()
            tot += len(b)
            h.update(p.relative_to(root).as_posix().encode() + b)
        return len(fs), tot, h.hexdigest()

    surface = json.loads((BASE / "ord0263_landedgen_surface_receipt.json").read_text(encoding="utf-8"))
    before = surface["generation"]
    n_after, b_after, t_after = tree_digest(LIVE_DIST) if (LIVE_DIST / "index.html").is_file() else (0, 0, "")
    same_as_before = (n_after, b_after, t_after) == (before["files"], before["bytes"], before["tree_sha256"])
    served = re.findall(r'assets/index-[A-Za-z0-9_-]+\.(?:js|css)',
                        (LIVE_DIST / "index.html").read_text(encoding="utf-8")) \
        if (LIVE_DIST / "index.html").is_file() else []
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "order": "ORD-0263 landedgen teardown",
           "ports_i_owned_and_stopped": killed, "ports_still_listening_after": still,
           "forbidden_or_other_lane_ports_observed_only": observed,
           "user_chain": {"ports_signalled": [], "db_files_opened": [], "demo_reset_issued": False,
                          "tunnel_or_proxy_touched": False},
           "named_removals": removed, "bytes_freed": freed,
           "live_source_untouched": {
               "path": str(LIVE_DIST),
               "root_is_readable": LIVE_DIST.is_dir() and (LIVE_DIST / "index.html").is_file(),
               "rehashed_after_teardown": {"files": n_after, "bytes": b_after, "tree_sha256": t_after},
               "recorded_before_run": {"files": before["files"], "bytes": before["bytes"],
                                       "tree_sha256": before["tree_sha256"]},
               "byte_identical_to_before": same_as_before,
               "served_refs_still": served,
               "note": "first draft of this check asked is_file() of a DIRECTORY and so reported the "
                       "source as unreadable; that was my bug, corrected here and re-measured by re-hash",
               "why_i_may_delete_my_copy": "digest-proven duplicate recorded in "
                                           "ord0263_landedgen_surface_receipt.json and republished in "
                                           "this run's index"},
           "kept": ["all ord0263_* captures/verdicts/receipts", "tools/*", "repo/ (compat/ord0254 @ "
                    "6a39c527f2aa3b16e73dfd122c34d6e6be7102df, porcelain 0 lines)",
                    "db/canary_8411.db"]}
    p = BASE / "ord0263_landedgen_teardown_receipt.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: rec[k] for k in ("ports_i_owned_and_stopped", "ports_still_listening_after",
                                          "bytes_freed", "live_source_untouched")},
                     ensure_ascii=False, indent=1))
    print("receipt:", p.name)
    return 0 if not any(still.values()) and rec["live_source_untouched"]["byte_identical_to_before"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
