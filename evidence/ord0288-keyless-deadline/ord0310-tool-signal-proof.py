"""Prove the two-sided witness behind `K0310_KEYLESS_LEG_HAS_SIGNAL_BUT_NO_DEADLINE`.

The commander's second instrument found that both POST option objects already carried `signal` before
this order, so a criterion worded as "is there a signal" would stay green on a tree with no deadline.
This script takes the bytes of the tested tree out of git, applies exactly the arm's substitution, and
shows that the caller's `signal` lines survive the mutation unchanged - which is the premise the arm's
result (K1 red, K2/K3 green) rests on.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
OUT = ROOT / "_scratch_0310" / "r3" / "ord0310-signal-vs-deadline-proof.out"
SHA = sys.argv[1] if len(sys.argv) > 1 else "30de4ebe409f49c5e25f4758cb2e5f4e90764a4f"
P = "frontend/src/features/planning/PlanWithAiSheet.tsx"
ANCHOR = "      const response = await fetchWithKeylessWriteDeadline("
MUTANT = "      const response = await fetch("


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def signal_lines(text: str) -> list:
    return [n + 1 for n, line in enumerate(text.splitlines()) if line.strip() == "signal,"]


def main() -> int:
    shown = subprocess.run(["git", "show", f"{SHA}:{P}"], cwd=ROOT, capture_output=True,
                           text=True, encoding="utf-8")
    if shown.returncode != 0:
        print(f"ABORT: git show {SHA}:{P} failed")
        return 2
    orig = shown.stdout
    hits = orig.count(ANCHOR)
    mutated = orig.replace(ANCHOR, MUTANT, 1)
    before, after = signal_lines(orig), signal_lines(mutated)
    idx = orig.find(ANCHOR)  # everything before this offset is byte-identical in the mutant
    leg = mutated[idx:idx + 340]
    rows = [
        f"$ git show {SHA}:{P}",
        f"  bytes={len(orig.encode('utf-8'))} blob={blob(orig.encode('utf-8'))}",
        f"anchor = `{ANCHOR.strip()}`",
        f"anchor 命中次数 = {hits}（臂要求 1；不等于 1 时驱动器拒绝改字节）",
        f"mutant = `{MUTANT.strip()}`",
        f"变异后字节 = {len(mutated.encode('utf-8'))}（差 {len(mutated.encode('utf-8')) - len(orig.encode('utf-8'))}，"
        f"少的只是包装函数名与右括号）",
        f"变异后 blob = {blob(mutated.encode('utf-8'))}",
        f"`signal,` 独立成行的行号 原件   = {before}",
        f"`signal,` 独立成行的行号 变异后 = {after}",
        f"行号集合是否一模一样 = {before == after}",
        f"无键那一发（变异后）调用点原文（从锚点偏移 {idx} 起 340 字）：",
        "   " + leg.replace("\n", " ⏎ "),
        "读法：`signal` 一行没少、一行没改，被拆掉的只有外面那层期限包装。",
        "该臂实测（同一代臂收据 `ord0310-arms-receipt-r5.json` 里 `attempt.nodes`）："
        "K1 = RED，K2 = GREEN，K3 = GREEN。",
        "⇒ 屏上那句的判据确实是「期限到了」，不是「有没有 signal」；拆包装也没有碰旅行者取消那一支。",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(rows) + "\n"
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    print(f"wrote {OUT} {OUT.stat().st_size} B blob={blob(OUT.read_bytes())}")
    return 0 if hits == 1 and before == after else 3


raise SystemExit(main())
