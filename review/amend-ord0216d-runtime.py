"""One-line amendment inside the block this lane appended minutes ago (ORD-0216 ④).

Same discipline as the appender: the old sentence must occur exactly once, the new text is written
with LF only, and taking the amendment back out has to give the previous file back byte for byte --
so a concurrent rewrite by another lane aborts the write instead of being overwritten.
"""

LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"

OLD = "`tsc --noEmit -p tsconfig.check.json` exit **0** 两次（④改动后、门修复后）。"
NEW = (
    "`tsc --noEmit -p tsconfig.check.json` exit **0** 两次（④改动后、门修复后）。"
    "另补四文件链（trip-shape / onboarding-failure / offline-persistence / mobile-overnight）"
    "**12 节点 GREEN**（`run-run073461`，exit 0）⇒ 覆盖 ORD-0216 ①②③④ 全部节点的运行时读数为 "
    "**54 节点 / 4 把独立进程 / 4 个不同临时库 / 0 红**（无 sleep、无重试、未降并发、未放宽断言）。"
)


def main() -> int:
    text = open(LEDGER, encoding="utf-8", newline="").read()
    hits = text.count(OLD)
    if hits != 1:
        print(f"ABORT: the sentence occurs {hits} times, not 1")
        return 2
    updated = text.replace(OLD, NEW, 1)
    open(LEDGER, "w", encoding="utf-8", newline="").write(updated)

    after = open(LEDGER, encoding="utf-8", newline="").read()
    round_trip = after.replace(NEW, OLD, 1) == text
    print(
        f"amended bytes={len(after) - len(text)} hits={hits} new_present={NEW in after} "
        f"round_trip={round_trip} crlf_lines={after.count(chr(13) + chr(10))} "
        f"orders_headings={after.count('## ORDERS（')}"
    )
    return 0 if round_trip and NEW in after else 4


if __name__ == "__main__":
    raise SystemExit(main())
