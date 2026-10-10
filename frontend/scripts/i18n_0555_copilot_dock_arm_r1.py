"""ORD-0555 arm: prove the 24 CopilotDock strings landed in the dictionary verbatim.

Fails (exit non-zero, prints the reason) unless:
  A. the two dictionaries still carry identical key sets,
  B. every moved key is absent from the base tip and present on both sides now,
  C. both sides' values are byte-identical to the inline pair that stood at the base tip,
  D. the source now reads t("<key>") once per key and holds no other change to the
     inline-pair inventory (anything left inline must still be inline, same text).
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_REL = "frontend/src/features/agent/CopilotDock.tsx"
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
EVIDENCE = os.path.join(ROOT, "frontend", "scripts", "i18n_0555_copilot_dock_move_evidence_r1.json")
BASE_TIP = json.load(open(EVIDENCE, encoding="utf-8"))["base_tip"]

PAIR = re.compile(r'zh \? "((?:[^"\\]|\\.)*)" : "((?:[^"\\]|\\.)*)"')
VALUE_ON_LINE = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
ENTRY = re.compile(r'^\s*"([^"]+)":\s*(.*)$')

checks = []
failures = []


def note(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        failures.append(name + " :: " + detail)


def git_show(rev, path):
    out = subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, path)],
                         capture_output=True)
    if out.returncode != 0:
        sys.stdout.write("ABORT: git show failed: " + out.stderr.decode("utf-8", "replace") + "\n")
        sys.exit(3)
    return out.stdout.decode("utf-8")


def dicts(text):
    """Read both dictionaries. A value may sit on the key's line or on the next one
    (the file uses both shapes), so the parser has to follow the wrap or it reports a
    parity break for a key that is really present on both sides."""
    i = text.index("const en: Dict = {")
    j = text.index("const zhCN: Dict = {")
    k = text.index("const dictionaries")
    out = {}
    for name, chunk in (("en", text[i:j]), ("zh", text[j:k])):
        lines = chunk.split("\n")
        d = {}
        n = 0
        while n < len(lines):
            m = ENTRY.match(lines[n])
            if not m or lines[n].lstrip().startswith("//"):
                n += 1
                continue
            key, rest = m.group(1), m.group(2).strip()
            if rest:
                v = VALUE_ON_LINE.match(rest)
                d[key] = v.group(1) if v else rest
                n += 1
                continue
            if n + 1 < len(lines):
                v = VALUE_ON_LINE.match(lines[n + 1])
                if v:
                    d[key] = v.group(1)
                    n += 2
                    continue
            n += 1
        out[name] = d
    return out["en"], out["zh"]


def main():
    rows = json.load(open(EVIDENCE, encoding="utf-8"))["items"]
    base_src = git_show(BASE_TIP, SRC_REL)
    now_src = open(os.path.join(ROOT, "frontend", "src", "features", "agent",
                                "CopilotDock.tsx"), encoding="utf-8").read()
    base_en, base_zh = dicts(git_show(BASE_TIP, DICT_REL))
    now_dict = open(os.path.join(ROOT, "frontend", "src", "i18n", "LocaleContext.tsx"),
                    encoding="utf-8").read()
    now_en, now_zh = dicts(now_dict)

    note("dict_key_parity", set(now_en) == set(now_zh),
         "symmetric difference has %d keys" % len(set(now_en) ^ set(now_zh)))

    note("base_pair_inventory", len(rows) == 24, "evidence carries %d rows" % len(rows))

    for row in rows:
        key = row["key"]
        note("absent_at_base_%s" % key, key not in base_en and key not in base_zh,
             "key already existed on the base tip")
        note("present_both_sides_%s" % key, key in now_en and key in now_zh,
             "missing en=%s zh=%s" % (key in now_en, key in now_zh))
        note("verbatim_en_%s" % key, now_en.get(key) == row["en"],
             "dictionary en=%r base inline=%r" % (now_en.get(key), row["en"]))
        note("verbatim_zh_%s" % key, now_zh.get(key) == row["zh"],
             "dictionary zh=%r base inline=%r" % (now_zh.get(key), row["zh"]))
        note("read_once_%s" % key, now_src.count('t("%s")' % key) == 1,
             "site count=%d" % now_src.count('t("%s")' % key))

    untouched = 0
    for m in PAIR.finditer(base_src):
        pair = m.group(0)
        if pair in now_src:
            untouched += 1
    base_pairs = len(PAIR.findall(base_src))
    moved = len(rows)
    note("remaining_inline_pairs", base_pairs - untouched == moved,
         "base=%d still_inline=%d moved=%d" % (base_pairs, untouched, moved))

    note("no_existing_value_changed",
         all(now_en[k] == v for k, v in base_en.items()) and
         all(now_zh[k] == v for k, v in base_zh.items()),
         "an existing key's text moved")
    note("only_new_keys_added",
         set(now_en) - set(base_en) == set(now_zh) - set(base_zh) ==
         set(r["key"] for r in rows),
         "added en=%d added zh=%d expected=%d"
         % (len(set(now_en) - set(base_en)), len(set(now_zh) - set(base_zh)), moved))

    sys.stdout.write("ARM i18n_0555_copilot_dock: %d checks, %d failed\n"
                     % (len(checks), len(failures)))
    for f in failures:
        sys.stdout.write("FAIL " + f + "\n")
    json.dump({"base_tip": BASE_TIP, "checks": checks, "failed": len(failures)},
              open(os.path.join(ROOT, "frontend", "scripts",
                                "i18n_0555_copilot_dock_arm_result_r1.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
