"""ORD-0287 判据 1/2/5：从权威尖 45b0a5e2 起一枚 test-only 候选，推到外部可读 ref 并按 https 回读。

只用 plumbing（hash-object / read-tree / update-index / write-tree / commit-tree）：
不碰任何工作树、不 checkout、不动权威线，所以 diff 一定是"只加一个测试文件"。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LANE = Path("D:/moodle/_qoder_f_ord253_20260923")
FILE_LOCAL = Path("D:/moodle/_qoder_f_run/o287_carrier/test_qoder_ord0287_k8_carrier.py")
PATH_IN_REPO = "backend/tests/test_qoder_ord0287_k8_carrier.py"
BASE = "45b0a5e281cae9c37715173afd3ac5778f309ca7"
BASE_MAIN = "416ea4f210e967130710a900cdecd20e7a1b5eca"
BRANCH = "agent/f-0287-k8-carrier"
REMOTE_REF = "refs/heads/review/ord0287-k8-carrier-f"
GR = "Canshu-King/CityNexus"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0287_candidate_commit.json")
MSG = ("test(ord0287): give the plans/generate receipt guard a regression carrier on the shipped line\n\n"
       "The guard `IdempotencyKey.response_json.is_(None)` protects a filled receipt from being rewritten by a\n"
       "later Phase B answer, and ORD-0282 measured it biting on 45b0a5e2 - but nothing on that line keeps it.\n"
       "K1 refuses-by-name (the canonical 409) and byte-compares the foreign receipt; K2 is the positive control\n"
       "so K1 cannot be green by always failing. Removing the half-condition turns K1 red and leaves K2 green.\n"
       "Test-only: no product byte changes, and nothing imported that is absent from this generation.")


def git(*args, binary=False):
    p = subprocess.run(["git", "-C", str(LANE), *[str(a) for a in args]], capture_output=True,
                       text=not binary, encoding=None if binary else "utf-8", errors="replace")
    assert p.returncode == 0, f"git {args[:2]} rc={p.returncode}: {(p.stderr or b'') if binary else p.stderr[:220]}"
    return p.stdout if binary else p.stdout.strip()


def api_ref(ref_path, tries=6):
    tok = Path(r"D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
    for a in range(tries):
        try:
            r = urllib.request.Request(f"https://api.github.com/repos/{GR}/git/ref/{ref_path}")
            r.add_header("Authorization", "Bearer " + tok)
            r.add_header("Accept", "application/vnd.github+json")
            r.add_header("User-Agent", "citynexus-lane-f")
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode()), None
        except Exception as exc:  # noqa: BLE001
            print("  https retry", a + 1, type(exc).__name__, str(exc)[:60])
            time.sleep(2 + 2 * a)
    return None, "exhausted"


content = FILE_LOCAL.read_bytes()
assert b"\r\n" not in content, "SETUP：文件里有 CRLF ⇒ 会以另一种字节入库"
local_sha1 = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()
before = git("status", "--porcelain").splitlines()
print("本机工作树脏行数（plumbing 不该动它）：", len(before))

base_tree = git("rev-parse", BASE + "^{tree}")
idx = Path("D:/moodle/_qoder_f_run/o287_carrier") / f"tmpidx_{uuid.uuid4().hex[:8]}"
env_blob = git("hash-object", "-w", "-t", "blob", str(FILE_LOCAL))
print("hash-object：", env_blob, "== 本机重算：", env_blob == local_sha1)
if idx.exists():
    idx.unlink()
p = subprocess.run(["git", "read-tree", base_tree], cwd=str(LANE), capture_output=True, text=True,
                   env={**dict(__import__("os").environ), "GIT_INDEX_FILE": str(idx)})
assert p.returncode == 0, p.stderr[:200]
p = subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{env_blob},{PATH_IN_REPO}"],
                   cwd=str(LANE), capture_output=True, text=True,
                   env={**dict(__import__("os").environ), "GIT_INDEX_FILE": str(idx)})
assert p.returncode == 0, p.stderr[:200]
new_tree = subprocess.run(["git", "write-tree"], cwd=str(LANE), capture_output=True, text=True,
                          env={**dict(__import__("os").environ), "GIT_INDEX_FILE": str(idx)}).stdout.strip()
idx.unlink()
assert len(new_tree) == 40, new_tree
tip = git("commit-tree", new_tree, "-p", BASE, "-m", MSG)
git("update-ref", "refs/heads/" + BRANCH, tip)
print("候选尖：", tip, "tree", new_tree)

names = git("diff", "--name-only", BASE, tip).splitlines()
numstat = git("diff", "--numstat", BASE, tip)
main_at_tip = git("rev-parse", f"{tip}:backend/app/main.py")
gate_at_tip = git("rev-parse", f"{tip}:backend/tests/test_qoder_ord0272_continuation.py")
carrier_at_tip = git("rev-parse", f"{tip}:{PATH_IN_REPO}")
parents = git("rev-parse", f"{tip}^")
worktree_after = git("status", "--porcelain").splitlines()
test_only = all(n.startswith("backend/tests/") for n in names) and len(names) == 1
print("diff 只含测试文件：", test_only, names)

CITY = Path("D:/moodle/CityNexus")


def city(*args):
    p = subprocess.run(["git", "-C", str(CITY), *[str(a) for a in args]], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    assert p.returncode == 0, f"CityNexus git {args[:2]} rc={p.returncode}: {p.stderr[:220]}"
    return p.stdout.strip()


# 不用 -f：那枚 ref 若已存在（别人的坐标）就让推送失败并停手，绝不覆盖
git("push", "origin", f"refs/heads/{BRANCH}:{REMOTE_REF}")   # 车道仓 origin = 本地 CityNexus 克隆
gh = city("push", "origin", f"{REMOTE_REF}:{REMOTE_REF}")
ls_gh = city("ls-remote", "origin", REMOTE_REF)
ls_local = git("ls-remote", "origin", REMOTE_REF)
print("GitHub ls-remote：", ls_gh.replace("\t", "  "))
print("本地 origin ls-remote：", ls_local.replace("\t", "  "))
https, err = api_ref(REMOTE_REF.replace("refs/heads/", "heads/"))
ext_sha = ((https or {}).get("object") or {}).get("sha")
print("https 回读：", ext_sha, "== 候选尖：", ext_sha == tip)

receipt = {
    "what": "ORD-0287 判据 1/2/5：test-only 候选（父=权威尖）+ 外部 ref 回读",
    "lane": "F 8ccd71d8", "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "criterion_1_branch_from_landed_tip": {
        "read_tip_via": "git rev-parse（本地 origin = D:/moodle/CityNexus 的 GitHub 镜像）+ "
                        "https GET /repos/…/git/ref/heads/mirror/integration-frontend-apple-pass1",
        "base": BASE, "base_parent_read_at": parents, "base_tree": base_tree,
        "base_main_blob": main_at_tip, "base_main_matches": main_at_tip == BASE_MAIN},
    "criterion_2_test_only": {
        "files_changed": names, "numstat": numstat.splitlines(),
        "every_path_under_backend_tests": all(n.startswith("backend/tests/") for n in names),
        "product_files_touched": [n for n in names if not n.startswith("backend/tests/")],
        "gate_0272_file_unchanged": gate_at_tip == "efa783397e6105ca8f15be9a5701e60e5ace0296",
        "main_py_unchanged": main_at_tip == BASE_MAIN},
    "candidate": {"branch": BRANCH, "tip": tip, "tree": new_tree, "parent": BASE,
                  "carrier_blob": carrier_at_tip, "carrier_bytes": len(content),
                  "local_recomputed_blob_sha1": local_sha1,
                  "commit_message_first_line": MSG.splitlines()[0],
                  "created_by": "plumbing only（hash-object/read-tree/update-index/write-tree/commit-tree）；"
                                "任何工作树 0 次 checkout",
                  "lane_worktree_dirty_before": len(before), "lane_worktree_dirty_after": len(worktree_after)},
    "criterion_5_external_readback": {
        "remote_ref": REMOTE_REF,
        "github_ls_remote_line": ls_gh, "local_origin_ls_remote_line": ls_local,
        "github_push_stdout_tail": (gh.splitlines()[-2:] if gh else []),
        "https_route": "GET https://api.github.com/repos/Canshu-King/CityNexus/git/ref/heads/"
                       "review/ord0287-k8-carrier-f",
        "https_sha": ext_sha, "https_error": err,
        "landing_sha_equals_candidate_tip": ext_sha == tip},
    "authoritative_line_writers": "0 次写权威线（只写自己的 review ref）",
}
OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
print("WROTE", OUT, OUT.stat().st_size, "B")
