# -*- coding: utf-8 -*-
"""ORD-0555 i18n arm: every key the changed file calls must exist on BOTH sides of the
dictionary as MY branch tip serves it, and the keys this branch adds must be named here.
Reads git blobs, never a working copy."""
import json
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
PANEL = "frontend/src/features/agent/AgentComposer.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
ADDED = ["hub.infeasible", "hub.needsMoreInfo", "hub.assessed"]
OUT = "D:/moodle/_liangchigong_0555_i18n_r1.txt"


def blob(rev):
    p = subprocess.run(["git", "-C", REPO, "show", rev], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit("SHOW_FAIL %s :: %s" % (rev, p.stderr.decode("utf-8", "replace")[:200]))
    return p.stdout.decode("utf-8", "replace")


def main():
    tip, mine = sys.argv[1], sys.argv[2]
    src = blob(f"{mine}:{PANEL}")
    keys = sorted(set(re.findall(r'\bt\(\s*"([^"]+)"', src)))
    lines = blob(f"{mine}:{DICT}").splitlines()
    en0 = next(i for i, l in enumerate(lines) if l.startswith("const en: Dict"))
    zh0 = next(i for i, l in enumerate(lines) if l.startswith("const zhCN: Dict"))
    end = next(i for i, l in enumerate(lines) if l.startswith("const dictionaries"))

    def block(a, b):
        found = {}
        for n in range(a, b):
            m = re.match(r'\s*"([^"]+)":', lines[n])
            if m:
                found.setdefault(m.group(1), n + 1)
        return found

    en, zh = block(en0, zh0), block(zh0, end)
    rows = [{"key": k, "en": en.get(k), "zh": zh.get(k), "both": k in en and k in zh} for k in keys]
    missing = [r["key"] for r in rows if not r["both"]]
    added_ok = {k: (k in en and k in zh) for k in ADDED}
    # the screen text must not move: compare each added key's value to what the inline ternary said
    before_after = []
    for k, old_zh, old_en in [
        ("hub.infeasible", "不可行", "Not feasible"),
        ("hub.needsMoreInfo", "需要更多信息", "Needs more information"),
        ("hub.assessed", "已评估", "Assessed"),
    ]:
        zv = re.findall(r'^\s*"%s": "(.*)",' % re.escape(k), "\n".join(lines[zh0:end]), re.M)
        ev = re.findall(r'^\s*"%s": "(.*)",' % re.escape(k), "\n".join(lines[en0:zh0]), re.M)
        before_after.append({"key": k, "zh_same_as_inline": bool(zv) and zv[0] == old_zh,
                             "en_same_as_inline": bool(ev) and ev[0] == old_en,
                             "zh_line": zh.get(k), "en_line": en.get(k)})
    still_inline = len(re.findall(r'zh \? "', src))
    verdict = "PASS" if not missing and all(added_ok.values()) and all(
        x["zh_same_as_inline"] and x["en_same_as_inline"] for x in before_after) and still_inline == 0 else "FAIL"
    text = "\n".join([
        f"# ORD-0555 i18n arm  (tip {tip}, branch tip {mine})",
        f"keys called by this file :: {len(keys)}",
        f"keys missing on either side :: {len(missing)} {missing}",
        f"keys added by this branch, both sides :: {json.dumps(added_ok, ensure_ascii=False)}",
        f"inline zh-ternaries left in this file :: {still_inline}",
        f"en block starts :: {DICT}:{en0 + 1}",
        f"zh block starts :: {DICT}:{zh0 + 1}",
        "added key | en line | zh line | text unchanged vs the inline string it replaces",
    ] + [f'{x["key"]} | {DICT}:{x["en_line"]} | {DICT}:{x["zh_line"]} | en_same={x["en_same_as_inline"]} zh_same={x["zh_same_as_inline"]}' for x in before_after] + [f"verdict :: {verdict}"])
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    print(json.dumps({"verdict": verdict, "keys": len(keys), "missing": missing,
                      "added": added_ok, "still_inline": still_inline, "out": OUT}, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
