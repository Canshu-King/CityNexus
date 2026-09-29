#!/usr/bin/env python3
"""ORD-0440 - do the survey's 14 keys really ship in BOTH languages, in the built bundle?

The standing constraint (re-read from the order's own 硬约束 ①) is that a Chinese addition must have
its English tier in the same artifact, measured rather than promised. The survey's copy lives in
`frontend/src/features/discovery/prepAbandonSurveyCopy.ts` (LocaleContext was hot), so the
whole-file denominator ruler cannot see these keys - this script reads them out of that file's own
`zh`/`en` blocks and then requires each value verbatim inside the bundle `index.html` points at.

    python review/ord0440/survey_pair_check_r1.py --dist frontend/dist \
        --out review/n3_0440_evidence_r1/survey_pair_r1.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KEY_RE = re.compile(r'"(prepSurvey\.[A-Za-z0-9]+)"\s*:\s*"([^"]+)"')
ARM_RE = re.compile(r'\n\s{2}(zh|en):\s*\{')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--dist", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    copy_file = root / "frontend" / "src" / "features" / "discovery" / "prepAbandonSurveyCopy.ts"
    text = copy_file.read_text(encoding="utf-8")

    # split the file on the two arm blocks; a key appearing in both blocks is a pair
    arms: dict[str, dict[str, str]] = {"zh": {}, "en": {}}
    marks = [(m.group(1), m.start()) for m in ARM_RE.finditer(text)]
    for index, (arm, start) in enumerate(marks):
        stop = marks[index + 1][1] if index + 1 < len(marks) else len(text)
        for key, value in KEY_RE.findall(text[start:stop]):
            arms[arm][key] = value

    all_keys = sorted(set(arms["zh"]) | set(arms["en"]))

    index_html = (Path(args.dist) / "index.html").read_text(encoding="utf-8")
    asset = re.search(r'/assets/(index-[^"\']+\.js)', index_html)
    bundle_name = asset.group(1) if asset else None
    bundle = ""
    if bundle_name:
        bundle = (Path(args.dist) / "assets" / bundle_name).read_text(encoding="utf-8", errors="replace")

    rows, both_arms, shipped_both = [], 0, 0
    for key in all_keys:
        zh, en = arms["zh"].get(key), arms["en"].get(key)
        in_pair_window = all(v is not None and 12 <= len(v) <= 70 for v in (zh, en))
        zh_ship = bool(zh and zh in bundle)
        en_ship = bool(en and en in bundle)
        both_arms += int(bool(zh) and bool(en))
        shipped_both += int(zh_ship and en_ship)
        rows.append({
            "key": key,
            "zh_chars": len(zh) if zh else None,
            "en_chars": len(en) if en else None,
            "both_arms_present": bool(zh) and bool(en),
            "inside_the_rulers_12_to_70_window": in_pair_window,
            "zh_value_in_bundle": zh_ship,
            "en_value_in_bundle": en_ship,
        })

    result = {
        "copy_file": str(copy_file.relative_to(root)).replace("\\", "/"),
        "bundle_asset": bundle_name,
        "keys_found": len(all_keys),
        "both_arms": both_arms,
        "shipped_in_both_arms": shipped_both,
        "pairs_missing_an_arm": [r["key"] for r in rows if not r["both_arms_present"]],
        "pairs_outside_the_12_to_70_window": [
            {"key": r["key"], "zh_chars": r["zh_chars"], "en_chars": r["en_chars"]}
            for r in rows
            if not r["inside_the_rulers_12_to_70_window"]
        ],
        "values_not_found_in_bundle": [
            r["key"] for r in rows if not (r["zh_value_in_bundle"] and r["en_value_in_bundle"])
        ],
        "rows": rows,
    }
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(
        f"keys={result['keys_found']} both_arms={both_arms} shipped_both={shipped_both} "
        f"missing_arm={len(result['pairs_missing_an_arm'])} "
        f"outside_window={len(result['pairs_outside_the_12_to_70_window'])} "
        f"values_not_found={len(result['values_not_found_in_bundle'])}"
    )
    for item in result["pairs_outside_the_12_to_70_window"]:
        print("  outside_window", item)
    for item in result["values_not_found_in_bundle"]:
        print("  NOT_IN_BUNDLE", item)
    ok = (
        result["keys_found"] > 0
        and both_arms == result["keys_found"]
        and shipped_both == result["keys_found"]
    )
    print("verdict", "SURVEY_PAIRS_OK" if ok else "SURVEY_PAIRS_RED")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
