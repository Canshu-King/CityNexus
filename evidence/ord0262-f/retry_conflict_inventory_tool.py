"""ORD-0262 前置读数：产品**现有**的重试/冲突语义长什么样（只读权威尖，不改任何东西）。

为什么要单独一把：判据得复用产品已有的词汇，不能我自己再造一套 409/503；
而"已有"必须以**具名尖 + 具名行号**说话，不能凭我印象（上次就是这么误报的）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
TIP = "dea8410be809ebf6c5046581873584e9dbf32b64"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_retry_conflict_inventory.json")

FILES = {
    "backend/app/main.py": "产品主体（错误信封、异常处理器、回放）",
    "backend/app/commerce/idempotency.py": "规范化签名 + 已提交回放的词汇",
    "backend/app/commerce/validators.py": "幂等键本身的形状判据",
    "backend/app/concurrency_guards.py": "旅程级写锁",
    "backend/app/db/models.py": "`idempotency_keys` 表（持久化那一侧）",
}

PROBES = {
    "error_envelope_def": (r"^def error\(", "信封函数本体"),
    "error_returns": (r"\berror\(\s*(?:\n\s*)?[\"']([A-Z][A-Z0-9_]{3,})[\"']",
                      "直接 `return error(\"CODE\", …)`（跨行也算）"),
    "httpexception_raises_named": (
        r"raise HTTPException\(\s*(\d{3})\s*,", "位置参数式 raise ⇒ 走通用码映射"),
    "status_args": (r"status=([0-9]{3})", "信封里显式写的 HTTP 状态"),
    "message_key_args": (r"message_key=", "给了翻译键的抛出点"),
    "reason_code_args": (r"reason_code=", "给了「哪一条条件拒的」的抛出点"),
    "retry_after_any": (r"[Rr]etry[_-][Aa]fter", "任何形式的重试提示"),
    "temporal_whitelist": (r"TEMPORAL_REJECTIONS", "具名拒绝白名单出现处"),
    "db_lock_soft_skip": (r"database is (?:locked|busy)", "sqlite 锁的现场判据"),
    "conflict_wording": (r"idempotency key used for a different request",
                         "幂等冲突那句话（产品已有词汇）"),
    "journaling_lock": (r"journey_write_lock", "旅程级写锁"),
    "integrity_error": (r"IntegrityError", "唯一索引撞车后的回滚路径"),
    "retry_after_header_out": (r"[Hh]eaders\[[\"']Retry-After", "把 Retry-After **发出去**的地方"),
    "retry_after_header_in": (r"headers\.get\([\"']Retry-After", "把 Retry-After **读进来**的地方"),
    "sleep_or_backoff": (r"\btime\.sleep\(|backoff|exponential", "产品里有没有自己重试"),
}


def lines_of(ref: str, path: str) -> list[str]:
    raw = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"],
                         capture_output=True).stdout
    return raw.decode("utf-8", "replace").splitlines()


def main() -> int:
    inv: dict = {"what": "ORD-0262 判据前置：产品现有重试/冲突语义的**只读**清单",
                 "lane": "F 8ccd71d8",
                 "scope": {"repo": REPO, "exact_ref": TIP,
                           "resolved_sha": subprocess.run(
                               ["git", "-C", REPO, "rev-parse", TIP],
                               capture_output=True, text=True).stdout.strip(),
                           "tree": subprocess.run(
                               ["git", "-C", REPO, "rev-parse", f"{TIP}^{{tree}}"],
                               capture_output=True, text=True).stdout.strip(),
                           "read_command": f"git -C {REPO} show {TIP}:<path>  (纯对象库，不碰工作树)"}}
    codes: Counter = Counter()
    statuses: Counter = Counter()
    per_file = {}
    for path, why in FILES.items():
        ls = lines_of(TIP, path)
        if not ls:
            per_file[path] = {"why": why, "lines": 0,
                              "reading": "EMPTY_OR_MISSING ⇒ 这一格不算'没有'，先修读数"}
            continue
        text = "\n".join(ls)

        def where(pos: int) -> int:
            return text.count("\n", 0, pos) + 1

        found = {}
        for name, (pat, why_) in PROBES.items():
            ms = list(re.finditer(pat, text, re.M))
            found[name] = {"why": why_, "count": len(ms),
                           "sites": [{"line": where(m.start()),
                                      "snip": ls[where(m.start()) - 1].strip()[:120]}
                                     for m in ms[:8]]}
        for m in re.finditer(r"\berror\(\s*(?:\n\s*)?[\"']([A-Z][A-Z0-9_]{3,})[\"']", text):
            codes[m.group(1)] += 1
        for m in re.finditer(r"status=([0-9]{3})", text):
            statuses[f"信封 status={m.group(1)}"] += 1
        for m in re.finditer(r"raise HTTPException\(\s*(\d{3})", text):
            statuses[f"raise HTTPException({m.group(1)}"] += 1
        per_file[path] = {"why": why, "lines": len(ls),
                          "bytes": len(text.encode("utf-8")), "probes": found}
    inv["per_file"] = per_file
    inv["named_error_codes_top"] = codes.most_common(20)
    inv["named_error_code_total_raises"] = sum(codes.values())
    inv["named_error_code_distinct"] = len(codes)
    inv["status_histogram"] = statuses.most_common()
    inv["status_total_call_sites"] = sum(statuses.values())
    OUT.write_text(json.dumps(inv, ensure_ascii=False, indent=1), encoding="utf-8",
                   newline="\n")
    print(json.dumps({"status_histogram": inv["status_histogram"],
                      "distinct_codes": inv["named_error_code_distinct"],
                      "raises": inv["named_error_code_total_raises"],
                      "top": inv["named_error_codes_top"][:12]}, ensure_ascii=False, indent=1))
    for path, blk in per_file.items():
        print(f"\n## {path}  lines={blk.get('lines')}")
        for name, v in (blk.get("probes") or {}).items():
            print(f"   {name}: {v['count']}  ← {v['why']}")
            for s in v["sites"][:3]:
                print(f"      :{s['line']}  {s['snip']}")
    print("\n## 具名码 top：", inv["named_error_codes_top"][:14])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
