"""
ORD-0401 -- paired-copy shipping check (this lane's own instrument).

Why this is not the commander's ruler: the order names `bundle_copy_check_e7286dfd_r2.json`
(blob c8625ceacfee827b23cbe691b345d473086fec7e, dictionary_pairs 627 / values_not_found 0) as the
reading to reproduce. That reading's *script* is not on any ref this lane can read -- searched
`origin/commander/control` and the authority line for every path matching `bundle_copy` and
`copy_check`, and the only hits are evidence JSON files, not a `.py`. Rather than invent a number and
call it theirs, this instrument states its own denominators and is then **run against the same bundle
they measured** (the tip generation, `index-Doj2alof.js`) so the two readings can be compared: if my
control run finds the strings they found, the instrument agrees with theirs on the shared population.

Definitions, so the denominators are checkable:
  - dictionary pairs: every `key: "value"` / `key: `value`` entry in the `en` and `zhCN` objects of
    `frontend/src/i18n/LocaleContext.tsx` (both locales counted; 691 en + 692 zh at this rev).
  - lane copy: the zh/en literal pairs this order changed, read from
    `frontend/src/lib/pretripChecklist.ts` and the inline ternaries in the panel.
  - found: the value occurs as a literal byte-for-byte in the bundle text. Placeholder-bearing values
    (`{asked}`) are searched whole. Minification keeps string literals intact, so this is a strict test.

`values_not_found` is reported per locale, and the arm is compared against the control on the *same*
definitions: the acceptance is "the candidate does not lose any string the tip shipped, and ships the
two it changed".
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

TREE = Path(os.environ.get("ORD0401_TREE", "D:/moodle/_qoder_q_ord0401/wt"))
OUT = Path(os.environ.get("ORD0401_OUT", "D:/moodle/_qoder_q_ord0401_evidence"))
BASE = os.environ.get("CNX_BUNDLE_BASE", "http://127.0.0.1:4781")
ASSET = os.environ.get("CNX_BUNDLE_ASSET", "")  # empty -> discover from index.html
TAG = os.environ.get("ORD0401_TAG", "arm")


def dictionary_pairs() -> list[tuple[str, str, str]]:
    src = (TREE / "frontend/src/i18n/LocaleContext.tsx").read_text(encoding="utf-8")
    out: list[tuple[str, str, str]] = []
    for locale, name in (("en", "en"), ("zh-CN", "zhCN")):
        i = src.index(f"const {name}: Dict = {{")
        j = src.index("\n};", i)
        block = src[i + 1 : j]
        for m in re.finditer(
            r'^\s{2}(?:"([a-zA-Z0-9_.\-]+)"|([a-zA-Z0-9_.\-]+)):\s*(["`])((?:\\.|(?!\3).)*)\3\s*,?\s*$',
            block,
            flags=re.M,
        ):
            key = m.group(1) or m.group(2)
            value = m.group(4)
            if not value.strip():
                continue
            out.append((locale, key, value))
    return out


def lane_copy() -> list[tuple[str, str]]:
    """The zh/en pair this order changed, read off the shipped source, plus what it replaced."""
    lib = (TREE / "frontend/src/lib/pretripChecklist.ts").read_text(encoding="utf-8")
    m = re.search(r"export function emptyStateCopy\(zh: boolean\) \{\s*return zh \? \"([^\"]+)\" : \"([^\"]+)\";", lib)
    if not m:
        raise SystemExit("emptyStateCopy no longer matches the shape this check reads -- do not silently pass")
    return [("zh-CN", m.group(1)), ("en", m.group(2))]


def removed_copy() -> list[str]:
    """Strings that must no longer be in the bundle, so the collapse is provably the only change."""
    return [
        "服务端这一代没有报出可行性失败，也没有等待你决定的恢复方案。这里只列契约已经写明依据的两类检查，其余没跑过的检查不会被打勾，也不会出现在这里。",
        "This generation of the plan reports no feasibility failures and no recovery awaiting your decision. Only the two checks whose fields the contract names live here; a check that was not run is never ticked, and never listed.",
    ]


def fetch_bundle() -> tuple[str, bytes, str]:
    html = urllib.request.urlopen(f"{BASE}/index.html", timeout=30).read().decode("utf-8", "replace")
    asset = ASSET
    if not asset:
        m = re.search(r"/assets/index-[A-Za-z0-9_-]+\.js", html)
        if not m:
            raise SystemExit(f"no index asset discoverable at {BASE}")
        asset = m.group(0)
    body = urllib.request.urlopen(f"{BASE}{asset}", timeout=60).read()
    return asset, body, body.decode("utf-8", "replace")


def main() -> int:
    asset, body, text = fetch_bundle()
    pairs = dictionary_pairs()
    lane = lane_copy()
    missing: list[dict[str, str]] = []
    found = 0
    for locale, key, value in pairs:
        # A TS string may carry \" for a quote the bundle emits bare, so both spellings count as
        # shipped. Without this the check reports one phantom miss (`shell.reservationReviewFields`).
        if value in text or value.replace('\\"', '"') in text:
            found += 1
        else:
            missing.append({"locale": locale, "key": key, "value": value[:120]})
    per_locale = {}
    for locale in ("en", "zh-CN"):
        tot = sum(1 for l, _, _ in pairs if l == locale)
        miss = sum(1 for m in missing if m["locale"] == locale)
        per_locale[locale] = {"values": tot, "found": tot - miss, "not_found": miss}
    lane_state = [{"locale": l, "value": v, "in_bundle": v in text} for l, v in lane]
    gone_state = [{"value": v[:70], "still_in_bundle": v in text} for v in removed_copy()]

    report = {
        "tag": TAG,
        "base": BASE,
        "served_asset": asset,
        "bundle_bytes": len(body),
        "sha256_bundle": __import__("hashlib").sha256(body).hexdigest(),
        "instrument": "review/ord0401/copy_pair_check_r1.py (this lane)",
        "dictionary_pairs": len(pairs),
        "distinct_keys": len({k for _, k, _ in pairs}),
        "values_found_in_served_bundle": found,
        "values_not_found": len(missing),
        "per_locale": per_locale,
        "changed_copy_shipped": lane_state,
        "replaced_copy_absent": gone_state,
        "misses": missing[:80],
        "misses_truncated": max(0, len(missing) - 80),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"copy_pair_{TAG}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("misses",)}, ensure_ascii=False, indent=2))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
