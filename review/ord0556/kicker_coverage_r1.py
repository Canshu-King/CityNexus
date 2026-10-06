"""ORD-0556 follow-up, seventh leg: how many of the whole-value all-caps dictionary labels are painted
through `.v8-kicker` (the rule that uppercases by CSS)?

Why this is the decisive number: leg six showed the values in the dictionary are Title Case on my tree
while the screen shows caps, because `.v8-kicker { text-transform: uppercase }` paints them. So "fix the
copy" and "fix the screen" are two different jobs, and which job a key needs depends on whether the key is
rendered inside a kicker element. This counts both sides at the live tip, read-only, zero product bytes.

Both sides are read from the same ref in the same run: the dictionary (key -> value, classified by its own
letter case) and every `v8-kicker` occurrence together with the `t("key")` it carries.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT = WT / "review/ord0556/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
DICT = "frontend/src/i18n/LocaleContext.tsx"
ENTRY = re.compile(r'^\s*"([^"]+)":\s*"([^"]*)"\s*,?\s*$')
KICKER = "v8-kicker"
CALL = re.compile(r'\bt\(\s*"([^"]+)"\s*\)')


def git(*a: str) -> str:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e)
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(a)}: {(r.stderr or '')[:160]}")
    return r.stdout


def is_all_caps_label(value: str) -> bool:
    """Whole-value caps: at least one A-Z and no lowercase letter at all.

    The CJK guard is load-bearing. The dictionary holds an English table and a Chinese one, and a Chinese
    sentence that embeds an acronym (`粘贴结构化预订 JSON，...`) has no lowercase ASCII either -- the first
    run of this leg counted those as caps labels and inflated the class (it also let a key whose English
    value is mixed case enter through its Chinese line).
    """
    if re.search(r"[\u4e00-\u9fff]", value):
        return False
    return bool(re.search(r"[A-Z]", value)) and not re.search(r"[a-z]", value)


def kicker_expression(src: list[str], n: int) -> str:
    """The text of the kicker element that starts on line `n` (1-based), and nothing else.

    A fixed look-ahead window over-captures: the first version of this leg took the next three lines, so
    the `<p className="v8-lede">{t("bookings.lede")}</p>` that sits two lines under `bookings.kicker` was
    counted as "painted by the kicker rule". This walks the element instead: from the closing `>` of the
    opening tag to the element's own `</`.
    """
    line = src[n - 1]
    start = line.find(KICKER)
    close = line.find(">", start)
    buf = ""
    i = n
    if close != -1:
        buf = line[close + 1:]
    while i < len(src):
        if "</" in buf:
            return buf[:buf.index("</")]
        if i >= n + 3:
            return buf
        i += 1
        buf += "\n" + src[i - 1]
    return buf


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    dict_src = git("show", f"{tip}:{DICT}").split("\n")
    labels: dict[str, str] = {}
    caps: dict[str, str] = {}
    for n, line in enumerate(dict_src, 1):
        m = ENTRY.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        labels.setdefault(key, value)
        if is_all_caps_label(value):
            caps.setdefault(key, f"{DICT}:{n}")

    paths = [p for p in git("ls-tree", "-r", "--name-only", tip).split("\n")
             if p.startswith("frontend/src/") and p.endswith((".ts", ".tsx"))]
    occurrences = []
    for p in paths:
        src = git("show", f"{tip}:{p}").split("\n")
        for n, line in enumerate(src, 1):
            if KICKER not in line:
                continue
            window = kicker_expression(src, n)
            keys = sorted(set(CALL.findall(window)))
            occurrences.append({"path": p, "line": n, "keys": keys,
                                "expression": window.strip()[:90],
                                "head": line.strip()[:90]})
    kicker_keys = sorted({k for o in occurrences for k in o["keys"]})
    caps_in_kicker = sorted(k for k in caps if k in kicker_keys)
    caps_not_in_kicker = sorted(k for k in caps if k not in kicker_keys)
    unknown = sorted(k for k in kicker_keys if k not in labels)

    doc = {
        "generation": {"run": RUN, "tip": tip, "dictionary": DICT, "read_only": True,
                       "files_scanned": len(paths)},
        "counts": {"dictionary_entries": len(labels), "all_caps_labels": len(caps),
                   "kicker_occurrences": len(occurrences),
                   "kicker_files": len({o["path"] for o in occurrences}),
                   "kicker_distinct_keys": len(kicker_keys),
                   "caps_labels_inside_a_kicker": len(caps_in_kicker),
                   "caps_labels_not_in_any_kicker": len(caps_not_in_kicker),
                   "kicker_keys_missing_from_dictionary": len(unknown)},
        "caps_labels_inside_a_kicker": [{"key": k, "at": caps[k]} for k in caps_in_kicker],
        "caps_labels_not_in_any_kicker": [{"key": k, "at": caps[k]} for k in caps_not_in_kicker],
        "kicker_keys_missing_from_dictionary": unknown,
        "kicker_occurrences": occurrences,
        "verdict": "KICKER_COVERAGE_READ",
    }
    OUT.joinpath(f"kicker_coverage_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(f"tip={tip} files={doc['generation']['files_scanned']} dict_entries={c['dictionary_entries']} "
          f"caps_labels={c['all_caps_labels']} kicker_occurrences={c['kicker_occurrences']} "
          f"kicker_files={c['kicker_files']} kicker_keys={c['kicker_distinct_keys']}")
    print(f"caps_inside_kicker={c['caps_labels_inside_a_kicker']} "
          f"caps_not_in_kicker={c['caps_labels_not_in_any_kicker']} unknown_keys={c['kicker_keys_missing_from_dictionary']}")
    print("receipt kicker_coverage_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
