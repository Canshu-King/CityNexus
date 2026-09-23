"""0262-NARROW 候选的具名坐标：按 40 位 sha 现取，逐件走 GitHub https 回读 blob 等值，再成文。

为什么要这一份：HJ-P3 的 N1–N4 四问基线卡在她读不到我候选本体这一步（本地 sha 不是坐标）。
所以这里给出的每一枚都必须**已外读成功**才写进表；回读失败的那件直接标 FAIL，不写"应该能读"。
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/_qoder_integration_20260919"
SHA = subprocess.run(["git", "-C", REPO, "rev-parse", "agent/f-ord0262-narrow"],
                     capture_output=True, text=True).stdout.strip()
assert len(SHA) == 40, f"SETUP：分支没解析成 40 位：{SHA!r}"
TREE = subprocess.run(["git", "-C", REPO, "rev-parse", f"{SHA}^{{tree}}"],
                      capture_output=True, text=True).stdout.strip()
PATHS = ["backend/app/main.py",
         "backend/tests/test_qoder_ord0262_narrow_contention.py",
         "backend/app/stay_generation_operations.py",
         "backend/app/catalog_hydration_operations.py",
         "contracts/openapi.yaml",
         "backend/tests/test_qoder_stay_generation_operations.py"]


def token() -> str:
    out = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True).stdout
    return dict(l.split("=", 1) for l in out.splitlines() if "=" in l)["password"].strip()


def local_blob(path: str) -> tuple[str, int]:
    b = subprocess.run(["git", "-C", REPO, "rev-parse", f"{SHA}:{path}"],
                       capture_output=True, text=True).stdout.strip()
    size = int(subprocess.run(["git", "-C", REPO, "cat-file", "-s", b],
                              capture_output=True, text=True).stdout.strip())
    return b, size


tok = token()
rows, ok = [], 0
for p in PATHS:
    want, size = local_blob(p)
    url = (f"https://api.github.com/repos/Canshu-King/CityNexus/contents/{p}?ref={SHA}")
    got, remote_size, how = "", 0, ""
    for attempt in range(1, 4):
        r = urllib.request.Request(url)
        r.add_header("Authorization", "Bearer " + tok)
        r.add_header("Accept", "application/vnd.github+json")
        r.add_header("User-Agent", "lane-f-gate-instrument")
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                d = json.loads(resp.read().decode())
            got, remote_size, how = d.get("sha", ""), d.get("size", 0), f"http={resp.status}"
            break
        except Exception as exc:
            how = f"{type(exc).__name__}"
            time.sleep(5 * attempt)
    equal = got == want and remote_size == size
    ok += 1 if equal else 0
    rows.append({"path": p, "git_blob_sha1": want, "bytes": size, "remote_sha": got,
                 "remote_size": remote_size, "byte_equal": equal, "how": how})
    print(f"{'OK ' if equal else 'FAIL'} {p:58s} blob {want[:16]} size {size} {how}")

ls = subprocess.run(["git", "-C", REPO, "ls-remote",
                     "https://github.com/Canshu-King/CityNexus.git",
                     "refs/heads/review/ord0262-narrow-f"], capture_output=True, text=True).stdout.strip()
sheet = {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
         "branch": "agent/f-ord0262-narrow", "exact_sha": SHA, "tree": TREE,
         "ref": "review/ord0262-narrow-f", "ls_remote_line": ls,
         "readable": f"{ok}/{len(rows)}", "files": rows,
         "raw_urls": [f"https://raw.githubusercontent.com/Canshu-King/CityNexus/{SHA}/{p}"
                      for p in PATHS]}
out = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_narrow_ref_coordinates.json")
out.write_text(json.dumps(sheet, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print(f"\nls-remote: {ls}")
print(f"READABLE {ok}/{len(rows)} → {out.name} ({out.stat().st_size} B)")
