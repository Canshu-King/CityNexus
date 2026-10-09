"""ORD-0553-r2 i18n arm: every key this branch calls must exist on BOTH sides of the
dictionary as the authoritative tip serves it.  Reads the tip blob, not the working copy."""
import json
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
TIP = "7f08160743b3b46e600c2c05e6863eaabd722f54"
PANEL = "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx"
DICT = "frontend/src/i18n/LocaleContext.tsx"
OUT = r"D:/moodle/_liangchigong_0553r2_i18n_r1.txt"


def blob(rev):
    return subprocess.run(["git", "-C", REPO, "show", rev], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def run():
    panel_src = blob(sys.argv[1] if len(sys.argv) > 1 else f"{TIP}:{PANEL}")
    if "formatWhen" not in panel_src:
        return {"verdict": "ABORT_WRONG_GENERATION", "note": "panel source read does not carry the change"}
    keys = sorted(set(re.findall(r'\bt\(\s*"([^"]+)"', panel_src)))
    dict_src = blob(f"{TIP}:{DICT}")
    lines = dict_src.splitlines()
    en_start = next(i for i, l in enumerate(lines) if l.startswith("const en: Dict"))
    zh_start = next(i for i, l in enumerate(lines) if l.startswith("const zhCN: Dict"))
    end = next(i for i, l in enumerate(lines) if l.startswith("const dictionaries"))

    def block(start, stop):
        found = {}
        for n in range(start, stop):
            m = re.match(r'\s*"([^"]+)":', lines[n])
            if m:
                found.setdefault(m.group(1), n + 1)
        return found

    en, zh = block(en_start, zh_start), block(zh_start, end)
    rows = [{"key": k, "en_line": en.get(k), "zh_line": zh.get(k),
             "both": k in en and k in zh} for k in keys]
    missing = [r["key"] for r in rows if not r["both"]]
    verdict = "PASS" if not missing else "FAIL"
    text = "\n".join([
        f"# ORD-0553-r2 i18n arm  (tip {TIP})",
        f"panel blob read :: {sys.argv[1] if len(sys.argv) > 1 else TIP + ':' + PANEL}",
        f"keys called by this file :: {len(keys)}",
        f"en dictionary block starts :: {DICT}:{en_start + 1}",
        f"zh dictionary block starts :: {DICT}:{zh_start + 1}",
        f"keys missing on either side :: {len(missing)} {missing}",
        f"verdict :: {verdict}",
        "",
        "key | en line | zh line",
    ] + [f'{r["key"]} | {DICT}:{r["en_line"]} | {DICT}:{r["zh_line"]}' for r in rows])
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text + "\n")
    return {"verdict": verdict, "keys": len(keys), "missing": missing, "out": OUT,
            "newly_called_by_this_change": [k for k in keys if k == "inbox.timePending"]}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False))
    sys.exit(0)
