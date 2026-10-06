"""ORD-0556 follow-up, eleventh leg: how many of the caps-labelled dictionary values are referenced at all?

Leg seven counted 66 values that carry no lowercase letter, and 7 of them painted through `.v8-kicker`. It
never asked the cheaper question first: are they referenced anywhere? A value no `t("key")` call reaches is
copy that no screen can show, so it is not part of the "machine words on screen" job at all.

Read-only: parse the dictionary at the live tip, then scan every frontend source file at that same tip for
calls that name each key.
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
# Every way this tree asks the dictionary for a string: t("k"), say("k"), copy["k"], dictionaries.en["k"].
CALL = re.compile(r'(?:t|say|copy|dictionaries\.(?:en|zh))\s*(?:\(\s*"|\.?\[\s*")([^"]+)"')


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


def is_all_caps(value: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", value):
        return False
    return bool(re.search(r"[A-Z]", value)) and not re.search(r"[a-z]", value)


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    dict_src = git("show", f"{tip}:{DICT}").splitlines()
    labels: dict[str, str] = {}
    caps: dict[str, str] = {}
    for n, line in enumerate(dict_src, 1):
        m = ENTRY.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2)
        labels.setdefault(key, value)
        if is_all_caps(value):
            caps.setdefault(key, f"{DICT}:{n}")

    # Count any QUOTED OCCURRENCE of the key, not just `t("key")`. The first version of this leg only
    # matched call sites, so keys that live inside a lookup table -- `stateKeyMap` maps an enum to
    # "exec.state.enRoute" as a plain string (V12AuthoritativeJourneyPanel.tsx) -- were reported dead
    # while a screen reads them. The dictionary file itself is excluded, or every key would "match".
    paths = [p for p in git("ls-tree", "-r", "--name-only", tip).split("\n")
             if p.startswith("frontend/src/") and p.endswith((".ts", ".tsx")) and p != DICT]
    refs: dict[str, list[str]] = {}
    for p in paths:
        src = git("show", f"{tip}:{p}")
        for m in CALL.finditer(src):
            key = m.group(1)
            if key in caps:
                line_no = src[:m.start()].count("\n") + 1
                refs.setdefault(key, []).append(f"{p}:{line_no}")
        for key in caps:
            needle = '"' + key + '"'
            start = 0
            while True:
                at = src.find(needle, start)
                if at < 0:
                    break
                start = at + 1
                line_no = src[:at].count("\n") + 1
                site = f"{p}:{line_no}"
                lst = refs.setdefault(key, [])
                if site not in lst:
                    lst.append(site)
                break  # one cite per file is enough to prove the key is reachable

    referenced = sorted(k for k in caps if refs.get(k))
    unreferenced = sorted(k for k in caps if not refs.get(k))
    doc = {"generation": {"run": RUN, "tip": tip, "dictionary": DICT, "read_only": True,
                          "files_scanned": len(paths), "dictionary_entries": len(labels)},
           "counts": {"caps_labels": len(caps), "referenced_somewhere": len(referenced),
                      "never_referenced": len(unreferenced)},
           "referenced": [{"key": k, "at": caps[k], "sites": refs[k][:3],
                           "sites_count": len(refs[k])} for k in referenced],
           "never_referenced": [{"key": k, "at": caps[k]} for k in unreferenced],
           "verdict": "DEAD_COPY_READ"}
    OUT.joinpath(f"dead_copy_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(f"tip={tip} files={len(paths)} dict_entries={len(labels)} caps={c['caps_labels']} "
          f"referenced={c['referenced_somewhere']} never_referenced={c['never_referenced']}")
    print("never_referenced=" + ",".join(unreferenced[:12]))
    print("receipt dead_copy_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
