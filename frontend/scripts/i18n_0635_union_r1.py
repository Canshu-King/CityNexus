"""ORD-0635 · 把 12 枚让路枝的字典键并成一枚落线：唯一的尺，两种档。

  python scripts/i18n_0635_union_r1.py            只验不写（交块前跑这一档，末行 ARM ...）
  python scripts/i18n_0635_union_r1.py --apply    按同一套判据写盘（判据不绿就不落一笔）
  python scripts/i18n_0635_union_r1.py --negative 只在内存里给一枚已并入的键值加盐，看这尺咬不咬

为什么要自己现读 12 枚枝而不是抄号令者那两份表：表是 05:11 切的，尖已经走了好几代，
加闸工-0585-r1 那三枚 simulation.* 已经自己上线了——并集因此从 16 缩到 13，这一格只能现算。

键尺的形制（踩过的坑都写在这里）：
  frontend/src/i18n/LocaleContext.tsx 是两半有序字典 `const en: Dict = {`（第 8 行）与
  `const zhCN: Dict = {`（现读），每行形如 `  "a.b.c": "文案",`；
  但 prettier 会把长值折行成
      "me.asksBeforeProtectedChange":
        "Anything affecting ...",
  一行两段的形状。早先我只认一行式，于是把这条读成「en 半边没有这枚键」，报了个假的不配对。
  这一版两种形状都认，并且把「折行只算一处出现」钉成判据（见 wrapped_pair）。
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.dirname(SCRIPT_DIR)
REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=FRONT,
                      capture_output=True, text=True).stdout.strip()
MOODLE = os.path.dirname(REPO)
LIB = os.path.join(MOODLE, "CityNexus")
MANIFEST = os.path.join(MOODLE, "_qoder_cn_work_0609", "rebase", "_manifest.tsv")
UNION_TABLE = os.path.join(MOODLE, "_qoder_cn_work_0609", "rebase", "_union_keys.tsv")
LC_REL = "frontend/src/i18n/LocaleContext.tsx"
LC = os.path.join(FRONT, "src", "i18n", "LocaleContext.tsx")
LINE_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
EVIDENCE = os.path.join(FRONT, "scripts", "i18n_0635_union_evidence_r1.json")

HALF_ROW = re.compile(r"^const (en|zhCN): Dict")
STRICT = re.compile(r'^  "([A-Za-z][A-Za-z0-9_.]*)": ("(?:[^"\\]|\\.)*"),?\s*$')
WRAPPED_KEY = re.compile(r'^  "([A-Za-z][A-Za-z0-9_.]*)":\s*$')
WRAPPED_VAL = re.compile(r'^\s+("(?:[^"\\]|\\.)*"),?\s*$')
FAMILY = re.compile(r'^([a-zA-Z][A-Za-z0-9_]*\.)')


def git(*args, cwd=None):
    done = subprocess.run(["git", "-C", cwd or LIB] + list(args), capture_output=True)
    return done.returncode, done.stdout.decode("utf-8", "replace"), done.stderr.decode("utf-8", "replace")


def parse(text):
    """Both halves -> {'en': [(line, key, value_literal, raw)], 'zhCN': [...]}, marks, wrapped lines."""
    marks = {}
    for number, row in enumerate(text.split("\n"), 1):
        hit = HALF_ROW.match(row)
        if hit:
            marks[hit.group(1)] = number
    if len(marks) != 2:
        raise SystemExit("dictionary halves not found: {}".format(marks))
    rows = {"en": [], "zhCN": []}
    wrapped = []
    lines = text.split("\n")
    for number, row in enumerate(lines, 1):
        side = "en" if marks["en"] < number < marks["zhCN"] else ("zhCN" if number > marks["zhCN"] else None)
        if side is None:
            continue
        hit = STRICT.match(row)
        if hit:
            rows[side].append((number, hit.group(1), hit.group(2), row))
            continue
        hit = WRAPPED_KEY.match(row)
        if hit and number < len(lines):
            value = WRAPPED_VAL.match(lines[number])
            if value:
                raw = row + "\n" + lines[number]
                rows[side].append((number, hit.group(1), value.group(1), raw))
                wrapped.append((number, side, hit.group(1)))
    return marks, rows, wrapped


def yield_branches():
    names = []
    for row in open(MANIFEST, encoding="utf-8").read().split("\n"):
        if not row.strip():
            continue
        cols = row.split("\t")
        if len(cols) < 2 or cols[0] in ("branch", "TIP") or cols[1] != "LocaleContext.tsx":
            continue
        if cols[0] not in names:
            names.append(cols[0])
    return names


def table_keys():
    keys = {}
    for row in open(UNION_TABLE, encoding="utf-8").read().split("\n")[1:]:
        if not row.strip():
            continue
        cols = row.split("\t")
        keys[cols[0]] = cols[1].split("|")
    return keys


def branch_rows(head):
    rc, text, err = git("show", "{}:{}".format(head, LC_REL))
    if rc != 0:
        raise SystemExit("cannot read dictionary on {}: {}".format(head[:12], err[:120]))
    return parse(text)


def plan_for(tip, rows_en, rows_zh):
    """Recompute every yielding branch's new keys at its own head and build the merge plan."""
    tip_en = {k for _, k, _, _ in rows_en}
    tip_zh = {k for _, k, _, _ in rows_zh}
    remote = {}
    for line in git("ls-remote", "origin")[1].splitlines():
        if "\t" in line:
            sha, ref = line.split("\t", 1)
            remote[ref] = sha
    plan = {}
    heads = {}
    missing = []
    for index, name in enumerate(yield_branches()):
        ref = "refs/heads/review/" + name
        if ref not in remote:
            missing.append(ref)
            continue
        tmp = "refs/tmp/0635-plan-{}".format(index)
        rc, _, err = git("fetch", "-q", "origin", "+{}:{}".format(ref, tmp))
        if rc != 0:
            raise SystemExit("fetch failed {} :: {}".format(ref, err[:120]))
        head = git("rev-parse", tmp)[1].strip()
        heads[name] = head
        _, brows, _ = branch_rows(head)
        new_en = {k: (n, v, raw) for n, k, v, raw in brows["en"] if k not in tip_en}
        new_zh = {k: (n, v, raw) for n, k, v, raw in brows["zhCN"] if k not in tip_zh}
        for key in sorted(set(new_en) | set(new_zh)):
            entry = plan.setdefault(key, {"en": {}, "zh": {}})
            if key in new_en:
                entry["en"][name] = new_en[key]
            if key in new_zh:
                entry["zh"][name] = new_zh[key]
    return plan, heads, missing


def side_row(entry, side):
    """The verbatim row for one side, refusing to pick when contributing branches disagree."""
    seen = entry[side]
    if not seen:
        return None
    distinct = {value[2] for value in seen.values()}
    if len(distinct) != 1:
        raise SystemExit("DISAGREE {} {} :: contributing rows are not byte-identical".format(
            side, sorted(seen)))
    name = sorted(seen)[0]
    return {"row": seen[name][2], "source": name, "source_line": seen[name][0],
            "sources": sorted(seen), "value": seen[name][1]}


def insert_rows(text, merged):
    """Place each row after the last key of its own family inside its half (tail when no family)."""
    lines = text.split("\n")
    marks, rows, _ = parse("\n".join(lines))
    for side, key, row_text in merged:
        prefix = FAMILY.match(key)
        prefix = prefix.group(1) if prefix else key
        same = [n for n, k, _, _ in (rows["en"] if side == "en" else rows["zhCN"]) if k.startswith(prefix)]
        anchor = max(same) if same else max(n for n, _, _, _ in (rows["en"] if side == "en" else rows["zhCN"]))
        after = anchor
        if side == "en":
            while after < marks["zhCN"] and not STRICT.match(lines[after - 1]) and not WRAPPED_KEY.match(lines[after - 1]):
                after += 1
        insert_at = after
        if side == "zhCN":
            while insert_at - 1 < len(lines) and WRAPPED_VAL.match(lines[insert_at - 1]):
                insert_at += 1
        lines.insert(insert_at - 1, row_text)
        marks, rows, _ = parse("\n".join(lines))
    return "\n".join(lines)


def main():
    apply_mode = "--apply" in sys.argv
    negative = "--negative" in sys.argv
    tip = git("ls-remote", "origin", LINE_REF)[1].split()[0]
    head = git("rev-parse", "HEAD", cwd=REPO)[1].strip()
    green, red = 0, []
    # The branch must already carry the freshly read tip; otherwise the plan below describes a
    # generation the line no longer is.
    if git("merge-base", "--is-ancestor", tip, head, cwd=REPO)[0] != 0:
        red.append("HEAD {} does not contain the freshly read tip {}".format(head[:12], tip[:12]))

    # The generation to diff against comes from git, never from the file on disk: after this merge
    # lands, reading the working file as the base would report "nothing new" and certify an empty
    # plan -- which is exactly what the first re-run did.
    base = None
    for position, argument in enumerate(sys.argv):
        if argument == "--base" and position + 1 < len(sys.argv):
            base = sys.argv[position + 1]
    if not base:
        base = git("merge-base", head, tip, cwd=REPO)[1].strip()
    if git("cat-file", "-t", base)[1].strip() != "commit":
        raise SystemExit("base {} is not a commit".format(base))

    original = open(LC, encoding="utf-8", newline="").read()
    newline = "\r\n" if "\r\n" in original else "\n"
    work = original.replace("\r\n", "\n")
    base_text = git("show", "{}:{}".format(base, LC_REL))[1].replace("\r\n", "\n")
    marks, rows, wrapped = parse(base_text)
    plan, heads, missing = plan_for(tip, rows["en"], rows["zhCN"])
    table = table_keys()

    merged = {}
    for key, entry in sorted(plan.items()):
        en = side_row(entry, "en")
        zh = side_row(entry, "zh")
        merged[key] = {"en": en, "zh": zh}
    both = [k for k, v in merged.items() if v["en"] and v["zh"]]
    zh_only = sorted(k for k, v in merged.items() if v["zh"] and not v["en"])
    en_only = sorted(k for k, v in merged.items() if v["en"] and not v["zh"])
    # A key written on only one side cannot be merged faithfully: the other half would have to be
    # invented, and the shipped parity gate (scripts/i18n_detail_parity_r1.py) counts it as a break.
    # Such keys are withheld and handed back with their source coordinates instead.
    withheld = {}
    for key in sorted(zh_only + en_only):
        side = "zh" if merged[key]["zh"] else "en"
        entry = merged[key][side]
        withheld[key] = {"side": "zhCN" if side == "zh" else "en", "source_branch": entry["source"],
                         "source_head": heads[entry["source"]], "source_line": entry["source_line"],
                         "row": entry["row"], "sources": entry["sources"]}
        del merged[key]
    multi = {}
    for key, pair in sorted(merged.items()):
        sources = sorted({s for side in ("en", "zh") if pair[side] for s in pair[side]["sources"]})
        if len(sources) > 1:
            multi[key] = sources

    landed = sorted(set(table) - set(merged) - set(withheld))


    def family_of(key):
        hit = FAMILY.match(key)
        return hit.group(1) if hit else key

    ordered = []
    for side, slot in (("en", "en"), ("zhCN", "zh")):
        for key in sorted(merged, key=lambda k: (family_of(k), k)):
            if merged[key][slot]:
                ordered.append((side, key, merged[key][slot]["row"]))

    candidate = insert_rows(base_text, ordered)
    cmarks, crows, cwrapped = parse(candidate)
    check = {"tip": tip, "head": head, "newline": "CRLF" if newline == "\r\n" else "LF",
             "tip_key_counts": {"en": len({k for _, k, _, _ in rows["en"]}),
                                "zhCN": len({k for _, k, _, _ in rows["zhCN"]})},
             "merged_key_counts": {"en": len({k for _, k, _, _ in crows["en"]}),
                                   "zhCN": len({k for _, k, _, _ in crows["zhCN"]})},
             "union": sorted(merged), "union_size": len(merged), "table_size": len(table),
             "already_on_line": landed, "multi": {k: v for k, v in sorted(multi.items())},
             "zh_only": zh_only, "en_only": en_only, "withheld": withheld, "both_sides": len(both),
             "insertions": {}, "wrapped_rows": {"before": [w[2] for w in wrapped],
                                                "after": [w[2] for w in cwrapped]}}

    for key in sorted(merged):
        for side, slot in (("en", "en"), ("zhCN", "zh")):
            want = merged[key][slot]
            if not want:
                continue
            found = [r for n, k, v, r in (crows[side]) if k == key]
            if len(found) != 1:
                red.append("{} {} appears {} times after merge".format(side, key, len(found)))
            elif found[0] != want["row"]:
                red.append("{} {} not byte-equal to its source".format(side, key))
            else:
                green += 1
            check["insertions"].setdefault(key, {})[side] = {
                "source_branch": want["source"], "source_head": heads[want["source"]][:12],
                "source_line": want["source_line"], "sources": want["sources"],
                "new_line": next((n for n, k, _, _ in crows[side] if k == key), None)}

    untouched = []
    old_en = {k: r for _, k, _, r in rows["en"]}
    new_en = {k: r for _, k, _, r in crows["en"]}
    for key, raw in old_en.items():
        if new_en.get(key) != raw:
            untouched.append("en " + key)
    old_zh = {k: r for _, k, _, r in rows["zhCN"]}
    new_zh = {k: r for _, k, _, r in crows["zhCN"]}
    for key, raw in old_zh.items():
        if new_zh.get(key) != raw:
            untouched.append("zh " + key)
    if untouched:
        red.append("pre-existing rows changed: {}".format(untouched[:4]))
    else:
        green += 1
    if len(crows["en"]) - len(rows["en"]) != sum(1 for k in merged if merged[k]["en"]):
        red.append("en half grew by the wrong number")
    else:
        green += 1
    if len(crows["zhCN"]) - len(rows["zhCN"]) != sum(1 for k in merged if merged[k]["zh"]):
        red.append("zhCN half grew by the wrong number")
    else:
        green += 1
    if [w[2] for w in wrapped] and set([w[2] for w in wrapped]) - set([w[2] for w in cwrapped]):
        red.append("a wrapped row stopped being read")
    else:
        green += 1
    for key, info in withheld.items():
        rc, hits, _ = git("grep", "-c", "-F", '"%s"' % key, tip, "--", "frontend/src")
        info["readers_on_tip"] = len([l for l in hits.splitlines() if l.strip()])
    if withheld:
        green += 1
    if set(merged) - set(table):
        red.append("union has keys the commander's table does not: {}".format(sorted(set(merged) - set(table))))
    else:
        green += 1
    if sorted(set(table) - set(merged) - set(withheld)) != sorted(landed) or sorted(
            set(table) - set(merged) - set(landed)) != sorted(withheld):
        red.append("already-landed bookkeeping inconsistent")
    else:
        green += 1
    readers = {}
    for key in sorted(merged):
        _, hits, _ = git("grep", "-l", "-F", '"%s"' % key, tip, "--", "frontend/src")
        files = [l.split(":", 2)[2] for l in hits.splitlines() if l.count(":") >= 2]
        readers[key] = {"files": sorted(set(files)),
                        "outside_dictionary": sorted(set(files) - {LC_REL})}
    check["readers_on_tip"] = readers
    # A key with no reader on the line is not a mover error - it is the consequence of landing the
    # union before the code that asks for it.  Counted, printed, and handed to the commander rather
    # than silently accepted or silently refused.
    check["merged_keys_without_a_reader"] = sorted(
        k for k in readers if not readers[k]["outside_dictionary"])
    print("ADVISORY keys_without_reader={} of {}".format(
        len(check["merged_keys_without_a_reader"]), len(merged)))
    if not apply_mode and candidate != work:
        red.append("the file on disk is not what this plan produces on base {}".format(base[:12]))
    else:
        green += 1
    check["base"] = base
    check["pre_existing_rows"] = {"en": len(old_en), "zhCN": len(old_zh)}
    check["bytes"] = {"before": len(original.encode("utf-8")), "after": len(candidate.encode("utf-8"))}
    def blob(data):
        return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()

    check["blob_before"] = blob(original.encode("utf-8"))
    check["blob_after"] = blob(candidate.encode("utf-8"))

    if negative:
        salted = candidate.replace('"inbox.recorded": "Recorded"', '"inbox.recorded": "Recorded SALT"', 1)
        smarks, srows, _ = parse(salted)
        bites = [r for n, k, v, r in srows["en"] if k == "inbox.recorded"][0] != merged["inbox.recorded"]["en"]["row"]
        print("NEGATIVE_CONTROL ARM i18n_0635: bites={} union={} green={} red={}".format(
            bites, len(merged), green, len(red)))
        return 0 if bites and not red else 1

    print(json.dumps(check, ensure_ascii=False, indent=2))
    if apply_mode:
        if red:
            print("REFUSE: {} red checks, nothing written".format(len(red)))
            return 1
        with open(LC, "w", encoding="utf-8", newline=newline) as handle:
            handle.write(candidate.replace("\n", newline))
        if open(LC, encoding="utf-8", newline="").read().replace("\r\n", "\n") != candidate:
            raise SystemExit("the write did not land what the plan produced")
        print("APPLIED rows={} bytes {} -> {}".format(len(ordered), check["bytes"]["before"], check["bytes"]["after"]))
    with open(EVIDENCE, "w", encoding="utf-8") as handle:
        json.dump(check, handle, ensure_ascii=False, indent=2)
    print("ARM i18n_0635: union={} already_on_line={} green={} red={} {}".format(
        len(merged), len(landed), green, len(red), red[:4]))
    return 0 if not red else 1


if __name__ == "__main__":
    sys.exit(main())
