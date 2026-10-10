"""Prove the six strings moved from sceneClock.ts into LocaleContext.tsx byte-for-byte.

Side A = the inline `zh ? "…" : "…"` pairs as they are on the authoritative tip (read from git).
Side B = the dictionary values my branch puts behind the six new keys (read from the worktree).
Also runs a negative control: corrupt one value in memory and show the ruler turns red,
so "all identical" is a measurement, not a hardcoded verdict.
"""

import re
import subprocess
import sys
import io

TIP = "3bb001aef4e2158dbdc53454ee14d56988f28405"
ROOT = "D:/moodle/_qoder_duibiaogong_0555"
SYS_ENC = sys.stdout.encoding or "utf-8"

PAIRS = [
    (177, "scene.theExecutionCursor"),
    (178, "scene.theJourneySStart"),
    (179, "scene.theServerGaveNoBasis"),
    (184, "scene.theFrozenEvidenceCarriesAnExpiry"),
    (197, "scene.noFrozenEvidenceOnThisTrip"),
    (198, "scene.noScenarioOnStage"),
]

KEY_LINE = re.compile(r'^\s{2}"([^"]+)": "([^"]*)",$', re.M)


def blob(rev, path):
    return subprocess.run(["git", "-C", ROOT, "show", "%s:%s" % (rev, path)],
                          capture_output=True).stdout.decode("utf-8")


def inline_pair(source, lineno):
    """Pull (zh, en) out of one `zh ? "…" : "…"` line exactly as written on the tip."""
    line = source.splitlines()[lineno - 1]
    m = re.search(r'zh\s*\?\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"', line)
    if not m:
        raise AssertionError("no inline bilingual pair at line %d, shape changed: %r" % (lineno, line))
    return m.group(1), m.group(2)


def dicts(path):
    """Split LocaleContext into the en block and the zh-CN block, then key -> value."""
    text = open(path, encoding="utf-8").read()
    en_start = text.index("const en: Dict = {")
    zh_start = text.index("const zhCN: Dict = {")
    en_body = text[en_start:zh_start]
    zh_body = text[zh_start:text.index("const dictionaries")]
    return dict(KEY_LINE.findall(en_body)), dict(KEY_LINE.findall(zh_body))


def main():
    src_tip = blob(TIP, "frontend/src/lib/sceneClock.ts")
    en, zh = dicts(ROOT + "/frontend/src/i18n/LocaleContext.tsx")
    rows = []
    clean = True
    for lineno, key in PAIRS:
        old_zh, old_en = inline_pair(src_tip, lineno)
        new_en = en.get(key)
        new_zh = zh.get(key)
        ok = (new_en == old_en) and (new_zh == old_zh)
        clean = clean and ok
        rows.append((lineno, key, old_zh, new_zh, old_en, new_en, ok))

    print("ruler = review/duibiaogong-0555/verbatim_move_check_r1.py")
    print("side A = git show %s:frontend/src/lib/sceneClock.ts" % TIP[:9])
    print("side B = worktree frontend/src/i18n/LocaleContext.tsx")
    print("")
    for lineno, key, old_zh, new_zh, old_en, new_en, ok in rows:
        print("line %d  key=%s" % (lineno, key))
        print("   zh identical=%s   old=%r  new=%r" % (old_zh == new_zh, old_zh, new_zh))
        print("   en identical=%s   old=%r  new=%r" % (old_en == new_en, old_en, new_en))
    print("")
    print("all_six_identical = %s" % clean)

    # negative control: the ruler must be able to see a wrong value
    saved = en["scene.noScenarioOnStage"]
    en["scene.noScenarioOnStage"] = "no scenario on stage "
    corrupt_red = not all(inline_pair(src_tip, ln)[1] == en.get(k) for ln, k in PAIRS)
    en["scene.noScenarioOnStage"] = saved
    restored_green = all(inline_pair(src_tip, ln)[1] == en.get(k) for ln, k in PAIRS)
    print("negative_control: one trailing space added -> ruler red = %s" % corrupt_red)
    print("negative_control: value restored          -> ruler green = %s" % restored_green)

    residual = [i + 1 for i, ln in enumerate(
        open(ROOT + "/frontend/src/lib/sceneClock.ts", encoding="utf-8").read().splitlines())
        if "zh ?" in ln or ln.strip() == "return zh" or ln.strip().startswith("? ")]
    print("residual inline zh branches left in sceneClock.ts (lines): %s" % residual)

    if not (clean and corrupt_red and restored_green):
        sys.exit(1)
    print("VERDICT = VERBATIM_MOVE_PROVED")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
