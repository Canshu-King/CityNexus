#!/usr/bin/env python3
"""ORD-0225 · 权威 = **已发布在证据分支上**（按 git blob sha1），不是"某个 ref 的祖先"。

Commander 2026-09-23 03:3x 定了两件事：

```text
输入一  CNX_AUTH_REF = Canshu-King/CityNexus @ commander/control
        ⇒ 权威 ref 只用来验"被主张的那件东西有没有发布在这个分支上"（按 git blob sha1）；
          产品候选的权威是一份**已发布的 patch blob**。工作尖 SHA 在 GitHub 上是 422 ——
          这正是 EXTERNALLY_READABLE_EVIDENCE 存在的原因。
输入二  不 push 分支；composite 只差一个路径（尺）⇒ 发布成"两份 patch + 构造器"的坐标，
        外审能自己重算出 ec65a3e。pushed:false 照写，但旁边必须写可审路径。
```

所以本脚本提供三个动作（全部**只读对端**，除了 publish 走 Commander 那份 fail-closed 发布器）：

```text
verify    GET /repos/.../contents/<path>?ref=commander/control，把远端 sha 与本地算出的
          blob sha1 逐字比；比上 = PROVEN，比不上/拿不到 = 具名不成立（不猜、不放行）
bundle    出 composite 的证据包三件：patch、提交档案（含重放自证）、清单
publish   把 bundle 三件交给 live_checks/publish_evidence.py（它自带 fail-closed 内容守卫），
          发布完立刻回读 verify ⇒ 不 publish 就 verify 不过，也就不许开跑
```

退出码：0 成立 ｜ 50 缺参/用法 ｜ 51 打包失败（含重放不等）｜ 52 verify 不成立
        53 发布器拒绝或非预期返回（原样转述，不改写它的判词）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RUNDIR = Path("D:/moodle/_qoder_f_run")
PUBLISHER = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/publish_evidence.py")
TOKEN_FILE = Path("D:/moodle/_qoder_recovery_20260919/.api_tok_20260920")
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"          # 证据分支 —— 权威看这里
RULER_PATH = "backend/tests/_qoder_streak_receipt.py"


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def git(repo: str, *args: str, binary: bool = False):
    p = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{p.stderr.decode('utf-8','replace')[:200]}")
    return p.stdout if binary else p.stdout.decode("utf-8", "replace").strip()


def remote_sha(path: str):
    """只读 GET 证据分支上一个路径的元数据。返回 (状态, 远端 blob sha1 或错误摘要)。

    绝不打印令牌；401/403 一律按"未证实"处理（本机已知：读回路 401 是噪声，不是凭证失败）。
    """
    if not TOKEN_FILE.is_file():
        return "TOKEN_FILE_ABSENT", None
    tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    url = f"https://api.github.com/repos/{REPO}/contents/{path}?ref={BRANCH}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "citynexus-lane-f")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
            return str(r.status), (body.get("sha") if isinstance(body, dict) else None)
    except urllib.error.HTTPError as e:
        return f"HTTP_{e.code}", None
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, None


def do_verify(claims: list[str], sink: list[dict] | None = None) -> int:
    """claims 形如 evidence/x.patch=<expected blob sha1>。sink 非空时把逐项读数塞进去。

    三档判定（**别把"抄来的前缀"读成"没发布"**——ORD-0225 就因为这类误读晚跑了一轮）：
      PROVEN         claim 给满 40 位且与远端逐字相等 ⇒ 唯一能当权威的一档
      PROVEN_PREFIX  claim 只给了 ≥7 位前缀且远端以它开头 ⇒ 回读成立，但**弱一档**，不许喂守卫 22
      NOT_PROVEN     对不上（或读不到）
    """
    unmatched = []
    prefix_only = []
    for c in claims:
        path, _, want = c.partition("=")
        st, got = remote_sha(path)
        full = bool(re.fullmatch(r"[0-9a-f]{40}", want or ""))
        if full:
            ok = bool(got) and got == want
            label = "PROVEN" if ok else "NOT_PROVEN"
        elif want and len(want) >= 7 and got and got.startswith(want):
            ok, label = True, "PROVEN_PREFIX"
            prefix_only.append(path)
        else:
            ok, label = False, "NOT_PROVEN"
        print(f"{label:13} {path}  http={st} remote_sha1={str(got)[:12] or '（无）'} "
              f"claimed={want[:12] or '（未给）'}"
              + ("" if ok else "  ⇒ 对不上")
              + ("  ⇒ 前缀相等，弱一档：**不能**当权威坐标喂守卫 22" if label == "PROVEN_PREFIX" else ""))
        if sink is not None:
            sink.append({"repo_path": path, "http": st, "remote_blob_sha1": got,
                         "claimed_blob_sha1": want or None,
                         "proven": ok, "proven_strict_full_sha1": bool(ok) and full})
        if not ok:
            unmatched.append(path)
    if prefix_only:
        print(f"（{len(prefix_only)} 件只做了前缀回读；要当权威请把 40 位 sha1 传进来）", file=sys.stderr)
    if unmatched:
        print(f"⇒ 52 有 {len(unmatched)} 件完全对不上 ⇒ 不算外部坐标，不许开跑", file=sys.stderr)
        return 52
    return 0


def do_bundle(repo: str, product: str, composite: str) -> int:
    out = RUNDIR / "evidence_pkg"
    out.mkdir(exist_ok=True)
    try:
        prod = git(repo, "rev-parse", "--verify", f"{product}^{{commit}}")
        comp = git(repo, "rev-parse", "--verify", f"{composite}^{{commit}}")
    except RuntimeError as exc:
        print(f"51 {exc}", file=sys.stderr)
        return 51
    names = [x for x in git(repo, "diff", "--name-only", prod, comp).splitlines() if x.strip()]
    if names != [RULER_PATH]:
        print(f"51 composite 相对产品不止多了尺：{names} ⇒ 不打包（归因会被污染）", file=sys.stderr)
        return 51
    patch = git(repo, "diff", prod, comp, binary=True)
    (out / "composite.patch").write_bytes(patch)

    fmt = "%H%n%T%n%P%n%an%n%ae%n%aI%n%cn%n%ce%n%cI%n%B"
    f = git(repo, "show", "-s", f"--format={fmt}", comp).split("\n")
    rec = {"composite_commit": f[0], "tree": f[1], "parent": f[2],
           "author_name": f[3], "author_email": f[4], "author_date_iso": f[5],
           "committer_name": f[6], "committer_email": f[7], "committer_date_iso": f[8],
           "message": "\n".join(f[9:]).rstrip("\n"),
           "product_candidate": prod, "ruler_path": RULER_PATH,
           "patch_bytes": len(patch), "patch_blob_sha1": blob_sha1(patch)}
    # 重放自证：只用档案字段造一次 commit-tree，sha 必须逐字相等，否则"可复算"是空话
    env = dict(os.environ,
               GIT_AUTHOR_NAME=rec["author_name"], GIT_AUTHOR_EMAIL=rec["author_email"],
               GIT_AUTHOR_DATE=rec["author_date_iso"], GIT_COMMITTER_NAME=rec["committer_name"],
               GIT_COMMITTER_EMAIL=rec["committer_email"], GIT_COMMITTER_DATE=rec["committer_date_iso"])
    p = subprocess.run(["git", "-C", repo, "commit-tree", rec["tree"], "-p", rec["parent"],
                        "-m", rec["message"]], capture_output=True, text=True, env=env,
                       encoding="utf-8", errors="replace")
    rec["replayed_commit"] = (p.stdout or "").strip()
    rec["replay_matches"] = rec["replayed_commit"] == rec["composite_commit"]
    (out / "composite_commit_record.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: rec[k] for k in ("composite_commit", "tree", "parent", "product_candidate",
                                          "patch_bytes", "patch_blob_sha1", "replayed_commit",
                                          "replay_matches")}, ensure_ascii=False, indent=2))
    if not rec["replay_matches"]:
        print("51 重放 sha 不等 ⇒ 不能说『外审可复算』，不打包", file=sys.stderr)
        return 51
    print(f"包在 {out}", file=sys.stderr)
    return 0


def do_publish(bundle_prefix: str) -> int:
    """把 bundle 三件交给 Commander 那份 fail-closed 发布器，然后回读 verify。"""
    if not PUBLISHER.is_file():
        print(f"53 发布器不在：{PUBLISHER}", file=sys.stderr)
        return 53
    bundle = RUNDIR / "evidence_pkg"
    # 只发 Commander 授权的三件（对外可见的共享分支，不多写一寸）：
    # patch + 提交档案 + 构造器本身。判级器/审计器/解析器留在账本里给路径，等他点名再发。
    items = [(bundle / "composite.patch", f"{bundle_prefix}composite.patch"),
             (bundle / "composite_commit_record.json",
              f"{bundle_prefix}composite_commit_record.json"),
             (RUNDIR / "o225_composite.sh", f"{bundle_prefix}o225_composite.sh")]
    claims = []
    for local, repo_path in items:
        if not local.is_file():
            print(f"53 要发布的文件不存在：{local}", file=sys.stderr)
            return 53
        want = blob_sha1(local.read_bytes())
        msg = (f"lane F 8ccd71d8: publish (iii) composite evidence "
               f"({local.name}) for ord0225")
        proc = subprocess.run([sys.executable, str(PUBLISHER), str(local), repo_path, msg],
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = (proc.stdout or "").strip().splitlines()[-3:]
        print(f"publish {repo_path}: rc={proc.returncode} | " + " / ".join(tail))
        if proc.returncode != 0:
            print(f"53 发布器拒了或非预期返回（原样转述，不改写它的判词）：{proc.stdout[:300]}"
                  f"{proc.stderr[:200]}", file=sys.stderr)
            return 53
        claims.append(f"{repo_path}={want}")
    print("\n回读 verify：", file=sys.stderr)
    return do_verify(claims)


def do_replay(repo: str, record_path: Path, patch_path: Path) -> int:
    """只靠两件公开文件重算 composite：patch 打在产品树上 ⇒ tree 必须逐字相等；
    再用档案里的作者/提交者/日期/信息 commit-tree ⇒ sha 必须逐字相等。
    全程临时索引，绝不碰真实 .git/index、绝不 checkout。"""
    rec = json.loads(record_path.read_text(encoding="utf-8"))
    prod, want_tree, want_sha = rec["product_candidate"], rec["tree"], rec["composite_commit"]
    idx = Path(RUNDIR / ".o225_replay_index")
    idx.unlink(missing_ok=True)
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    try:
        def run(args):
            p = subprocess.run(["git", "-C", repo, *args], capture_output=True, env=env)
            if p.returncode != 0:
                raise RuntimeError(f"git {' '.join(args)} → {p.stderr.decode('utf-8','replace')[:200]}")
            return p.stdout.decode("utf-8", "replace").strip()
        run(["read-tree", prod])
        apply_patch = subprocess.run(["git", "-C", repo, "apply", "--cached",
                                      str(patch_path.resolve())], capture_output=True, env=env)
        if apply_patch.returncode != 0:
            print(f"51 patch 打不上：{apply_patch.stderr.decode('utf-8','replace')[:240]}",
                  file=sys.stderr)
            return 51
        got_tree = run(["write-tree"])
        meta_env = dict(env,
                        GIT_AUTHOR_NAME=rec["author_name"], GIT_AUTHOR_EMAIL=rec["author_email"],
                        GIT_AUTHOR_DATE=rec["author_date_iso"],
                        GIT_COMMITTER_NAME=rec["committer_name"],
                        GIT_COMMITTER_EMAIL=rec["committer_email"],
                        GIT_COMMITTER_DATE=rec["committer_date_iso"])
        p = subprocess.run(["git", "-C", repo, "commit-tree", got_tree, "-p", prod,
                            "-m", rec["message"]], capture_output=True, text=True, env=meta_env,
                           encoding="utf-8", errors="replace")
        got_sha = (p.stdout or "").strip()
    except RuntimeError as exc:
        print(f"51 重放管道失败：{exc}", file=sys.stderr)
        return 51
    finally:
        idx.unlink(missing_ok=True)
    tree_ok = got_tree == want_tree
    sha_ok = got_sha == want_sha
    print(json.dumps({"from": "patch + commit record only", "replayed_tree": got_tree,
                      "recorded_tree": want_tree, "tree_matches": tree_ok,
                      "replayed_commit": got_sha, "recorded_commit": want_sha,
                      "commit_matches": sha_ok}, ensure_ascii=False, indent=2))
    if not (tree_ok and sha_ok):
        print("51 复算不等 ⇒ 两件公开文件不足以让外审重算，不能声称可复算", file=sys.stderr)
        return 51
    print("⇒ 复算成立：外审只拿 composite.patch + composite_commit_record.json 就能重出同一枚 sha",
          file=sys.stderr)
    return 0


def do_list(prefix: str) -> int:
    """列出证据分支某目录下的文件（只读）。用来回答"C 的 patch 上了没有"。"""
    if not TOKEN_FILE.is_file():
        print("52 TOKEN_FILE_ABSENT ⇒ 无法核验证据分支", file=sys.stderr)
        return 52
    # `contents/evidence/` 带尾斜杠会 404（GitHub 的语义），所以先规范化再问
    prefix = (prefix or "").strip().strip("/")
    tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
    url = f"https://api.github.com/repos/{REPO}/contents/{prefix}?ref={BRANCH}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "citynexus-lane-f")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        print(f"52 HTTP_{e.code} 读不到 {REPO}@{BRANCH}:{prefix}", file=sys.stderr)
        print("   ⇒ **读不到 ≠ 不存在**：先把上一层目录列一遍（`--prefix evidence`）再下"
              "'没发布'的结论，别拿一次 404 当判据", file=sys.stderr)
        return 52
    except Exception as e:  # noqa: BLE001
        print(f"52 {type(e).__name__} 读不到 {REPO}@{BRANCH}:{prefix}", file=sys.stderr)
        print("   ⇒ 同上：网络/工具故障不是'未发布'，要下结论得先拿到清单", file=sys.stderr)
        return 52
    items = body if isinstance(body, list) else [body]
    print(f"{REPO}@{BRANCH}/{prefix} 共 {len(items)} 件：")
    for it in items:
        if isinstance(it, dict):
            print(f"  {it.get('type'):6} {it.get('name')}  sha1={str(it.get('sha'))[:12]} "
                  f"size={it.get('size')}")
    return 0


def do_assert_authority(claims: list[str], composite_patch: str, composite_expected: str,
                        out: str = "") -> int:
    """一条可机判的权威断言：所有列出的东西都必须已在证据分支上、且 blob sha1 逐字相等。"""
    need = list(claims)
    if composite_patch and composite_expected:
        need.append(f"{composite_patch}={composite_expected}")
    if not need:
        print("52 assert-authority 没有任何可核项 ⇒ 权威不成立（不给默认放行）", file=sys.stderr)
        return 52
    # 守卫 22 的输入 ⇒ 只认**满 40 位** blob sha1。do_verify 允许前缀回读是给人看"在不在"，
    # 不是给权威用：拿抄来的 16 位前缀当权威，等于把"我记得的样子"当"外部事实"。
    short = [c for c in need
             if not re.fullmatch(r"[^=]+=[0-9a-f]{40}", c or "")]
    if short:
        print(f"54 有 {len(short)} 项 claim 不是 `路径=<40 位 blob sha1>` ⇒ 权威拒绝成立："
              f"{[s[:60] for s in short]}；前缀回读只能证明'东西在'，不能当闭包坐标", file=sys.stderr)
        return 54
    items: list[dict] = []
    rc = do_verify(need, sink=items)
    receipt = {
        "authority_ref": f"{REPO}@{BRANCH}",
        "authority_meaning": "权威 = 被主张的东西发布在这条证据分支上（按 git blob sha1 逐字比），"
                             "不是某个产品 ref 的祖先（Commander 输入一）",
        "claim_form_required": "路径=<满 40 位 blob sha1>；前缀一律拒绝（rc 54）",
        "pushed": False,
        "push_note": "不 push 新分支（Commander 输入二）。可审路径 = 下面这些已发布 blob + 构造器脚本，"
                     "外审可自己重算 composite sha（o225_evidence.py replay 已自证相等）。",
        "checks": items, "checks_total": len(items),
        "checks_proven": sum(1 for i in items if i.get("proven_strict_full_sha1")),
        "auditable_path": [f"{REPO}@{BRANCH}:{i['repo_path']}#{str(i['remote_blob_sha1'])[:12]}"
                           for i in items if i.get("proven_strict_full_sha1")],
        "proven": rc == 0,
    }
    print(json.dumps({k: receipt[k] for k in ("authority_ref", "pushed", "checks_total",
                                              "checks_proven", "proven")},
                     ensure_ascii=False, indent=2))
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8", newline="\n")
        print(f"权威回执 -> {out}", file=sys.stderr)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["verify", "bundle", "publish", "replay",
                                       "list", "assert-authority"])
    ap.add_argument("--repo", default="D:/moodle/_qoder_f_o210b_20260922")
    ap.add_argument("--product", default="")
    ap.add_argument("--composite", default="")
    ap.add_argument("--prefix", default="evidence/")
    ap.add_argument("--composite-patch", default="")
    ap.add_argument("--composite-blob", default="")
    ap.add_argument("--out", default="", help="assert-authority 的权威回执输出路径")
    ap.add_argument("--record", default=str(RUNDIR / "evidence_pkg/composite_commit_record.json"))
    ap.add_argument("--patch", default=str(RUNDIR / "evidence_pkg/composite.patch"))
    ap.add_argument("--claim", action="append", default=[],
                    help="verify 用：<repo path>=<expected blob sha1>，可重复")
    ap.add_argument("--bundle-prefix", default="evidence/ord0225-composite/")
    args = ap.parse_args()
    if args.action == "list":
        return do_list(args.prefix)
    if args.action == "assert-authority":
        return do_assert_authority(args.claim, args.composite_patch, args.composite_blob, args.out)
    if args.action == "verify":
        if not args.claim:
            print("50 verify 需要至少一个 --claim path=blobsha1", file=sys.stderr)
            return 50
        return do_verify(args.claim)
    if args.action == "replay":
        rec, pat = Path(args.record), Path(args.patch)
        if not (rec.is_file() and pat.is_file()):
            print(f"50 缺复算输入：record={rec.is_file()} patch={pat.is_file()}", file=sys.stderr)
            return 50
        return do_replay(args.repo, rec, pat)
    if args.action == "bundle":
        if not args.product or not args.composite:
            print("50 bundle 需要 --product 与 --composite", file=sys.stderr)
            return 50
        return do_bundle(args.repo, args.product, args.composite)
    return do_publish(args.bundle_prefix)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
