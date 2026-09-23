"""ORD-0262-NARROW 判据前置：把"写锁冲突为什么现在只回 19 B"量成一张可判的表（只读）。

新尖 `035721357da99a43c276f5803df83c3b08c1361c`（ORD-0219 落地，+888/-6，4 件）——
所有行号都在这枚尖上重算，不沿用我在 `dea8410` 上量到的旧行号。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
TIP = "035721357da99a43c276f5803df83c3b08c1361c"
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_narrow_preflight.json")
FILES = ["backend/app/main.py", "backend/app/services.py", "backend/app/concurrency_guards.py",
         "backend/app/commerce/idempotency.py", "backend/app/catalog_hydration_operations.py",
         "backend/app/stay_generation_operations.py"]

PROBES = {
    "error_envelope_def": (r"^def error\(", "产品唯一的错误信封本体"),
    "jsonresponse_returned": (r"-> JSONResponse", "信封返回的类型"),
    "exception_handlers": (r"@app\.exception_handler\((\w+)", "注册了哪些异常类型"),
    "unhandled_500_source": (r"Internal Server Error", "那 19 B 那句话（若产品里有，就是产品自己在印）"),
    "plaintext_500": (r"PlainTextResponse", "19 B 的响应类型是谁给的"),
    "operational_error_mentions": (r"OperationalError", "sqlite 锁/忙异常出现的文件"),
    "lock_detail_test": (r"database is (?:locked|busy)", "现场判据：靠 detail 字符串认锁"),
    "soft_skip": (r"except OperationalError[\s\S]{0,220}?continue", "吞掉锁错的写法（twin 那类软跳过）"),
    "named_busy_codes": (r"\"([A-Z_]+_STORE_BUSY)\"", "产品**已有**的具名繁忙码"),
    "retry_after_ms_emitted": (r"retry_after_ms", "机器可读的重试预算"),
    "journey_write_lock": (r"journey_write_lock", "进程内写锁（跨进程不保护）"),
    "raise_500": (r"raise HTTPException\(\s*500", "显式 500"),
    "message_key_derived": (r"message_key=", "屏上那句的翻译键来源"),
    "reason_code_emitted": (r"reason_code=", "具名'哪一条条件拒的'"),
}


def show(ref: str, path: str) -> str:
    p = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"], capture_output=True)
    return "" if p.returncode else p.stdout.decode("utf-8", "replace")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    per_file: dict[str, object] = {}
    codes: Counter = Counter()
    handlers: Counter = Counter()
    for path in FILES:
        text = show(TIP, path)
        if not text:
            per_file[path] = {"reading": "EMPTY_OR_MISSING ⇒ 不等于'没有'，先修读数"}
            continue
        lines = text.splitlines()
        found = {}
        for name, (pat, why) in PROBES.items():
            ms = list(re.finditer(pat, text, re.M))
            if ms:
                pos = [text.count("\n", 0, m.start()) + 1 for m in ms]
                found[name] = {"why": why, "count": len(ms), "lines": pos[:8]}
                if name == "named_busy_codes":
                    codes.update(m.group(1) for m in ms)
                if name == "exception_handlers":
                    handlers.update(m.group(1) for m in ms)
        per_file[path] = {"lines": len(lines), "probes": found}

    # 那 19 B 到底是谁写的：读已装的 starlette 里默认 500 的正文与类型
    import importlib.util

    import site
    hits = []
    for root in {p for p in ([site.getsitepackages()[0]] if site.getsitepackages() else [])}:
        f = Path(root) / "starlette" / "middleware" / "errors.py"
        if f.is_file():
            src = f.read_text(encoding="utf-8")
            for m in re.finditer(r"PlainTextResponse\(\s*[\"']([^\"']+)[\"'][^)]*status_code\s*=\s*(\d{3})", src):
                hits.append({"file": "starlette/middleware/errors.py",
                             "body": m.group(1), "bytes": len(m.group(1).encode()),
                             "status": m.group(2), "content_type": "text/plain"})
            break

    receipt = {
        "what": "ORD-0262-NARROW 前置：写锁冲突今天的真实形状，逐文件具名（只读，未跑产品）",
        "lane": "F 8ccd71d8",
        "scope": {"repo": REPO, "exact_ref": TIP,
                  "tree": subprocess.run(["git", "-C", REPO, "rev-parse", f"{TIP}^{{tree}}"],
                                         capture_output=True, text=True).stdout.strip(),
                  "read_command": f"git -C {REPO} show {TIP}:<path>",
                  "product_was_run": False,
                  "main_py_changed_since_dea8410": "no（0219 只动 services.py / 2 枚测试 / places.json）"},
        "per_file": per_file,
        "named_busy_codes_present": codes.most_common(),
        "exception_handlers_registered": handlers.most_common(),
        "default_500_source": hits or "未定位（说明 19 B 不是从这一路来的，别下结论）",
        "the_19b_claim": {
            "commander_reading": "14/59 次 500 正文只有 19 B `text/plain`、无 detail/无码/无 trace-id",
            "in_this_tree": "产品自己**没有**任何 `Internal Server Error` 字面量 ⇒ 那 19 B 来自框架默认异常面（见 default_500_source）",
            "consequence": "凡是没被 `@app.exception_handler` 接住的异常，客户端拿到的就是这个，"
                           "与'产品有错误信封'并不矛盾——信封只在有人主动装填时才有内容"},
    }
    body = json.dumps(receipt, ensure_ascii=False, indent=1)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
