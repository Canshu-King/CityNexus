import re, subprocess, sys

KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def load(chunk):
    d = {}
    for line in chunk.split("\n"):
        if line.strip().startswith("//") or line.strip().startswith("*"):
            continue
        m = KEY.match(line)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def halves(src):
    i = src.index("const en: Dict")
    j = src.index("const zhCN: Dict")
    k = src.index("const dictionaries")
    return load(src[i:j]), load(src[j:k])


def report(name, src):
    en, zh = halves(src)
    diff = sorted(set(en) ^ set(zh))
    print("%s | en=%d zh=%d | symmetric_difference=%d %s"
          % (name, len(en), len(zh), len(diff), diff))
    return en, zh


TIP = "ae2d96198bb346af5712810ddad3013928e62aa4"
show = subprocess.run(["git", "-C", r"D:\moodle\CityNexus", "show",
                       TIP + ":frontend/src/i18n/LocaleContext.tsx"],
                      capture_output=True, text=True, encoding="utf-8")
if show.returncode != 0:
    sys.exit("ABORT git show rc=%s %s" % (show.returncode, show.stderr[:200]))
tip_src = show.stdout
if not tip_src:
    sys.exit("ABORT git show returned empty bytes")

mine = open(r"D:\moodle\_qoder_lupaigongjia_0570\frontend\src\i18n\LocaleContext.tsx",
            encoding="utf-8").read()

tip_en, tip_zh = report("tip_" + TIP[:10], tip_src)
my_en, my_zh = report("worktree_0570", mine)

keys = ["pending.title", "pending.sub", "pending.loading"]
for loc, (en, zh) in (("tip", (tip_en, tip_zh)), ("mine", (my_en, my_zh))):
    for key in keys:
        print("%-6s %-16s en=%s zh=%s" % (loc, key,
                                          "HIT" if key in en else "absent",
                                          "HIT" if key in zh else "absent"))
print("delta_en=%+d delta_zh=%+d" % (len(my_en) - len(tip_en), len(my_zh) - len(tip_zh)))
added = sorted(set(my_en) - set(tip_en))
removed = sorted(set(tip_en) - set(my_en))
print("keys_added_on_en_side=%d %s" % (len(added), added))
print("keys_removed_on_en_side=%d %s" % (len(removed), removed))
added_zh = sorted(set(my_zh) - set(tip_zh))
removed_zh = sorted(set(tip_zh) - set(my_zh))
print("keys_added_on_zh_side=%d %s" % (len(added_zh), added_zh))
print("keys_removed_on_zh_side=%d %s" % (len(removed_zh), removed_zh))
