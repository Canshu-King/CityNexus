"""ORD-0465 - the paired-copy check on the artifact that actually ships.

The order's rule is that every new sentence exists on both sides of the dictionary AND can be read out
of the built bundle. "Both sides" is the half that a key added in one language only survives silently:
`t()` falls back to `dictionaries.en[key]`, so a missing Chinese entry renders as English on a Chinese
phone and nothing fails. So this instrument does three things, in this order:

  1. reads the key sets of both dictionary literals and reports the set difference, so a one-sided key
     is named rather than inferred;
  2. reads the values of this order's 28 keys from the source, not from a list written here;
  3. fetches the entry script over the lane's own front (the bytes a browser would run) and requires
     every value, from both languages, to be present in those bytes.

A value that is in the source but not in the bundle means the copy never reached the artifact. A value
that is in the bundle but not in the source means this instrument is lying about where it looked.
"""
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
FRONT = "http://127.0.0.1:4931"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
PREFIX = "shared."


def dictionary_blocks(source: str):
    """The `en` and `zh-CN` object literals, located by their own declarations rather than by line numbers."""
    out = {}
    for name in ("en", "zhCN"):
        start = source.index(f"const {name}: Dict = {{")
        end = source.index("\n};", start)
        out[name] = source[start:end]
    return out


def entries(block: str):
    return dict(re.findall(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)",?$', block, re.M))


def main():
    source = (LANE / "wt/frontend/src/i18n/LocaleContext.tsx").read_text(encoding="utf-8")
    blocks = dictionary_blocks(source)
    en, zh = entries(blocks["en"]), entries(blocks["zhCN"])

    order_keys_en = {k: v for k, v in en.items() if k.startswith(PREFIX)}
    order_keys_zh = {k: v for k, v in zh.items() if k.startswith(PREFIX)}
    only_en = sorted(set(order_keys_en) - set(order_keys_zh))
    only_zh = sorted(set(order_keys_zh) - set(order_keys_en))

    status, shell, _ctype = (lambda r: (r.status, r.read(), r.headers.get("content-type")))(
        OPENER.open(FRONT + "/", timeout=30)
    )
    entry = re.search(rb'src="(?:\./)?(/assets/index-[A-Za-z0-9_-]+\.js)"', shell)
    bundle_status, bundle, _ = (lambda r: (r.status, r.read(), None))(
        OPENER.open(FRONT + entry.group(1).decode(), timeout=60)
    )

    missing_en = sorted(k for k, v in order_keys_en.items() if unescape(v).encode("utf-8") not in bundle)
    missing_zh = sorted(k for k, v in order_keys_zh.items() if unescape(v).encode("utf-8") not in bundle)
    def slots(text):
        # The call-site parameters a line consumes, not the grammar marker. `lib/plural.ts` is
        # explicit that Chinese copy carries no `{plural:…}` marker by construction, so comparing the
        # marker across the two sides reports a difference that the mechanism is designed to have;
        # what must agree is the parameters the call site passes in (`{n}`, `{from}`, …).
        return sorted(
            name
            for name in set(re.findall(r"\{(\w+)(?::[^}]*)?\}", text))
            if name != "plural"
        )

    params_mismatched = sorted(
        key
        for key in set(order_keys_en) & set(order_keys_zh)
        if slots(order_keys_en[key]) != slots(order_keys_zh[key])
    )

    report = {
        "looked_at": {
            "source": "wt/frontend/src/i18n/LocaleContext.tsx",
            "served_shell_http_status": status,
            "entry_asset": entry.group(1).decode() if entry else None,
            "entry_http_status": bundle_status,
            "entry_bytes": len(bundle),
        },
        "keys_this_order_added": len(order_keys_en),
        "dictionary_totals": {"en": len(en), "zh-CN": len(zh)},
        "one_sided_keys": {"en_only": only_en, "zh_only": only_zh},
        "values_not_found_in_the_served_bundle": {"en": missing_en, "zh": missing_zh},
        "params_mismatched": params_mismatched,
    }

    ok = (
        not only_en and not only_zh and not missing_en and not missing_zh
        and not params_mismatched and len(order_keys_en) == len(order_keys_zh)
    )
    report["verdict"] = "ALL_PAIRS_PRESENT_IN_BUNDLE" if ok else "RED"
    out = LANE / "wt/review/ord0465/paired_copy_check_r1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def unescape(text: str) -> str:
    return text.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")


if __name__ == "__main__":
    sys.exit(main())
