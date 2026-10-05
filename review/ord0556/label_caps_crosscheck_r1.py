"""ORD-0556 follow-up, third leg: does the label map still hold at the tip the line is at right now?

token_source_probe_r1.py classified the words against the copy dictionary at the sweep's own generation
(base_tip). Authoritative tips move during a shift, so a claim of "these lines shout" has to be re-read at
a tip fetched now, not inherited. This leg reads refs/heads/HEAD off the remote, fetches exactly that
commit shallowly, and looks every key up again in the English table.

Zero product bytes. Read-only over git objects.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT_DIR = ROOT / "review/ord0556/readouts"
DICT_FILE = "frontend/src/i18n/LocaleContext.tsx"
PROBE = sorted((OUT_DIR).glob("token_source_probe_*.json"))[-1]


def env_clean() -> dict:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    return e


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env_clean())


def main() -> int:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    keys = {}
    for tok, row in probe["per_token"].items():
        for hit in row["dict_en_hits"]:
            if hit["form"] != "LABEL_ALL_CAPS":
                continue
            m = re.match(r'^"([^"]+)"\s*:', hit["text"])
            if not m:
                continue
            key = m.group(1)
            keys.setdefault(key, {"line_at_probe": hit["line"], "tokens": set()})
            keys[key]["tokens"].add(tok)

    tip = (git("ls-remote", "origin", "HEAD").stdout or "").split()
    if not tip or not re.fullmatch(r"[0-9a-f]{40}", tip[0]):
        raise SystemExit("ABORT ls-remote did not return a full 40-hex tip")
    tip_sha = tip[0]
    fr = git("fetch", "--depth=1", "origin", tip_sha)
    if fr.returncode != 0:
        raise SystemExit("ABORT fetch failed: " + (fr.stderr or "")[:200])
    shown = git("show", f"{tip_sha}:{DICT_FILE}")
    if shown.returncode != 0:
        raise SystemExit("ABORT dict file not readable at tip: " + (shown.stderr or "")[:160])
    dict_blob = git("rev-parse", "--verify", f"{tip_sha}:{DICT_FILE}").stdout.strip()
    lines = (shown.stdout or "").split("\n")

    en_open = next(i for i, l in enumerate(lines, 1) if re.match(r"^\s*const en\w*\s*:\s*Dict\s*=\s*\{", l))
    zh_open = next(i for i, l in enumerate(lines, 1) if re.match(r"^\s*const (zhCN|zh)\w*\s*:\s*Dict\s*=\s*\{", l))

    rows = {}
    for n in range(en_open, zh_open):
        m = re.match(r'^\s*"([^"]+)"\s*:\s*"([^"]*)"', lines[n - 1])
        if m and m.group(1) in keys:
            value = m.group(2)
            words = re.findall(r"[A-Za-z][A-Za-z'’-]*", value)
            caps = [w for w in words if w.isupper()]
            form = ("LABEL_ALL_CAPS" if words and len(caps) == len(words)
                    else ("PROSE_WITH_CAPS_WORD" if caps else "PROSE_NO_CAPS"))
            rows[m.group(1)] = {"line_at_tip": n, "value": value[:90], "form_at_tip": form}

    still = sorted(k for k, v in rows.items() if v["form_at_tip"] == "LABEL_ALL_CAPS")
    moved = sorted(set(keys) - set(rows))
    changed = sorted(k for k, v in rows.items() if v["form_at_tip"] != "LABEL_ALL_CAPS")
    doc = {
        "generation": {"tip_from_ls_remote": tip_sha, "dict_blob": dict_blob,
                       "probe_receipt": PROBE.name, "probe_base_tip": probe["generation"]["base_tip"],
                       "recorded_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                       "en_table_line_range_at_tip": [en_open, zh_open - 1]},
        "keys_checked": len(keys),
        "still_all_caps_at_tip": len(still),
        "no_longer_all_caps_at_tip": len(changed),
        "key_not_found_at_tip": len(moved),
        "still_all_caps_keys": {k: rows[k] for k in still},
        "no_longer_all_caps": {k: rows.get(k, {}) for k in changed},
        "not_found": moved,
    }
    out = OUT_DIR / f"label_caps_crosscheck_{doc['generation']['recorded_at']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"receipt": out.name, "tip": tip_sha, "dict_blob": dict_blob,
                      "keys_checked": doc["keys_checked"], "still": doc["still_all_caps_at_tip"],
                      "no_longer": doc["no_longer_all_caps_at_tip"],
                      "not_found": doc["key_not_found_at_tip"]}, ensure_ascii=False))
    for k in still:
        print(f"STILL {k} :{rows[k]['line_at_tip']} {rows[k]['value'][:56]}")
    for k in changed:
        print(f"CHANGED {k} {rows[k].get('form_at_tip')} {rows[k].get('value', '')[:56]}")
    for k in moved:
        print(f"NOT_FOUND {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
