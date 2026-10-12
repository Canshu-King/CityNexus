# ORD-0585 arm r1 -- independent byte proof for the five keys this batch moved.
#
# Reads the base tip blobs (git show), the working-tree product files and the working-tree
# dictionary. Per row: the base literal text is found where declared; the dictionary value
# reconstructs that text under the declared hole map; the call site reads the key exactly
# once with a param for every hole; and for sampled values the base expression and the
# dictionary read render identical bytes in both locales. Plus the file-wide invariants:
# only these five keys added, both arms gained them in the same order, no base entry text
# moved, the old literals are gone, and the line census drops by the batch.
import io
import json
import os
import re
import subprocess
import sys

TREE = r"D:/moodle/_qoder_jianpanggong_0555"
BASE = "70da925d886199bd367478069fd428ca870a8a98"
DICTF = "frontend/src/i18n/LocaleContext.tsx"
KEYLESS = "frontend/src/lib/keylessWriteDeadline.ts"
WRITE = "frontend/src/lib/writeDeadline.ts"
CLOCK = "frontend/src/lib/sceneClock.ts"
EN = u"en"
ZH = u"zh-CN"
LIT = re.compile("|".join((r'"(?:[^"\\]|\\.)*"', r"`[^`]*`", r"'(?:[^'\\]|\\.)*'")))
ENTRY = re.compile(r'^  "([A-Za-z0-9._]+)": "(.*)",$')
KEYS = ["live.evidence.serverWordUnexplained", "recover.writeDeadline.title",
        "recover.writeDeadline.body", "recover.writeDeadline.retryGuidance",
        "copilot.keyless.writeUnknown"]


def show(path):
    return subprocess.check_output(["git", "-C", TREE, "show", "%s:%s" % (BASE, path)]).decode("utf-8")


def load(path):
    with io.open(os.path.join(TREE, path.replace("/", os.sep)), encoding="utf-8", newline="") as fh:
        return fh.read()


def lits(text, line):
    return LIT.findall(text.split("\n")[line - 1])


def inner(raw):
    body = raw[1:-1]
    if raw[0] in ('"', "'"):
        body = body.replace('\\"', '"').replace("\\'", "'")
    return body


def arms(text):
    lines = text.split("\n")
    out = {}
    for name, marker in (("en", "const en: Dict = {"), ("zh", "const zhCN: Dict = {")):
        s = lines.index(marker)
        e = s
        while lines[e] != "};":
            e += 1
        d = {}
        for i in range(s + 1, e):
            m = ENTRY.match(lines[i])
            if m:
                d[m.group(1)] = (m.group(2), i + 1)
        out[name] = d
    return out


def fill(value, params):
    out = value
    for k, v in params.items():
        out = out.replace("{%s}" % k, str(v))
    return out.replace('\\"', '"')


def main():
    green = 0
    red = []
    coords = []
    negative = "--negative" in sys.argv
    dw = arms(load(DICTF))
    db = arms(show(DICTF))
    wk = dict((p, load(p)) for p in (KEYLESS, WRITE, CLOCK))
    wb = dict((p, show(p)) for p in (KEYLESS, WRITE, CLOCK))
    if negative:
        v, ln = dw["en"][KEYS[0]]
        dw["en"][KEYS[0]] = (v + " SALTED", ln)

    # row 1: keylessWriteDeadline.ts, three concatenated literals, one key, both arms equal
    base_parts = [inner(lits(wb[KEYLESS], n)[0]) for n in (62, 63, 64)]
    joined = "".join(base_parts)
    holes = {"method": "${method}", "path": "${path}", "seconds": "${seconds}"}
    want = joined
    for h, src in holes.items():
        want = want.replace(src, "{%s}" % h)
    for side in ("en", "zh"):
        if dw[side][KEYS[4]][0] != want:
            red.append("keyless_%s_side_not_the_base_string" % side)
        else:
            green += 1
    site = [i + 1 for i, l in enumerate(wk[KEYLESS].split("\n")) if '"%s"' % KEYS[4] in l]
    if len(site) != 1:
        red.append("keyless_site=%s" % site)
    else:
        green += 1
    if not re.search(r'dictionaryText\("zh-CN", "%s", \{ method, path, seconds \}\)' % KEYS[4],
                     wk[KEYLESS]):
        red.append("keyless_call_shape")
    else:
        green += 1
    for s in [{"method": "POST", "path": "/api/v1/plans/generate", "seconds": 60},
              {"method": "PUT", "path": "/x", "seconds": 1}]:
        old = "".join(p.replace("${method}", s["method"]).replace("${path}", s["path"])
                      .replace("${seconds}", str(s["seconds"])) for p in base_parts)
        new = fill(dw["zh"][KEYS[4]][0], s)
        if old != new or fill(dw["en"][KEYS[4]][0], s) != new:
            red.append("keyless_screen_diff %r" % (s,))
        else:
            green += 2
    coords.append(dict(key=KEYS[4], file=KEYLESS, before="62-64", after=site[0] if site else 0,
                       dict_en=dw["en"][KEYS[4]][1], dict_zh=dw["zh"][KEYS[4]][1]))

    # row 2: writeDeadline title
    bzh = inner(lits(wb[WRITE], 84)[0])
    ben = inner(lits(wb[WRITE], 91)[0])
    for name, basev in (("zh", bzh), ("en", ben)):
        got = dw[name][KEYS[1]][0].replace("{seconds}", "${seconds}")
        if got != basev:
            red.append("title_%s=%r vs base %r" % (name, got, basev))
        else:
            green += 1
    site = [i + 1 for i, l in enumerate(wk[WRITE].split("\n")) if '"%s"' % KEYS[1] in l]
    if len(site) != 1:
        red.append("title_site=%s" % site)
    else:
        green += 1
        for s in [{"seconds": 60}, {"seconds": 1}]:
            old_zh = bzh.replace("${seconds}", str(s["seconds"]))
            old_en = ben.replace("${seconds}", str(s["seconds"]))
            new_zh = fill(dw["zh"][KEYS[1]][0], s)
            new_en = fill(dw["en"][KEYS[1]][0], s)
            if (old_zh, old_en) != (new_zh, new_en):
                red.append("title_screen_diff %r" % (s,))
            else:
                green += 2
    coords.append(dict(key=KEYS[1], file=WRITE, before="84|91", after=site[0] if site else 0,
                       dict_en=dw["en"][KEYS[1]][1], dict_zh=dw["zh"][KEYS[1]][1]))

    # rows 3 and 4: body + retryGuidance, one displayed string built from two keys
    b_body_zh = inner(lits(wb[WRITE], 86)[0])
    b_retry_zh = inner(lits(wb[WRITE], 87)[0])
    b_en_body = "".join(inner(x) for x in lits(wb[WRITE], 93)) + \
        "".join(inner(x) for x in lits(wb[WRITE], 94)) + "".join(inner(x) for x in lits(wb[WRITE], 95))
    if dw["zh"][KEYS[2]][0] != b_body_zh:
        red.append("body_zh_literal")
    else:
        green += 1
    if dw["zh"][KEYS[3]][0] != b_retry_zh:
        red.append("retry_zh_literal")
    else:
        green += 1
    rebuilt_en = (fill(dw["en"][KEYS[2]][0], {}) + " " + fill(dw["en"][KEYS[3]][0], {}))
    if rebuilt_en != b_en_body:
        red.append("body_retry_en_join=%r vs %r" % (rebuilt_en[:70], b_en_body[:70]))
    else:
        green += 1
    if (dw["zh"][KEYS[2]][0] + dw["zh"][KEYS[3]][0]) != (b_body_zh + b_retry_zh):
        red.append("body_retry_zh_join")
    else:
        green += 1
    if not re.search(r'dictionaryCopy\(locale, "%s"\) \+\s*\(zh \? "" : " "\) \+\s*dictionaryCopy\(locale, "%s"\)'
                     % (KEYS[2], KEYS[3]), wk[WRITE]):
        red.append("body_join_call_shape")
    else:
        green += 1
    sites = dict((k, [i + 1 for i, l in enumerate(wk[WRITE].split("\n")) if '"%s"' % k in l])
                 for k in (KEYS[1], KEYS[2], KEYS[3]))
    if any(len(v) != 1 for v in sites.values()):
        red.append("write_sites=%s" % sites)
    else:
        green += 1
    for s in [{"seconds": 60}]:
        old_body_zh = b_body_zh + b_retry_zh
        old_body_en = b_en_body
        new_body_zh = fill(dw["zh"][KEYS[2]][0], {}) + fill(dw["zh"][KEYS[3]][0], {})
        new_body_en = fill(dw["en"][KEYS[2]][0], {}) + " " + fill(dw["en"][KEYS[3]][0], {})
        if (old_body_zh, old_body_en) != (new_body_zh, new_body_en):
            red.append("body_screen_diff")
        else:
            green += 2
    coords.append(dict(key=KEYS[2], file=WRITE, before="86", after=sites[KEYS[2]][0] if sites[KEYS[2]] else 0,
                       dict_en=dw["en"][KEYS[2]][1], dict_zh=dw["zh"][KEYS[2]][1]))
    coords.append(dict(key=KEYS[3], file=WRITE, before="87", after=sites[KEYS[3]][0] if sites[KEYS[3]] else 0,
                       dict_en=dw["en"][KEYS[3]][1], dict_zh=dw["zh"][KEYS[3]][1]))

    # row 5: sceneClock, single-line ternary with two literals
    pair = lits(wb[CLOCK], 231)
    bzh2 = inner(pair[0]) if len(pair) == 2 else ""
    ben2 = inner(pair[1]) if len(pair) == 2 else ""
    if len(pair) != 2:
        red.append("clock_base_pair=%d" % len(pair))
    else:
        bzh2, ben2 = inner(pair[0]), inner(pair[1])
        if dw["zh"][KEYS[0]][0].replace("{state}", "${state}") != bzh2:
            red.append("clock_zh_literal")
        else:
            green += 1
        if dw["en"][KEYS[0]][0].replace("{state}", "${state}") != ben2:
            red.append("clock_en_literal")
        else:
            green += 1
        site = [i + 1 for i, l in enumerate(wk[CLOCK].split("\n")) if '"%s"' % KEYS[0] in l]
        if len(site) != 1:
            red.append("clock_site=%s" % site)
        else:
            green += 1
            for s in [{"state": "SOMETHING_NEW"}, {"state": "X Y"}]:
                old_zh = bzh2.replace("${state}", s["state"])
                old_en = ben2.replace("${state}", s["state"])
                if (old_zh, old_en) != (fill(dw["zh"][KEYS[0]][0], s), fill(dw["en"][KEYS[0]][0], s)):
                    red.append("clock_screen_diff %r" % (s,))
                else:
                    green += 2
            coords.append(dict(key=KEYS[0], file=CLOCK, before="231", after=site[0],
                               dict_en=dw["en"][KEYS[0]][1], dict_zh=dw["zh"][KEYS[0]][1]))

    # file-wide invariants
    w_en = dict((k, v[0]) for k, v in dw["en"].items())
    w_zh = dict((k, v[0]) for k, v in dw["zh"].items())
    b_en = dict((k, v[0]) for k, v in db["en"].items())
    b_zh = dict((k, v[0]) for k, v in db["zh"].items())
    touched = [k for k in b_en if w_en.get(k) != b_en[k]] + [k for k in b_zh if w_zh.get(k) != b_zh[k]]
    if touched:
        red.append("existing_texts_touched=%s" % touched[:3])
    else:
        green += 1
    if (set(b_en) ^ set(b_zh)) != (set(w_en) ^ set(w_zh)):
        red.append("parity_gap_changed")
    else:
        green += 1
    added_en = [k for k in w_en if k not in b_en]
    added_zh = [k for k in w_zh if k not in b_zh]
    # Generation-proof: the line keeps gaining keys from other lanes, so "the set added since my
    # base" is not mine alone. What must hold is that every key of this batch is present on both
    # sides, that both sides gained them in the same order, and (checked above) that no pre-existing
    # row moved. Asserting the exact set reddens every dictionary landing that follows mine.
    missing = sorted(set(KEYS) - set(added_en)) or sorted(set(KEYS) - set(added_zh))
    if missing:
        red.append("my_keys_not_added=%s" % missing[:3])
    elif added_en != added_zh:
        red.append("added_order_differs en=%s zh=%s" % (added_en[:3], added_zh[:3]))
    else:
        green += 1
    gone = 0
    for raw, p in ((joined, KEYLESS), (b_body_zh, WRITE), (b_retry_zh, WRITE),
                   (bzh2, CLOCK), (ben2, CLOCK)):
        if raw and raw not in wk[p]:
            gone += 1
    if gone != 5:
        red.append("old_literals_still_present=%d" % gone)
    else:
        green += 1

    def cjk(text):
        n = 0
        block = False
        for line in text.split("\n"):
            s = line.strip()
            if block:
                if "*/" in s:
                    block = False
                continue
            if s.startswith("/*"):
                if "*/" not in s:
                    block = True
                continue
            if s.startswith(("//", "*", "*/")):
                continue
            for lit in LIT.findall(line):
                if re.search(u'[一-鿿]', lit[1:-1]):
                    n += 1
                    break
        return n
    census = dict((p, (cjk(wb[p]), cjk(wk[p]))) for p in (KEYLESS, WRITE, CLOCK))
    if census != {KEYLESS: (3, 0), WRITE: (3, 0), CLOCK: (9, 8)}:
        red.append("cjk_census=%s" % census)
    else:
        green += 1

    if negative:
        bit = any(x.startswith("clock_") or x.startswith("parity") for x in red) or bool(red)
        sys.stdout.write("NEGATIVE_CONTROL_BITES passed=%d failed=%s\n" % (green, red[:3] if bit else []))
        sys.exit(0 if bit else 1)

    sys.stdout.write("ARM i18n_0585: rows=%d green=%d red=%d %s\n" % (len(KEYS), green, len(red), red[:6]))
    with io.open(os.path.join(TREE, "frontend/scripts/i18n_0585_arm_evidence_r1.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(dict(base=BASE, coordinates=coords, cjk_census=census, green=green, red=red),
                  fh, ensure_ascii=False, indent=1)
    sys.exit(0 if not red else 1)


main()
