"""ORD-0549 inventory against the live authoritative tip.

The commander verified his table at 68b5b3cbf4 and published it at da846e54e7; the tip has moved since
and several cells have been taken. This re-answers his own three questions per row, plus one he cannot
have answered at publish time -- whether the cell still exists at all:

1. does that line still carry the inline `zh ? "…" : "…"` pair, and where is it now;
2. if not, is the cell gone because the file now reads the named key (absorbed), or because the text
   moved into some other shape (needs re-reading by a human);
3. do both arms of the named key still equal those two strings byte for byte.

Read-only: every byte comes from `git show <tip>:<path>`, no working tree, no product writes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = "D:/moodle/CityNexus"
TIP_REF = "refs/remotes/origin/mirror/integration-frontend-apple-pass1"
ROWS = Path("D:/moodle/_qoder_lane_heyuegong_20261009/ord0549_rows.json")
OUT_TXT = Path("D:/moodle/_qoder_lane_heyuegong_20261009/ord0549_inventory.txt")
OUT_JSON = Path("D:/moodle/_qoder_lane_heyuegong_20261009/ord0549_inventory.json")

INLINE_PAIR = re.compile(r'zh\s*\?\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"')
DICT_ENTRY = re.compile(r'"([A-Za-z0-9_.]+)"\s*:\s*"((?:[^"\\]|\\.)*)"')
LABEL_ENTRY = re.compile(r'\b([A-Z][A-Z0-9_]*)\s*:\s*\{\s*zh:\s*"((?:[^"\\]|\\.)*)"\s*,\s*en:\s*"((?:[^"\\]|\\.)*)"\s*\}')


def git_show(rev: str, path: str) -> str:
    run = subprocess.run(["git", "-C", REPO, "show", f"{rev}:{path}"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if run.returncode:
        raise RuntimeError(f"git show {rev}:{path} failed: {run.stderr.strip()[:120]}")
    return run.stdout


def main() -> int:
    tip = subprocess.run(
        ["git", "-C", REPO, "rev-parse", "--verify", TIP_REF], capture_output=True, text=True
    ).stdout.strip()
    if len(tip) != 40:
        raise RuntimeError(f"the tip ref did not resolve: {tip!r}")
    rows = json.loads(ROWS.read_text(encoding="utf-8"))

    cache: dict[str, list[str]] = {}

    def lines_of(path: str) -> list[str]:
        if path not in cache:
            try:
                cache[path] = git_show(tip, path).splitlines()
            except RuntimeError:
                cache[path] = []
        return cache[path]

    # Dictionary arms, read once per dictionary file, keyed by the entry name.
    arms: dict[str, list[str]] = {}
    for dictionary in ("frontend/src/i18n/LocaleContext.tsx", "frontend/src/i18n/travelerLabels.ts"):
        for line in lines_of(dictionary):
            for match in DICT_ENTRY.finditer(line):
                arms.setdefault(match.group(1), []).append(match.group(2))
            for match in LABEL_ENTRY.finditer(line):
                arms.setdefault(match.group(1), []).extend([match.group(2), match.group(3)])

    verdicts: dict[str, int] = {}
    results: list[tuple[dict, str]] = []
    report = [
        "ORD-0549 re-inventory on the live authoritative tip.",
        f"tip={tip} (the commander verified at 68b5b3cbf4, published at da846e54e7)",
        f"rows={len(rows)} files={len({row['file'] for row in rows})}",
        "",
    ]

    for row in rows:
        path = row["file"]
        body = lines_of(path)
        inline_at = [
            i + 1 for i, line in enumerate(body)
            for m in INLINE_PAIR.finditer(line)
            if m.group(1) == row["zh_text"] and m.group(2) == row["en_text"]
        ]
        reads_key = any(f't("{row["key"]}")' in line for line in body)
        zh_anywhere = [i + 1 for i, line in enumerate(body) if row["zh_text"] in line]
        key_arms = arms.get(row["key"], [])
        arms_ok = row["zh_text"] in key_arms and row["en_text"] in key_arms

        if inline_at:
            verdict = "STILL_INLINE"
        elif reads_key and arms_ok:
            verdict = "ABSORBED_by_a_lane_reading_the_named_key"
        elif arms_ok:
            verdict = "GONE_no_inline_no_key_read"
        else:
            verdict = "DICTIONARY_ARM_MOVED"

        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        results.append((row, verdict))
        report.append(
            f"{verdict:38} {path}:{row['signpost_line']} key={row['key']}"
        )
        report.append(
            f"{'':38} inline_now={inline_at or 'none'} reads_key_here={reads_key}"
            f" arms_both_present={arms_ok} arm_count={len(key_arms)}"
            f" zh_still_in_file_at={zh_anywhere[:4] or 'none'}"
        )

    report += ["", "counts_by_verdict:"] + [f"  {name} = {count}" for name, count in sorted(verdicts.items())]

    # The instrument's own blind spot, measured rather than assumed: a line can carry two inline pairs,
    # and a scanner that takes only the first match reports the second as missing.
    multi_pair_lines = 0
    for path in {row["file"] for row in rows}:
        for line in lines_of(path):
            if len(INLINE_PAIR.findall(line)) >= 2:
                multi_pair_lines += 1
    report.append(f"lines_carrying_two_or_more_inline_pairs_in_these_files={multi_pair_lines}")

    per_file: dict[str, list[str]] = {}
    for row, verdict in results:
        per_file.setdefault(row["file"], []).append(verdict)
    report += ["", "per_file (what is left for a lane to take):"]
    for name in sorted(per_file, key=lambda item: (-len([v for v in per_file[item] if v == "STILL_INLINE"]), item)):
        still = len([v for v in per_file[name] if v == "STILL_INLINE"])
        report.append(f"  inline_left={still:2d} of {len(per_file[name]):2d}  {name}")

    text = "\n".join(report) + "\n"
    OUT_TXT.write_text(text, encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"tip": tip, "counts": verdicts, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"tip={tip}")
    print(f"wrote {OUT_TXT}")
    for name, count in sorted(verdicts.items(), key=lambda item: -item[1]):
        print(f"  {count:3d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
