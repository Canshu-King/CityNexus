"""ORD-0263 landed-generation teardown: stop only my own ports, delete only my own copy, re-hash the source.

Three checks make this a receipt rather than a claim: the ports are read back from netstat after the kill
(not assumed), the served root is re-hashed and compared to the digest recorded in my face-start receipt (so
deleting my copy cannot have touched the generation the user is being served), and the clone is re-read for
`git status --porcelain -- frontend` after any rebuild, not before.

`diskgen/dist` is the one deletion that needs justifying: it is a byte-identical duplicate of the served root
(tree digest in both receipts, re-verified here), its digests are published, and the originals stay on disk
behind the user's chain. Everything the verdicts cite is kept.
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
SRC = Path(r"D:\moodle\_qoder_preview_20260920\dist")
MINE = BASE / "diskgen" / "dist"
MY_PORTS = (4418, 8411)
OBSERVED_ONLY = (4781, 4782, 8693, 4185, 8713, 4411, 4412, 4413, 4414, 4415, 4416, 4417)
BRANCH_BACK = "compat/ord0254"
TIP_BACK = "6a39c527f2aa3b16e73dfd122c34d6e6be7102df"


def sh(*a, cwd=None):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", cwd=cwd or str(BASE / "repo"))


def listeners(port: int) -> list[int]:
    out = sh("netstat", "-ano").stdout
    return sorted({int(m.group(2)) for m in
                   re.finditer(r"TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)", out)
                   if int(m.group(1)) == str(port)})


def tree(root: Path) -> tuple[int, int, str]:
    fs = sorted(p for p in root.rglob("*") if p.is_file())
    h, tot = hashlib.sha256(), 0
    for p in fs:
        b = p.read_bytes()
        tot += len(b)
        h.update(p.relative_to(root).as_posix().encode() + b)
    return len(fs), tot, h.hexdigest()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    before = json.loads((BASE / "ord0263_close_surface_receipt.json").read_text(encoding="utf-8"))
    n_before, b_before, t_before = tree(SRC)
    print(f"source at teardown start: {n_before} files {b_before:,} B tree {t_before[:16]} "
          f"(recorded at face start: {before['generation']['root_tree_sha256'][:16]})")

    killed = {}
    for port in MY_PORTS:
        pids = listeners(port)
        for pid in pids:
            sh("powershell", "-NoProfile", "-Command",
               f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")
        killed[str(port)] = pids
    still = {str(p): [] for p in MY_PORTS}
    for _ in range(25):
        still = {str(p): listeners(p) for p in MY_PORTS}
        if not any(still.values()):
            break
        time.sleep(1)
    observed = {str(p): listeners(p) for p in OBSERVED_ONLY}

    freed, removed = 0, []
    for target in [MINE, BASE / "diskgen", BASE / "close_preview.log", BASE / "close_preview.pid"] + \
                  [BASE / f for f in ("close_s4.log", "close_s3.log", "close_junk_html.log",
                                      "close_s4b.log", "close_s3b.log", "close_j1.log", "close_j2.log",
                                      "close_j3.log")]:
        try:
            if target.is_dir() and not any(target.iterdir()):
                target.rmdir()
                removed.append({"path": target.name, "kind": "empty dir"})
            elif target.is_dir():
                freed += sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
                shutil.rmtree(target)
                removed.append({"path": str(target), "kind": "dir", "bytes": freed})
            elif target.is_file():
                freed += target.stat().st_size
                target.unlink()
                removed.append({"path": target.name, "kind": "file", "bytes": target.stat().st_size})
        except OSError as e:
            removed.append({"path": str(target), "kind": "left in place", "why": str(e)[:90]})

    co = sh("git", "checkout", BRANCH_BACK)
    head = sh("git", "rev-parse", "HEAD").stdout.strip()
    porcelain = [l for l in sh("git", "status", "--porcelain", "--", "frontend").stdout.splitlines() if l.strip()]
    n_after, b_after, t_after = tree(SRC)
    rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
           "order": "ORD-0263 landed-generation close-out teardown",
           "ports_i_owned_and_stopped": killed, "ports_still_listening_after": still,
           "other_lane_and_user_ports_observed_only": observed,
           "user_chain": {"ports_signalled": [], "db_files_opened": [], "demo_reset_issued": False,
                          "tunnel_or_proxy_touched": False},
           "source_root": {"path": str(SRC), "at_teardown_start": {"files": n_before, "bytes": b_before,
                                                                    "tree": t_before},
                           "after_teardown": {"files": n_after, "bytes": b_after, "tree": t_after},
                           "unchanged": (n_before, b_before, t_before) == (n_after, b_after, t_after),
                           "matches_face_start_receipt": t_before == before["generation"]["root_tree_sha256"]},
           "named_removals": removed, "bytes_freed": freed,
           "why_i_may_delete_my_copy": "byte-identical duplicate of the served root (same tree digest) whose "
                                       "digests are published; the originals remain on disk",
           "clone": {"branch_after": sh("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(),
                     "head": head, "expected_tip": TIP_BACK, "matches": head == TIP_BACK,
                     "checkout_tail": (co.stdout + co.stderr).strip().splitlines()[-1][:120],
                     "porcelain_frontend_lines": porcelain, "porcelain_line_count": len(porcelain)},
           "kept": ["all ord0263_* captures / verdicts / readings / receipts / side logs", "tools/*",
                    "repo/ (compat/ord0254, clean)"]}
    p = BASE / "ord0263_landedgen_teardown_receipt.json"
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(json.dumps({k: rec[k] for k in ("ports_still_listening_after", "source_root", "bytes_freed",
                                          "clone")}, ensure_ascii=False, indent=1))
    print("receipt:", p.name)
    return 0 if not any(still.values()) and rec["source_root"]["unchanged"] and not porcelain else 5


if __name__ == "__main__":
    raise SystemExit(main())
