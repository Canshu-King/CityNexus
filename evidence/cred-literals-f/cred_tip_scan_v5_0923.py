"""全尖凭据字面量总数：直接在**对象库**里扫，不靠工作树，也不裸扫文件系统。

为什么这样扫：`a1cc0c1` 的快照导出只有 6,898 个路径，而 `ls-tree` 那一尖有 6,950 个
—— 差的 53 个几乎全是 `review/evidence/**` 里的 **补丁与收据**（当年那次漏就漏在 `.patch`
里套字面量）。 ⇒ 拿快照仓当分母会**少测**，我不能拿它冒充"全尖"。

只读：`git ls-tree -r` 出分母 + `git cat-file --batch` 按 ref 取 blob 字节；不 checkout、
不写盘、不起产品进程。分块喂 + communicate()，避免我自己把管道写死（上一次就死在这）。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
GATE = Path("D:/moodle/_qoder_f_run/snap/cred_gate_v4.py")
CHUNK = 200

spec = importlib.util.spec_from_file_location("cred_gate_v4", GATE)
g = importlib.util.module_from_spec(spec)
sys.modules["cred_gate_v4"] = g
spec.loader.exec_module(g)


def ref_paths(ref: str) -> list[str]:
    """NUL 分隔取全量路径：默认 `--name-only` 会把带特殊字节的名字 **加引号转义**，
    那种字符串再喂回 `cat-file` 就查不到对象 ⇒ 分母会假性变小。用 `-z` 避开。"""
    proc = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", "-z", ref],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"SETUP 失败 ls-tree rc={proc.returncode} "
                         f"{proc.stderr.decode('utf-8','replace')[:200]}")
    return [p for p in proc.stdout.split(b"\0") if p]


def blobs(ref: str, paths: list[bytes]):
    """逐块向 `git cat-file --batch` 取 blob；yield (path_bytes, bytes|None)。

    spec 用**原始字节**拼，避免 ls-tree 与 cat-file 之间再经过一次编码转换而查不到对象。
    """
    prefix = ref.encode("utf-8", "surrogateescape") + b":"
    for i in range(0, len(paths), CHUNK):
        batch = paths[i:i + CHUNK]
        stdin = b"".join(prefix + p + b"\n" for p in batch)
        proc = subprocess.run(["git", "-C", REPO, "cat-file", "--batch"],
                              input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out = proc.stdout  # type: ignore[assignment]
        if proc.returncode != 0:
            raise SystemExit(f"SETUP 失败 cat-file rc={proc.returncode}")
        pos = 0
        for p in batch:
            nl = out.index(b"\n", pos)
            header = out[pos:nl]
            pos = nl + 1
            parts = header.split(b" ")
            if not header.endswith(b" missing") and (len(parts) != 3 or parts[1] != b"blob"):
                raise SystemExit(f"SETUP 失败：cat-file 回了没见过的响应头 {header[:120]!r}"
                                 " ⇒ 字节对不齐，宁可不出数也不报错数")
            if header.endswith(b" missing"):
                yield p, None
                continue
            size = int(parts[2])
            if pos + size > len(out):
                raise SystemExit(f"SETUP 失败：声明 {size} B 但输出只剩 {len(out) - pos} B ⇒ 中止")
            body = out[pos:pos + size]
            pos += size + 1
            yield p, body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="dea8410be809ebf6c5046581873584e9dbf32b64")
    ap.add_argument("--out", default=str(Path("D:/moodle/_qoder_f_run/o225_receipts")
                                         / "cred_tip_scan_receipt_v4.json"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="只扫前 N 个路径：**冒烟用**，收据里会具名标成截断，不得当全尖读数报")
    ap.add_argument("--pathspec", default="",
                    help="逗号分隔的 fnmatch 形（对 `路径` 整体匹配），例：'*.py,*.patch'。"
                         "给了它 ⇒ 这一趟是**限定射程**，收据里连残差一起报")
    args = ap.parse_args()

    paths = ref_paths(args.ref)
    listing_total = len(paths)
    pats = [p.strip() for p in args.pathspec.split(",") if p.strip()]
    excluded: list[str] = []
    if pats:
        import fnmatch

        kept = [p for p in paths
                if any(fnmatch.fnmatch(p.decode("utf-8", "surrogateescape"), pat) for pat in pats)]
        kept_set = set(kept)
        excluded = [p for p in paths if p not in kept_set]
        paths = kept
    if args.limit:
        paths = paths[:args.limit]
    live = g.live_credentials()
    hits: list[dict] = []
    n_bytes = 0
    unreadable: list[str] = []
    non_utf8 = 0
    ext_seen: dict[str, int] = {}
    for idx, (rel_b, body) in enumerate(blobs(args.ref, paths), start=1):
        rel = rel_b.decode("utf-8", "surrogateescape")
        if body is None:
            unreadable.append(rel)
            continue
        n_bytes += len(body)
        suf = Path(rel).suffix.lower() or "(无扩展名)"
        ext_seen[suf] = ext_seen.get(suf, 0) + 1
        try:
            text = body.decode("utf-8")
            clean = True
        except UnicodeDecodeError:
            non_utf8 += 1
            text = body.decode("utf-8", "replace")
            clean = False
        for number, pattern_name, length, token_fp in g.find_credential_shapes(text):
            hits.append({
                "at": f"{rel}:{number}", "shape": pattern_name, "len": length,
                "token_fp": token_fp,
                "loc_fp": hashlib.sha256(f"{rel}:{number}".encode("utf-8")).hexdigest()[:12],
                "utf8_clean": clean,
            })
        if not args.quiet and idx % 1000 == 0:
            print(f"  … {idx}/{len(paths)} 路径 / {n_bytes/1e6:.1f} MB / 命中 {len(hits)}",
                  flush=True)

    rows = g.classify_offenders(hits, live, len(paths))
    verdicts: dict[str, int] = {}
    for r in rows:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    receipt = {
        "what": "全尖凭据字面量**总数**（对象库直读，非工作树、非快照导出）",
        "lane": "F 8ccd71d8",
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "interpreter": sys.version.split()[0],
        "gate_file": {"path": str(GATE), "bytes": GATE.stat().st_size,
                      "git_blob_sha1": subprocess.run(
                          ["git", "-C", REPO, "hash-object", "--no-filters", str(GATE)],
                          capture_output=True, text=True).stdout.strip()},
        "scope": {"repo": REPO, "exact_ref": args.ref,
                  "resolved_sha": subprocess.run(["git", "-C", REPO, "rev-parse", args.ref],
                                                 capture_output=True, text=True).stdout.strip(),
                  "tree": subprocess.run(["git", "-C", REPO, "rev-parse", f"{args.ref}^{{tree}}"],
                                          capture_output=True, text=True).stdout.strip(),
                  "listing_command": f"git -C {REPO} ls-tree -r --name-only -z {args.ref}",
                  "pathspec_patterns": pats or None,
                  "truncated_limit": args.limit or None,
                  "paths_listed_vs_scanned": [listing_total, len(paths)],
                  "full_tip_reading": args.limit == 0 and not pats,
                  "residual_not_read": {
                      "paths": len(excluded),
                      "by_extension": {s: sum(1 for e in excluded
                                              if Path(e.decode('utf-8', 'surrogateescape')).suffix.lower() == s)
                                       for s in sorted({Path(e.decode('utf-8', 'surrogateescape')).suffix.lower()
                                                        for e in excluded})},
                      "meaning": ("限定射程那一趟**必然**有残差：这里是没被读到的路径数与它们的扩展名，"
                                  "不并进命中数也不当作 0" if pats else "全尖那一趟残差应为 0"),
                  },
                  "read_command": f"git -C {REPO} cat-file --batch  (specs = '{args.ref}:<path>', "
                                  f"chunks of {CHUNK}, communicate())"},
        "denominator": {"paths_in_listing": len(paths), "blobs_read": len(paths) - len(unreadable),
                        "blobs_unreadable": len(unreadable), "unreadable_list": unreadable[:40],
                        "bytes_read": n_bytes, "non_utf8_blobs": non_utf8,
                        "extensions_covered": dict(sorted(ext_seen.items(),
                                                          key=lambda kv: -kv[1])),
                        "meaning": (
                            f"**限定射程**：pathspec={pats} 命中 {len(paths)}/{listing_total} 个路径"
                            " ⇒ 这一趟的 shape_hits 只代表**被读到的那部分**，残差见 scope.residual_not_read"
                            if pats else
                            "分母 = 该尖 `ls-tree -r -z` 的**全部**路径 ⇒ 不是限定 pathspec 的抽样；"
                            "每个路径都必须真读到字节，读不到就单列，不并进命中数"
                            if not args.limit else
                            f"**截断冒烟**：只扫了 listing 的前 {len(paths)}/{listing_total} 个路径"
                            " ⇒ 这一趟的 shape_hits **不是**全尖读数，别引用")},
        "live_side": {"credentials_found": len(live), "detail": live},
        "shape_hits": len(hits),
        "classification": rows,
        "by_verdict": verdicts,
        "print_policy": "只印位置/长度/摘要/布尔/计数；原文、前缀、env 值一律不印",
    }
    to_test = {n: v for n in g.LIVE_CREDENTIAL_ENV_VARS if (v := os.environ.get(n) or "")}
    text = json.dumps(receipt, ensure_ascii=False, indent=1)
    leaked = [n for n, v in to_test.items() if v.encode("utf-8") in text.encode("utf-8")]
    shapes = g.find_credential_shapes(text)
    receipt["leak_guard"] = {"values_tested": len(to_test), "matches_found": leaked,
                             "credential_shaped_tokens_in_this_receipt": len(shapes),
                             "note": "只测非空值（空串 `in` 任何字节流恒真 = 假命中）；"
                                     "再用门自己的形状判据反扫这份收据"}
    text = json.dumps(receipt, ensure_ascii=False, indent=1)
    leaked = [n for n, v in to_test.items() if v.encode("utf-8") in text.encode("utf-8")]
    shapes = g.find_credential_shapes(text)
    receipt["leak_guard"]["credential_shaped_tokens_in_this_receipt"] = len(shapes)
    receipt["leak_guard"]["matches_found"] = leaked
    if leaked:
        print(f"REFUSE：收据里出现 {leaked} 的原文 ⇒ 不落盘")
        return 3
    if shapes:
        print(f"REFUSE：收据里还留着 {len(shapes)} 个凭据形状 ⇒ 不落盘")
        return 4
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    print(text if not args.quiet else "")
    print(f"\nWROTE {out} ({out.stat().st_size} B, sha256[:12]="
          f"{hashlib.sha256(out.read_bytes()).hexdigest()[:12]}) 含原文={leaked}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
