#!/usr/bin/env python3
"""ORD-0407 ① -- the paired-copy check, run against the bundle this lane builds.

The commander's own ruler is `evidence/cmdr-instruments/bundle_copy_check_r1.py` (blob
699fb64506a035cbe1d70b9b5b3a58b35654a138).  Its 口径 is kept here on purpose: the same regex over
`frontend/src/i18n/LocaleContext.tsx` (a `"key":"value"` entry whose value is 12..70 characters), the
same first `/assets/*.js` taken out of `index.html`, and the same rule -- every captured value has to
appear verbatim in that bundle, so `values_not_found` must be 0.

Two things differ, both named so nobody reads them as the same measurement:
  * it scans a **built artifact on disk** (`--dist`), because this is a candidate ref, not a deployed
    generation.  The commander's ruler reads an asset over HTTP from a serving chain.
  * it also reports, for the keys this order touched, whether **both** arms of the pair are in the
    dictionary and in the bundle.  That is the part the order's constraint ① actually asks for and the
    original ruler cannot see, because its denominator is the whole file, not my diff.

    python review/n3_0407_copy_pair_check_r1.py --dist frontend/dist --out review/evidence/x.json \
        --head <40-hex>
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "frontend" / "src" / "i18n" / "LocaleContext.tsx"
MAP_COPY = ROOT / "frontend" / "src" / "i18n" / "mapPanelCopy.ts"

# The commander's ruler's own pattern, verbatim.
PAIR_RE = re.compile(r'"([a-z][A-Za-z]*\.[A-Za-z]+)"\s*:\s*"([^"]{12,70})"')

# Keys ORD-0407 touched, and where each language lives.  mapPanelCopy.ts keeps the map surface's copy in
# its own file (LocaleContext was hot), so those keys are outside the ruler's file but inside the order.
TOUCHED_LOCALE_KEYS = ["bookings.noStaySub", "bookings.noStayAction"]
TOUCHED_MAP_KEYS = ["noLocationBody"]


def zh_en_arms(path: Path, key: str) -> dict[str, str]:
    """Pull the zh and en arms for one key out of a two-dictionary file, by document order.

    LocaleContext.tsx declares `const en: Dict` first and `const zhCN: Dict` after it, so the first
    hit is English and the second is Chinese.  mapPanelCopy.ts stores both arms on one line as
    `{ zh: "...", en: "..." }`.
    """
    text = path.read_text(encoding="utf-8")
    if path == MAP_COPY:
        m = re.search(rf'{key}: \{{\s*zh: "(.*?)",\s*en: "(.*?)"', text, re.S)
        return {"zh": m.group(1), "en": m.group(2)} if m else {}
    hits = re.findall(rf'"{re.escape(key)}":\s*"(.*?)"', text)
    if len(hits) < 2:
        return {}
    return {"en": hits[0], "zh": hits[1]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--head", default="")
    args = ap.parse_args()

    dist = Path(args.dist)
    index = (dist / "index.html").read_text(encoding="utf-8")
    asset = re.search(r"/assets/[A-Za-z0-9_\-.]+\.js", index).group(0)
    bundle = (dist / asset.lstrip("/")).read_text(encoding="utf-8", errors="replace")

    loc_text = LOCALE.read_text(encoding="utf-8")
    pairs = PAIR_RE.findall(loc_text)
    bykey: dict[str, list[str]] = {}
    for k, v in pairs:
        bykey.setdefault(k, []).append(v)
    hits, misses = [], []
    for k in sorted(bykey):
        for v in bykey[k]:
            (hits if v in bundle else misses).append((k, v))

    touched = []
    for key in TOUCHED_LOCALE_KEYS:
        arms = zh_en_arms(LOCALE, key)
        touched.append(
            {
                "file": str(LOCALE.relative_to(ROOT)).replace("\\", "/"),
                "key": key,
                "arms_found": sorted(arms),
                "both_arms_present": set(arms) == {"zh", "en"},
                "in_bundle": {lang: (val in bundle) for lang, val in arms.items()},
                "counted_by_the_rulers_regex": {
                    lang: bool(PAIR_RE.search(f'"{key}": "{val}"')) for lang, val in arms.items()
                },
            }
        )
    for key in TOUCHED_MAP_KEYS:
        arms = zh_en_arms(MAP_COPY, key)
        touched.append(
            {
                "file": str(MAP_COPY.relative_to(ROOT)).replace("\\", "/"),
                "key": key,
                "note": "outside LocaleContext.tsx, so the commander's ruler does not count it; "
                "checked here against the same bundle",
                "arms_found": sorted(arms),
                "both_arms_present": set(arms) == {"zh", "en"},
                "in_bundle": {lang: (val in bundle) for lang, val in arms.items()},
            }
        )

    out = {
        "tree_head": args.head,
        "dist_asset": asset,
        "bundle_bytes": len(bundle),
        "denominators": {
            "dictionary_pairs": len(pairs),
            "distinct_keys": len(bykey),
            "values_checked": len(hits) + len(misses),
        },
        "values_found_in_built_bundle": len(hits),
        "values_not_found": len(misses),
        "misses": misses[:40],
        "touched_keys": touched,
        "touched_both_arms_ship": all(t.get("in_bundle", {}).get("zh") and t.get("in_bundle", {}).get("en") for t in touched),
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["denominators"], ensure_ascii=False))
    print("values_not_found", out["values_not_found"])
    print("touched_both_arms_ship", out["touched_both_arms_ship"])
    for t in touched:
        print(" ", t["key"], t["arms_found"], t["in_bundle"])
    bad = out["values_not_found"] != 0 or not out["touched_both_arms_ship"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
