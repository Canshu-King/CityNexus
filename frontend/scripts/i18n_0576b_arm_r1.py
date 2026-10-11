# ORD-0576 batch two, arm r1. Reads three generations: the base tip blobs (git show), the
# working-tree product files and the working-tree dictionary. Per row it proves, in order:
#   1 the base arm literal is on the declared line, byte for byte;
#   2 the dictionary value on each side reconstructs that literal exactly, given the hole
#     map -- a {plural:stem:countKey} marker reconstructs to the very
#     `${expr} ${englishCountNoun(expr, "stem")}` shape the base carried;
#   3 the call site reads the key once and passes a param for every hole, with the same
#     expression source the base used;
#   4 for sampled values the base expression and the dictionary read render identical bytes
#     in both locales -- where a singular/plural mistake would show up;
#   5 the old literal is gone, both dictionary arms still carry the same key set, and no
#     base entry text moved.
# `--negative` salts one English value in memory only (nothing on disk changes) and requires
# this same ruler to go red on that row.
import io
import json
import os
import re
import subprocess
import sys

TREE = r"D:/moodle/_qoder_jianpanggong_0555"
BASE = "d2f06bee22f0e051208a9e208b3c7f55622d7487"
FILES = {
    "journey": "frontend/src/features/progress/journeyProgress.ts",
    "detail": "frontend/src/features/trip/ActivityDetail.tsx",
    "stay": "frontend/src/features/stay/stayGenerationDoor.ts",
}
DICTF = "frontend/src/i18n/LocaleContext.tsx"
BATCH_ONE = ["main.demoAgentCommand", "main.modeAutonomous", "main.modeAssisted", "main.modeAdvisory"]
IRREGULAR = {"person": "people"}


def die(msg):
    sys.stdout.write("ARM ABORT (nothing written) :: " + msg + "\n")
    sys.exit(2)


def js_round(v):
    import math
    return int(math.floor(v + 0.5))


def regular_plural(word):
    w = word.strip()
    if not w:
        return w
    if w in IRREGULAR:
        return IRREGULAR[w]
    if re.search(r'[^aeiouy]y$', w, re.I):
        return w[:-1] + "ies"
    if re.search(r'(s|x|z|ch|sh)$', w, re.I):
        return w + "es"
    return w + "s"


def count_noun(count, stem):
    text = ("" if count is None else str(count)).strip()
    return stem.strip() if (count == 1 or text == "1") else regular_plural(stem)


EXPR = {
    "p.day_total": 's["day_total"]',
    "p.day_of": 's["day_of"]',
    "p.planned_total": 's["planned_total"]',
    "p.completed_count": 's["completed_count"]',
    "skipped": 's["skipped"]',
    "duration": 's["duration"]',
    "Math.floor(duration / 60)": 's["duration"] // 60',
    "duration % 60": 's["duration"] % 60',
    "activity.travel_from_prev_min": 's["travel_min"]',
    "nearbyRadiusM": 's["radius"]',
    "Math.round(metres)": 'js_round(s["metres"])',
    "(metres / 1000).toFixed(1)": '"%.1f" % (s["metres"] / 1000.0)',
}
CN = re.compile(r'^englishCountNoun\((.+),\s*"([A-Za-z]+)"\)$')


def ev(expr_src, s):
    expr_src = expr_src.strip()
    m = CN.match(expr_src)
    if m:
        return count_noun(ev(m.group(1), s), m.group(2))
    if expr_src not in EXPR:
        die("no evaluator for expression %r" % expr_src)
    return eval(EXPR[expr_src], {"js_round": js_round}, {"s": s})


def ts_num(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def base_text(path):
    return subprocess.check_output(["git", "-C", TREE, "show", "%s:%s" % (BASE, path)]).decode("utf-8")


def work_text(path):
    with io.open(os.path.join(TREE, path.replace("/", os.sep)), encoding="utf-8", newline="") as fh:
        return fh.read()


ENTRY_RE = re.compile(r'^  "([A-Za-z0-9._]+)": "(.*)",$')
LIT = re.compile(r'"(?:[^"\\]|\\.)*"|`[^`]*`')


def dict_arms(text):
    lines = text.split("\n")
    arms = {}
    for name, marker in (("en", "const en: Dict = {"), ("zh", "const zhCN: Dict = {")):
        start = lines.index(marker)
        end = start
        while lines[end] != "};":
            end += 1
        d = {}
        for i in range(start + 1, end):
            m = ENTRY_RE.match(lines[i])
            if m:
                d[m.group(1)] = (m.group(2), i + 1)
        arms[name] = d
    return arms


def literals_at(text, line, want):
    hits = LIT.findall(text.split("\n")[line - 1])
    if want >= len(hits):
        die("line %d holds %d literals, wanted number %d" % (line, len(hits), want))
    raw = hits[want][1:-1]
    return raw


def reconstruct(value, holes, plural):
    """Dictionary value -> the source text it was ported from. The house shape keeps the
       number in its own `{hole}` and lets `{plural:stem:countKey}` stand for the noun
       only, which is what `${expr} ${englishCountNoun(expr, "stem")}` looks like."""
    out = value
    for name, (stem, ck) in plural.items():
        e = holes[ck]
        out = out.replace("{plural:%s:%s}" % (stem, ck), '${englishCountNoun(%s, "%s")}' % (e, stem))
    for name, e in holes.items():
        out = out.replace("{%s}" % name, "${%s}" % e)
    return out


def render(value, plural, params):
    out = value
    for name, (stem, ck) in plural.items():
        out = out.replace("{plural:%s:%s}" % (stem, ck), count_noun(params[ck], stem))
    for name, v in params.items():
        out = out.replace("{%s}" % name, ts_num(v))
    return out.replace('\\"', '"')


def subst_eval(raw, s):
    out = re.sub(r'\$\{([^{}]*)\}', lambda m: ts_num(ev(m.group(1), s)), raw)
    return out


ROWS = [
    dict(f="journey", key="progress.none.scheduled", zh_line=77, en_line=78, mode="plain"),
    dict(f="journey", key="progress.day.total.blank", zh_line=84, en_line=85, mode="plain"),
    dict(f="journey", key="progress.day.total.only", zh_line=87, en_line=87, mode="tpl",
         holes={"count": "p.day_total"}, plural={"count": ("day", "count")},
         samples=[{"day_total": 1}, {"day_total": 3}, {"day_total": 12}]),
    dict(f="journey", key="progress.day.of.total", zh_line=90, en_line=91, mode="tpl",
         holes={"day": "p.day_of", "total": "p.day_total"}, plural={},
         samples=[{"day_of": 1, "day_total": 3}, {"day_of": 2, "day_total": 12}]),
    dict(f="journey", key="progress.stop.none.walked", zh_line=95, en_line=96, mode="tpl",
         holes={"count": "p.planned_total"}, plural={"count": ("stop", "count")},
         samples=[{"planned_total": 1}, {"planned_total": 5}]),
    dict(f="journey", key="progress.stop.completed", zh_line=99, en_line=101, mode="tpl",
         holes={"completed": "p.completed_count", "total": "p.planned_total"},
         plural={"total": ("stop", "total")},
         samples=[{"completed_count": 1, "planned_total": 1}, {"completed_count": 3, "planned_total": 8}]),
    dict(f="journey", key="progress.stop.skipped.clause", zh_line=100, en_line=102, mode="tpl",
         holes={"count": "skipped"}, plural={}, samples=[{"skipped": 1}, {"skipped": 4}]),
    dict(f="journey", key="progress.day.gap.no.cursor", zh_line=112, en_line=113, mode="plain"),
    dict(f="journey", key="progress.day.gap.stale.cursor", zh_line=115, en_line=116, mode="plain"),
    dict(f="detail", key="detail.duration.hours.minutes", zh_line=147, en_line=148, mode="both",
         holes={"hours": "Math.floor(duration / 60)", "minutes": "duration % 60"}, plural={},
         zh_rebuilt="${Math.floor(duration / 60)} 小时 ${duration % 60} 分",
         en_rebuilt="${Math.floor(duration / 60)}h ${duration % 60}m",
         old=lambda s: ("%s 小时 %s 分" % (s["duration"] // 60, s["duration"] % 60),
                        "%sh %sm" % (s["duration"] // 60, s["duration"] % 60)),
         samples=[{"duration": 61}, {"duration": 80}, {"duration": 125}]),
    dict(f="detail", key="detail.duration.hours.only", zh_line=147, en_line=148, mode="both",
         holes={"hours": "Math.floor(duration / 60)"}, plural={},
         zh_rebuilt="${Math.floor(duration / 60)} 小时", en_rebuilt="${Math.floor(duration / 60)}h",
         old=lambda s: ("%s 小时" % (s["duration"] // 60), "%sh" % (s["duration"] // 60)),
         samples=[{"duration": 60}, {"duration": 120}, {"duration": 180}]),
    dict(f="detail", key="detail.duration.minutes", zh_line=150, en_line=151, mode="tpl",
         holes={"minutes": "duration"}, plural={"minutes": ("minute", "minutes")},
         samples=[{"duration": 1}, {"duration": 45}]),
    dict(f="detail", key="detail.travel.prev.minutes", zh_line=186, en_line=187, mode="tpl",
         holes={"minutes": "activity.travel_from_prev_min"}, plural={"minutes": ("minute", "minutes")},
         samples=[{"travel_min": 1}, {"travel_min": 20}]),
    dict(f="detail", key="detail.cost.unknown", zh_line=201, en_line=202, mode="plain"),
    dict(f="detail", key="detail.hoursNoData", zh_line=219, en_line=220, mode="plain", reuse=True),
    dict(f="detail", key="detail.nearby.radius.note", zh_line=292, en_line=293, mode="tpl",
         holes={"metres": "nearbyRadiusM"}, plural={"metres": ("metre", "metres")},
         samples=[{"radius": 1}, {"radius": 350}]),
    dict(f="detail", key="detail.distance.metres", zh_line=307, en_line=308, mode="tpl",
         holes={"metres": "Math.round(metres)"}, plural={"metres": ("metre", "metres")},
         samples=[{"metres": 1.4}, {"metres": 240.6}, {"metres": 0.6}]),
    dict(f="detail", key="detail.distance.kilometres", zh_line=310, en_line=311, mode="tpl",
         holes={"km": "(metres / 1000).toFixed(1)"}, plural={"km": ("kilometre", "km")},
         samples=[{"metres": 1000.0}, {"metres": 1400.0}, {"metres": 2500.0}]),
    dict(f="stay", key="stay.outcome.unnamed", zh_line=48, en_line=49, mode="plain"),
]


def main():
    negative = "--negative" in sys.argv
    salt_key = "detail.distance.metres"
    green = 0
    red = []
    coords = []
    dict_work = dict_arms(work_text(DICTF))
    dict_base = dict_arms(base_text(DICTF))
    base_cache = dict((k, base_text(v)) for k, v in FILES.items())
    work_cache = dict((k, work_text(v)) for k, v in FILES.items())
    if negative:
        v, ln = dict_work["en"][salt_key]
        dict_work["en"][salt_key] = (v + " SALTED", ln)

    for row in ROWS:
        f, key, mode = row["f"], row["key"], row["mode"]
        if key not in dict_work["en"] or key not in dict_work["zh"]:
            red.append("missing_from_dictionary_" + key)
            continue
        en_val, en_ln = dict_work["en"][key]
        zh_val, zh_ln = dict_work["zh"][key]
        holes = row.get("holes", {})
        plural = row.get("plural", {})
        same_line = row["zh_line"] == row["en_line"]
        base_zh = literals_at(base_cache[f], row["zh_line"], 0)
        base_en = literals_at(base_cache[f], row["en_line"], 1 if same_line else 0)

        if mode == "plain":
            ok = (zh_val == base_zh, en_val == base_en)
        elif mode == "tpl":
            ok = (reconstruct(zh_val, holes, plural) == base_zh,
                  reconstruct(en_val, holes, plural) == base_en)
        else:
            ok = (reconstruct(zh_val, holes, {}) == row["zh_rebuilt"],
                  reconstruct(en_val, holes, {}) == row["en_rebuilt"])
        if not all(ok):
            red.append("reconstruct_%s zh=%s en=%s :: want=%r got=%r"
                       % (key, ok[0], ok[1], base_en[:70], reconstruct(en_val, holes, plural)[:70]))
            continue
        green += 2

        reads = [i + 1 for i, l in enumerate(work_cache[f].split("\n")) if ('"%s"' % key) in l]
        if len(reads) != 1:
            red.append("site_reads_%s=%s" % (key, reads))
            continue
        green += 1
        site = work_cache[f].split("\n")[reads[0] - 1]

        if mode != "plain":
            m = re.search(r'\{\s*([^{}]*?)\s*\}\s*\)', site)
            if not m:
                red.append("no_param_map_" + key)
                continue
            got = dict(pair.split(":", 1) for pair in m.group(1).split(","))
            got = dict((k.strip(), v.strip()) for k, v in got.items())
            want = dict(holes)
            for name, (stem, ck) in plural.items():
                want[ck] = holes[ck]
            if got != want:
                red.append("params_%s=%s want=%s" % (key, sorted(got.items()), sorted(want.items())))
                continue
            green += 1
            for s in row["samples"]:
                params = dict((n, ev(e, s)) for n, e in holes.items())
                if "old" in row:
                    old_zh, old_en = row["old"](s)
                else:
                    old_zh, old_en = subst_eval(base_zh, s), subst_eval(base_en, s)
                new_zh, new_en = render(zh_val, plural, params), render(en_val, plural, params)
                if (old_zh, old_en) != (new_zh, new_en):
                    red.append("screen_diff_%s %r/%r vs %r/%r" % (key, old_zh, old_en, new_zh, new_en))
                else:
                    green += 2
            if red and any(x.startswith("screen_diff_" + key) for x in red):
                continue
        else:
            green += 1

        for raw in (base_zh, base_en):
            if raw in work_cache[f]:
                red.append("literal_still_in_%s :: %s" % (f, raw[:36]))
        green += 1
        coords.append(dict(key=key, file=FILES[f], before_zh_line=row["zh_line"],
                           before_en_line=row["en_line"], after_line=reads[0],
                           dict_en_line=en_ln, dict_zh_line=zh_ln, mode=mode,
                           reuse=bool(row.get("reuse"))))

    w_en = dict((k, v[0]) for k, v in dict_work["en"].items())
    w_zh = dict((k, v[0]) for k, v in dict_work["zh"].items())
    b_en = dict((k, v[0]) for k, v in dict_base["en"].items())
    b_zh = dict((k, v[0]) for k, v in dict_base["zh"].items())
    touched = [k for k in b_en if w_en.get(k) != b_en[k]] + [k for k in b_zh if w_zh.get(k) != b_zh[k]]
    if touched:
        red.append("existing_texts_touched=%s" % touched[:4])
    else:
        green += 1
    if (set(b_en) ^ set(b_zh)) != (set(w_en) ^ set(w_zh)):
        red.append("parity_gap_changed")
    else:
        green += 1
    # r2 carries batch one's commit, so relative to the base tip the dictionary gains this
    # batch's 18 keys plus the four main.* keys shipped in batch one
    mine = sorted([r["key"] for r in ROWS if not r.get("reuse")] + BATCH_ONE)
    added_en = [k for k in w_en if k not in b_en]
    added_zh = [k for k in w_zh if k not in b_zh]
    if sorted(added_en) != mine or sorted(added_zh) != mine:
        red.append("added_en=%s added_zh=%s" % (added_en[:3], added_zh[:3]))
    else:
        green += 1
    if added_en != added_zh:
        red.append("added_order_differs")
    else:
        green += 1

    def cjk(text):
        n = 0
        for line in text.split("\n"):
            st = line.strip()
            if st.startswith("//") or st.startswith("*") or st.startswith("/*") or st.startswith("{/*"):
                continue
            for lit in LIT.findall(line):
                body = lit[1:-1]
                if u"。" == body or u"，" == body:
                    continue
                if re.search(u'[\u4e00-\u9fff]', body):
                    n += 1
                    break
        return n
    def marks(text):
        hits = []
        for i, line in enumerate(text.split("\n"), 1):
            st = line.strip()
            if st.startswith("//") or st.startswith("*") or st.startswith("/*") or st.startswith("{/*"):
                continue
            for lit in LIT.findall(line):
                if lit[1:-1] in (u"。", u"，"):
                    hits.append(i)
                    break
        return hits
    census = dict((f, (cjk(base_cache[f]), cjk(work_cache[f]))) for f in FILES)
    expect = {"journey": (9, 0), "detail": (8, 0), "stay": (6, 5)}
    if census != expect:
        red.append("cjk_census=%s" % census)
    else:
        green += 1
    # the sentence mark journeyProgress.ts still keeps inline is counted here, not hidden:
    # copy literals went to zero while that one mark stays, declared non-display by the CN
    # side's own COVERAGE line for this file
    mark_census = dict((f, (marks(base_cache[f]), marks(work_cache[f]))) for f in FILES)
    if mark_census != {"journey": ([100], [91]), "detail": ([], []), "stay": ([], [])}:
        red.append("punctuation_mark_census=%s" % mark_census)
    else:
        green += 1

    if negative:
        bit = any(x.startswith("reconstruct_" + salt_key) for x in red)
        sys.stdout.write("NEGATIVE_CONTROL_BITES passed=%d failed=%s\n" % (green, [salt_key] if bit else []))
        sys.exit(0 if bit else 1)

    sys.stdout.write("ARM i18n_0576b: rows=%d green=%d red=%d %s\n" % (len(ROWS), green, len(red), red[:6]))
    out = os.path.join(TREE, "frontend/scripts/i18n_0576b_arm_evidence_r1.json")
    with io.open(out, "w", encoding="utf-8") as fh:
        json.dump(dict(base=BASE, coordinates=coords, cjk_census=census, mark_census=mark_census,
                       green=green, red=red),
                  fh, ensure_ascii=False, indent=1)
    sys.exit(0 if not red else 1)


main()
