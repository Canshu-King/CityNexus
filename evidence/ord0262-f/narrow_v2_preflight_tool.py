"""ORD-0262-NARROW 判据 v2 的前置读数：行号只在**一枚具名尖**上取，且把 commander/HJ-P3 的三条说法逐条对表。

只读：`git show <ref>:<path>`，不 checkout、不跑产品、不写任何被测文件。
每一条别人的"成因"我都自己复现一遍；复现不出的，两枚读数一起贴，不擅自改谁的数。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/_qoder_integration_20260919"
TIPS = ("dea8410", "035721357da99a43c276f5803df83c3b08c1361c")
TIP = TIPS[1]
OUT = Path("D:/moodle/_qoder_f_run/o225_receipts/ord0262_narrow_v2_preflight.json")
FILES = ["backend/app/main.py", "backend/app/services.py", "backend/app/db/session.py",
         "backend/app/agent/mission.py", "backend/app/agent/runtime.py",
         "frontend/src/features/planning/PlanWithAiSheet.tsx"]


def show(ref: str, path: str) -> str:
    p = subprocess.run(["git", "-C", REPO, "show", f"{ref}:{path}"], capture_output=True)
    return "" if p.returncode else p.stdout.decode("utf-8", "replace")


def blob(ref: str, path: str) -> str:
    p = subprocess.run(["git", "-C", REPO, "rev-parse", f"{ref}:{path}"],
                       capture_output=True, text=True)
    return p.stdout.strip() or "ABSENT"


def enclosing(text: str, line_no: int) -> str:
    """这一行落在哪个 def 里（往上找最近的顶层/缩进 def，带行号，别只给名字）。"""
    lines = text.splitlines()
    for i in range(line_no - 1, -1, -1):
        m = re.match(r"(\s*)(?:async\s+)?def (\w+)", lines[i])
        if m:
            return f"{lines[i].strip()[:70]}  @:{i + 1}"
    return "(找不到 def)"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out: dict = {"what": "0262-NARROW v2 前置：行号逐条重取 + commander/HJ-P3 三说法逐条对表",
                 "lane": "F 8ccd71d8", "scope": {"repo": REPO, "exact_ref": TIP,
                                                 "tree": subprocess.run(
                                                     ["git", "-C", REPO, "rev-parse", f"{TIP}^{{tree}}"],
                                                     capture_output=True, text=True).stdout.strip(),
                                                 "read_command": f"git -C {REPO} show {TIP}:<path>",
                                                 "product_was_run": False}}

    # ① 他说三枚 blob 变了：逐枚在两枚尖上取，看"变"发生在哪一段
    out["blob_check"] = {
        path: {ref.split(":")[-1]: blob(ref, path) for ref in TIPS} for path in FILES}

    main_txt = show(TIP, "backend/app/main.py")
    sites = [(main_txt.count("\n", 0, m.start()) + 1, m.group(0))
             for m in re.finditer(r"create_mission\(", main_txt)]
    out["create_mission_sites_main"] = [
        {"line": ln, "enclosing": enclosing(main_txt, ln)} for ln, _ in sites]
    out["create_mission_site_count"] = len(sites)

    lock = [(main_txt.count("\n", 0, m.start()) + 1)
            for m in re.finditer(r"except OperationalError", main_txt)]
    out["except_operational_error_sites_main"] = lock          # 全文件唯一捕获？让数说话
    out["twin_soft_skip_region"] = [
        {"line": i, "text": ln.strip()} for i, ln in
        enumerate(main_txt.splitlines()[5943:5953], start=5944)]

    svc = show(TIP, "backend/app/services.py")
    gp = [svc.count("\n", 0, m.start()) + 1 for m in re.finditer(r"def generate_plans\(", svc)]
    out["generate_plans_def_line"] = gp
    out["generate_plans_flush_lines"] = [
        {"line": svc.count("\n", 0, m.start()) + 1, "text": m.group(0)}
        for m in re.finditer(r"session\.flush\(\)", svc)][:6]

    ses = show(TIP, "backend/app/db/session.py").splitlines()
    out["session_lock_lines"] = [{"line": i, "text": ln.strip()} for i, ln in enumerate(ses, 1)
                                 if re.search(r"timeout|busy_timeout", ln)][:6]

    sheet = show(TIP, "frontend/src/features/planning/PlanWithAiSheet.tsx").splitlines()
    chain = [{"line": i, "text": ln.strip()} for i, ln in enumerate(sheet, 1)
             if "body?.detail" in ln or "body?.error?.message" in ln or "HTTP ${response.status}" in ln]
    out["frontend_fallback_chain"] = chain
    out["does_the_envelope_reach_the_screen"] = {
        "envelope_body_shape": '{"error": {code,message,message_key,trace_id,details,[reason_code]}}  (main.py:469-478)',
        "reader_uses": [c["line"] for c in chain if "error?.message" in c["text"]],
        "verdict": ("可达：回落链里有一格读 `body?.error?.message` ⇒ 发产品信封，卡上「技术详情」就是服务器那句话"
                    if any("error?.message" in c["text"] for c in chain) else
                    "不可达：链里没有那一格 ⇒ 我发的 message 上不了屏，屏上仍是客户端自造的 HTTP <status>"),
    }

    # ② 词汇：现成的同族码与它们那几格（不许另造第二套）
    busy = [{"line": main_txt.count("\n", 0, m.start()) + 1, "text": ln.strip()[:150]}
            for m in re.finditer(r"\"(HYDRATION_STORE_BUSY|GENERATION_STORE_BUSY)\"", main_txt)
            for ln in [main_txt.splitlines()[main_txt.count("\n", 0, m.start())]]]
    out["existing_busy_codes"] = busy
    out["envelope_def"] = {"line": next(i for i, ln in enumerate(main_txt.splitlines(), 1)
                                        if ln.startswith("def error(")),
                           "assembled_at": [i for i, ln in enumerate(main_txt.splitlines(), 1)
                                            if re.match(r'^\s+"(code|message_key|trace_id|details)",', ln)]}
    body = json.dumps(out, ensure_ascii=False, indent=1)
    OUT.write_text(body, encoding="utf-8", newline="\n")
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
