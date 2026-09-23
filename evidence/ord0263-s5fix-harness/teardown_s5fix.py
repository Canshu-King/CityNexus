"""ORD-0263 s5fix teardown: stop my :4416/:8411, put the clone back, and prove nothing was left dirty.

Order matters here. The working tree currently holds the A-arm mutant *build* in `repo/frontend/dist`
(index-C9iKFFQY.js). The mutant source was already reverted with `git checkout --`, so the sequence is:
return to `compat/ord0254`, rebuild from that tree, and only then read the porcelain count - so the "0 lines"
I report is measured after the experiment, not before it. `dist` is git-ignored, which is exactly why the
rebuild is required for the bundle on disk to match the candidate that was signed.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"D:\moodle\_qoder_harness_ord0254")
REPO = BASE / "repo"
FRONTEND = REPO / "frontend"
MY_PORTS = (4416, 8411)
OBSERVED_ONLY = (4781, 4782, 8693, 4185, 8713, 4411, 4412, 4413, 4414, 4415)
BRANCH_BACK = "compat/ord0254"
TIP_BACK = "6a39c527f2aa3b16e73dfd122c34d6e6be7102df"


def sh(*a, cwd=None):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or str(REPO))


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == str(port)})


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

    co = sh("git", "checkout", BRANCH_BACK)
    head = sh("git", "rev-parse", "HEAD").stdout.strip()
    dirty_before = [l for l in sh("git", "status", "--porcelain", "--", "frontend").stdout.splitlines() if l.strip()]
    b = sh("node", "node_modules/vite/bin/vite.js", "build", cwd=str(FRONTEND))
    refs = re.findall(r"assets/index-[A-Za-z0-9_-]+\.js",
                      (FRONTEND / "dist" / "index.html").read_text(encoding="utf-8"))
    dirty_after = [l for l in sh("git", "status", "--porcelain", "--", "frontend").stdout.splitlines() if l.strip()]
    scratch = [BASE / f"{n}_preview.log" for n in ("s5fix", "aarm")] + \
              [BASE / f"{n}.out" for n in ("s5fix_junk_html", "s5fix_junk_empty", "s5fix_junk_nonjson",
                                           "aarm_junk_html", "s5fix_s3_silent", "s5fix_s4_answered")] + \
              [BASE / f"{n}_preview.pid" for n in ("s5fix", "aarm")]
    freed, removed = 0, []
    for f in scratch:
        if f.is_file():
            try:
                freed += f.stat().st_size
                removed.append(f.name)
                f.unlink()
            except PermissionError:
                removed.append(f.name + " (still held by a just-stopped process, left in place)")
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "order": "ORD-0263 s5fix teardown",
           "ports_i_owned_and_stopped": killed, "ports_still_listening_after": still,
           "other_lane_and_user_ports_observed_only": observed,
           "user_chain": {"ports_signalled": [], "db_files_opened": [], "demo_reset_issued": False,
                          "tunnel_or_proxy_touched": False},
           "clone_returned_to": {"branch": BRANCH_BACK, "head": head, "expected_tip": TIP_BACK,
                                 "matches": head == TIP_BACK,
                                 "checkout_tail": (co.stdout + co.stderr).strip().splitlines()[-1][:120]},
           "candidate_rebuilt": {"vite_rc": b.returncode, "index_asset": refs[:1],
                                 "note": "dist is git-ignored, so the rebuild is what makes the bundle on "
                                         "disk match the signed candidate again instead of my A-arm mutant"},
           "porcelain_frontend": {"before_rebuild": dirty_before, "after_rebuild": dirty_after,
                                  "line_count_after": len(dirty_after)},
           "mutant_status": {"committed": False, "source_reverted": "git checkout -- before this script",
                             "diff_kept_as_evidence": "ord0263_aarm_mutant.diff",
                             "build_replaced": True},
           "named_scratch_removed": removed, "bytes_freed": freed,
           "kept": ["every ord0263_* capture / verdict / receipt / side log", "tools/*", "repo/"]}
    p = BASE / "ord0263_s5fix_teardown_receipt.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: rec[k] for k in ("ports_still_listening_after", "clone_returned_to",
                                          "candidate_rebuilt", "bytes_freed")},
                     ensure_ascii=False, indent=1))
    print("[porcelain -- frontend] after rebuild:", len(dirty_after), "lines")
    print("receipt:", p.name)
    return 0 if not any(still.values()) and head == TIP_BACK and not dirty_after else 5


if __name__ == "__main__":
    raise SystemExit(main())
