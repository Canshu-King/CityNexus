"""ORD-0402 slice 2 -- dictionary <-> built artifact, value by value, on this lane's own build.

Same judgement the commander already used once (their reading of the deployed generation is
`evidence/cmdr-1825/bundle_copy_check_e7286dfd_r2.json`, blob c8625ceacfee827b23cbe691b345d473086fec7e,
627 pairs / 627 found): every copy string the source declares must be present, byte for byte, in the
bundle a traveller would download -- so a key that exists in one language only, or copy that the
bundler tree-shook away, shows up as a miss instead of as a blank space on screen.

This script states its own denominators (the commander's script is not on any ref this lane can read;
see the ORD-0401 block). It covers two populations:
  * `en` and `zhCN` in `frontend/src/i18n/LocaleContext.tsx`, which now includes this order's
    `nav.trash` pair;
  * every `key: "value"` pair in `frontend/src/features/trash/journeyTrashCopy.ts`, which is lane copy
    and is therefore invisible to a dictionary-only check.

Run it against both bundles: the tip generation served on :4781 (control) and this lane's build on
:4302 (arm). The acceptance is `values_not_found == 0` on the arm, and the arm's miss list equal to the
control's.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

TREE = Path(os.environ.get("ORD0402_TREE", "D:/moodle/_qoder_q_ord0402/wt"))
OUT = Path(os.environ.get("ORD0402_OUT", "D:/moodle/_qoder_q_ord0402_evidence"))
BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4302")
TAG = os.environ.get("ORD0402_TAG", "arm")
PAIRS_RE = re.compile(
    r'^\s{2,4}(?:"([a-zA-Z0-9_.\-]+)"|([a-zA-Z0-9_.\-]+)):\s*(["`])((?:\\.|(?!\3).)*)\3\s*,?\s*$',
    flags=re.M,
)


def dictionary_pairs() -> list[tuple[str, str, str, str]]:
    src = (TREE / "frontend/src/i18n/LocaleContext.tsx").read_text(encoding="utf-8")
    out: list[tuple[str, str, str, str]] = []
    for locale, name in (("en", "en"), ("zh-CN", "zhCN")):
        i = src.index(f"const {name}: Dict = {{")
        j = src.index("\n};", i)
        for m in PAIRS_RE.finditer(src[i + 1 : j]):
            value = m.group(4)
            if value.strip():
                out.append((locale, m.group(1) or m.group(2), "LocaleContext", value))
    return out


def lane_copy_pairs() -> list[tuple[str, str, str, str]]:
    p = TREE / "frontend/src/features/trash/journeyTrashCopy.ts"
    src = p.read_text(encoding="utf-8")
    out = []
    for locale in ("en", "zh-CN"):
        # `en` is written unquoted and `zh-CN` quoted, because a TS key only needs quotes when it
        # carries a hyphen. Both spellings open the same block.
        head = next(h for h in ('  "' + locale + '": {', "  " + locale + ": {") if h in src)
        i = src.index(head)
        j = src.index("\n  },", i)
        for m in PAIRS_RE.finditer(src[i:j]):
            value = m.group(4)
            if value.strip():
                out.append((locale, m.group(1) or m.group(2), "journeyTrashCopy", value))
    return out


def fetch_bundle() -> tuple[str, bytes, str]:
    html = urllib.request.urlopen(f"{BASE}/index.html", timeout=30).read().decode("utf-8", "replace")
    m = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
    if not m:
        raise SystemExit(f"no index asset discoverable at {BASE}")
    body = urllib.request.urlopen(f"{BASE}{m.group(0)}", timeout=60).read()
    return m.group(0), body, body.decode("utf-8", "replace")


def main() -> int:
    asset, body, text = fetch_bundle()
    pairs = dictionary_pairs() + lane_copy_pairs()
    missing = []
    for locale, key, source, value in pairs:
        # A TS string may carry \" for a quote the bundle emits bare; both spellings count as shipped.
        if value in text or value.replace('\\"', '"') in text:
            continue
        missing.append({"locale": locale, "key": key, "module": source, "value": value[:120]})
    per_locale = {}
    for locale in ("en", "zh-CN"):
        total = sum(1 for l, _, _, _ in pairs if l == locale)
        miss = sum(1 for m in missing if m["locale"] == locale)
        per_locale[locale] = {"values": total, "found": total - miss, "not_found": miss}
    report = {
        "tag": TAG,
        "base": BASE,
        "served_asset": asset,
        "bundle_bytes": len(body),
        "sha256_bundle": hashlib.sha256(body).hexdigest(),
        "instrument": "review/ord0402/copy_pair_trash_r1.py (this lane)",
        "populations": {
            "LocaleContext": sum(1 for p in pairs if p[2] == "LocaleContext"),
            "journeyTrashCopy": sum(1 for p in pairs if p[2] == "journeyTrashCopy"),
        },
        "values_checked": len(pairs),
        "distinct_keys": len({k for _, k, _, _ in pairs}),
        "values_found_in_served_bundle": len(pairs) - len(missing),
        "values_not_found": len(missing),
        "per_locale": per_locale,
        "this_orders_copy": [
            {"locale": l, "key": k, "in_bundle": v in text or v.replace('\\"', '"') in text}
            for l, k, _, v in pairs
            if k == "nav.trash" or k.startswith("trash.")
        ],
        "misses": missing[:80],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"copy_pair_{TAG}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k != "misses"}, ensure_ascii=False, indent=2))
    print(f"wrote {path}")
    return 0 if not missing else 3


if __name__ == "__main__":
    sys.exit(main())
