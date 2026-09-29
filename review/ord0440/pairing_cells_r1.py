#!/usr/bin/env python3
"""ORD-0440 second half - pairing over the tree this lane builds, with the door's own denominator.

Two questions, both measured on the built artifact rather than on the source:

  1. the commander's denominator: every `"key": "value"` pair of 12..70 characters in
     `frontend/src/i18n/LocaleContext.tsx` must appear verbatim in the bundle `index.html` points at;
  2. the module this order added (`prepFailureCopy.ts`) is not in that file, so the denominator cannot
     see it. Its sentences are longer than 70 characters on purpose, which means the pairing window
     misses them too - so this script checks both arms of every key in it and requires each value to
     be in the bundle, and reports how many fall outside the window rather than quietly excluding them.

    python review/ord0440/pairing_cells_r1.py <worktree> <out-json>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve()

PAIR = re.compile(r'"([a-z][A-Za-z]*\.[A-Za-z]+)"\s*:\s*"([^"]{12,70})"')
ENTRY = re.compile(r'^\s*"([A-Za-z_]+)":\s*"([^"]+)",\s*$', re.M)


def main() -> int:
    locale = (ROOT / "frontend/src/i18n/LocaleContext.tsx").read_text(encoding="utf-8")
    pairs = PAIR.findall(locale)
    index = (ROOT / "frontend/dist/index.html").read_text(encoding="utf-8")
    asset = re.search(r"/assets/(index-[^\"']+\.js)", index).group(1)
    bundle = (ROOT / f"frontend/dist/assets/{asset}").read_text(encoding="utf-8", errors="replace")

    missing = [key for key, value in pairs if value not in bundle]

    copy_file = (ROOT / "frontend/src/features/discovery/prepFailureCopy.ts").read_text(encoding="utf-8")
    zh_block = copy_file.split("zh: {", 1)[1].split("\n  },", 1)[0]
    en_block = copy_file.split("en: {", 1)[1].split("\n  },", 1)[0]
    zh = dict(ENTRY.findall(zh_block))
    en = dict(ENTRY.findall(en_block))
    rows = []
    for key in sorted(set(zh) | set(en)):
        z, e = zh.get(key), en.get(key)
        rows.append({
            "key": key,
            "zh_chars": len(z) if z else None,
            "en_chars": len(e) if e else None,
            "both_arms": bool(z) and bool(e),
            "zh_in_bundle": bool(z) and z in bundle,
            "en_in_bundle": bool(e) and e in bundle,
            "inside_the_12_to_70_window": all(v is not None and 12 <= len(v) <= 70 for v in (z, e)),
        })
    result = {
        "bundle_asset": "/assets/" + asset,
        "bundle_bytes": len(bundle.encode("utf-8")),
        "denominator": {"dictionary_pairs": len(pairs),
                        "distinct_keys": len({k for k, _ in pairs}),
                        "values_not_found": len(missing),
                        "missing_keys": missing[:10]},
        "failure_copy": {
            "keys": len(rows),
            "both_arms": sum(1 for r in rows if r["both_arms"]),
            "shipped_in_both_arms": sum(1 for r in rows if r["zh_in_bundle"] and r["en_in_bundle"]),
            "outside_the_window": sum(1 for r in rows if not r["inside_the_12_to_70_window"]),
            "rows": rows,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({"denominator": result["denominator"],
                      "failure_copy": {k: v for k, v in result["failure_copy"].items() if k != "rows"}},
                     ensure_ascii=False))
    ok = result["denominator"]["values_not_found"] == 0 and result["failure_copy"]["both_arms"] == result["failure_copy"]["keys"] \
        and result["failure_copy"]["shipped_in_both_arms"] == result["failure_copy"]["keys"]
    print("verdict", "PAIRING_OK" if ok else "PAIRING_RED")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
