"""ORD-0289 第一步：两代各自从 GitHub tarball 干净导出 frontend/src，并用 GitHub 树对象独立点数。

先读尖（https），再下载，再核对：tarball 字节数 + 每代 frontend/src 下 .ts/.tsx 文件数 ==
`GET /git/trees/<tree>?recursive=1` 里同前缀同后缀的条目数 ⇒ 导出没漏件，才敢拿它当分母。
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RUN = Path("D:/moodle/_qoder_f_run")
OUT = RUN / "o225_receipts/ord0289_exports.json"
GR = "Canshu-King/CityNexus"
TOK = Path(r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-lane-f"}
GENS = {"landed_45b0a5e2": "45b0a5e281cae9c37715173afd3ac5778f309ca7",
        "earlier_dcae1bc9": "dcae1bc964125c3a975916f6bf667794cc19622a"}
MIRROR = "mirror/integration-frontend-apple-pass1"


def api(path, tries=6):
    for a in range(tries):
        try:
            r = urllib.request.Request("https://api.github.com" + path)
            for k, v in HDRS.items():
                r.add_header(k, v)
            with urllib.request.urlopen(r, timeout=120) as resp:
                return json.loads(resp.read().decode()), None
        except Exception as exc:  # noqa: BLE001
            print("  api retry", a + 1, type(exc).__name__, str(exc)[:60])
            time.sleep(2 + 2 * a)
    return None, "exhausted"


def ref_tip(name):
    d, _ = api(f"/repos/{GR}/git/ref/heads/{name}")
    return ((d or {}).get("object") or {}).get("sha")


def commit_of(sha):
    d, err = api(f"/repos/{GR}/git/commits/{sha}")
    return ((d or {}).get("tree") or {}).get("sha"), err


def tree_files(tree_sha, prefix):
    d, err = api(f"/repos/{GR}/git/trees/{tree_sha}?recursive=1")
    if not d:
        return None, err
    out = [e["path"] for e in d.get("tree", [])
           if e.get("type") == "blob" and e["path"].startswith(prefix)
           and (e["path"].endswith(".ts") or e["path"].endswith(".tsx"))
           and not e["path"].endswith(".d.ts")]
    return out, d.get("truncated")


data = {"what": "ORD-0289 导出与分母核对：两代 frontend/src 从 GitHub tarball 干净导出",
        "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gens": {}}
for label, sha in GENS.items():
    dest = RUN / f"o289_{label}"
    tip_now = ref_tip(MIRROR)
    tree, err = commit_of(sha)
    remote_files, truncated = tree_files(tree, "frontend/src/")
    print(f"[{label}] 尖 {sha[:9]} tree {tree[:9]} 权威尖现在={tip_now} 递归树 truncated={truncated}")
    blob = None
    for a in range(4):
        try:
            r = urllib.request.Request(f"https://api.github.com/repos/{GR}/tarball/{sha}")
            for k, v in HDRS.items():
                r.add_header(k, v)
            with urllib.request.urlopen(r, timeout=600) as resp:
                blob = resp.read()
            break
        except Exception as exc:  # noqa: BLE001
            print("  tarball retry", a + 1, type(exc).__name__, str(exc)[:60])
            time.sleep(3 + 3 * a)
    assert blob, f"SETUP：{label} tarball 取不到"
    if dest.exists():
        import shutil
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    picked, members = None, 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        names = [n for n in tf.getnames() if "/frontend/src/" in n]
        members = len([n for n in names if tf.getmember(n).isfile()])
        for ti in tf.getmembers():
            if not ti.isfile() or "/frontend/src/" not in ti.name:
                continue
            rel = "/".join(ti.name.split("/")[1:])          # 去掉 GitHub 的根目录名
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tf.extractfile(ti).read())
        hits = [n for n in names if n.endswith("PlanWithAiSheet.tsx")]
        picked = "/".join(hits[0].split("/")[1:]) if hits else None
    local = sorted(str(p.relative_to(dest / "frontend" / "src")).replace("\\", "/")
                   for p in (dest / "frontend" / "src").rglob("*")
                   if p.is_file() and p.suffix in (".ts", ".tsx") and not p.name.endswith(".d.ts"))
    remote = sorted(f.split("frontend/src/", 1)[1] for f in (remote_files or []))
    entry = {"sha": sha, "tree": tree, "authoritative_tip_read_now": tip_now,
             "tarball_bytes": len(blob), "tarball_sha256_16": hashlib.sha256(blob).hexdigest()[:16],
             "tarball_members_under_frontend_src": members,
             "recursive_tree_entries_frontend_src_ts_tsx": len(remote),
             "tree_truncated": truncated, "export_root_stripped_to": picked,
             "exported_files_local": len(local),
             "local_equals_remote_list": local == remote,
             "only_in_export": sorted(set(local) - set(remote))[:6],
             "only_in_tree": sorted(set(remote) - set(local))[:6],
             "export_dir": str(dest)}
    data["gens"][label] = entry
    print(f"  tarball {len(blob):,} B；树里 {len(remote)} 件；导出 {len(local)} 件；逐名相等={entry['local_equals_remote_list']}")
OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("WROTE", OUT, OUT.stat().st_size, "B")
