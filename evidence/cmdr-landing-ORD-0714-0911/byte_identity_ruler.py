# -*- coding: utf-8 -*-
"""第廿五波的字面替换对账：每一句要证明三件事，而不是"看着一样"。

1. 现尖字典里的值，在旧尖的应用壳里原本就以同样的字节出现过（改的是搬运，不是改写）；
2. 现尖的应用壳里那一串字面量已经没有了（写者只剩字典一处）；
3. 这一枚键在旧尖的字典里原本不存在（不是我抄了一份留着两处）。

任何一条不成立就 CHECK 并退出非零——一把不会拒绝自己结论的尺，和没有尺一样。
"""
import re
import subprocess
import sys

TIP = "2f9fc88d22658fea9f80f69218aa3fcdc301f692"
OLD = "a8ae9fa6ee2ec7868f46dbd9b93d45dcde4b9d66"
DICT = "frontend/src/i18n/LocaleContext.tsx"
SHELL = "frontend/src/app/V8Experience.tsx"
REPO = "D:/moodle/CityNexus"

KEYS = [
    "demo.notAStage",
    "demo.noSealedJourney",
    "hub.stayWaitingNote",
    "hub.stayFailed",
    "hub.stayEmpty",
    "today.nothingScheduled",
    "itinerary.choosePlanHint",
    "itinerary.candidatePreviewNote",
]

ROW = re.compile(r'^[ \t]*"([^"]+)":[ \t]*"((?:[^"\\]|\\.)*)",[ \t]*$', re.M)


def blob(ref, path):
    r = subprocess.run(["git", "show", "%s:%s" % (ref, path)], cwd=REPO,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise SystemExit("SHOW_FAIL %s:%s :: %s" % (ref, path, r.stderr[:200]))
    return r.stdout.decode("utf-8")


def block(src, start_marker):
    head, rest = src.split(start_marker, 1)
    return rest.split("\n};", 1)[0]


def values(src):
    en = {}
    zh = {}
    for m in ROW.finditer(block(src, "const en: Dict = {")):
        en[m.group(1)] = m.group(2)
    for m in ROW.finditer(block(src, "const zhCN: Dict = {")):
        zh[m.group(1)] = m.group(2)
    if not en or not zh:
        raise SystemExit("DICT_PARSE_BLIND en=%d zh=%d —— 表情感知失败，不许据此说没有" % (len(en), len(zh)))
    return en, zh


def main():
    new_dict = blob(TIP, DICT)
    old_dict = blob(OLD, DICT)
    old_shell = blob(OLD, SHELL)
    new_shell = blob(TIP, SHELL)
    en_new, zh_new = values(new_dict)
    en_old, zh_old = values(old_dict)
    print("tip=%s old=%s" % (TIP, OLD))
    print("dictionary rows read at tip: en=%d zh=%d" % (len(en_new), len(zh_new)))
    print("shell bytes read: old=%d tip=%d" % (len(old_shell), len(new_shell)))
    bad = []
    for k in KEYS:
        v_en, v_zh = en_new.get(k), zh_new.get(k)
        if v_en is None or v_zh is None:
            bad.append("%s missing in tip dictionary" % k)
            print("%-32s MISSING-IN-TIP-DICT" % k)
            continue
        q_en = '"%s"' % v_en
        q_zh = '"%s"' % v_zh
        moved_en, moved_zh = old_shell.count(q_en), old_shell.count(q_zh)
        left_en, left_zh = new_shell.count(q_en), new_shell.count(q_zh)
        existed = k in en_old or k in zh_old
        ok = moved_en == 1 and moved_zh == 1 and left_en == 0 and left_zh == 0 and not existed
        if not ok:
            bad.append("%s: %s" % (k, "not moved cleanly"))
        print("%-32s old-shell-inline=(%d,%d) tip-shell-inline=(%d,%d) key-at-old-tip=%s %s"
              % (k, moved_en, moved_zh, left_en, left_zh, existed, "OK" if ok else "CHECK"))
    print("VERDICT %s" % ("ALL %d KEYS MOVED BYTE-IDENTICALLY, SINGLE WRITER" % len(KEYS)
                          if not bad else "CHECK -- %d key(s) failed" % len(bad)))
    for b in bad:
        print("  FAIL %s" % b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
