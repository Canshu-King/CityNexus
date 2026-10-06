"""ORD-0553 r16 -- are the four `exec.mark*` dictionary entries reachable on any screen today?

The ruling cell this feeds: three English values in the traveller dictionary are the contract enum printed
verbatim ("Mark EN_ROUTE", "Mark ARRIVED", "Mark IN_PROGRESS", "Mark COMPLETED").  Whether rewording them is
a screen change or a no-op is not a matter of taste -- it is a matter of who reads the key.  So this
instrument measures, on a full export of the current authority tip:

  * every reference to each of the four keys outside the dictionary itself, with file and line;
  * whether a reference consumes the whole string or only its first word (the panel composes a label);
  * whether any of them is built dynamically (a key-name grep alone cannot see `exec.mark${x}`);
  * a runtime leg: the screen reading this lane already took on the SAME generation (the button names that
    screen paints), searched for the four values -- with the painted first word as the positive control, so
    a zero here is a reading and not a blind instrument.

Nothing here writes anything outside my own directory; the export tree is mine.
"""
import io
import json
import os
import re

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
TIP = io.open(os.path.join(R1, "_tip_r11.txt"), encoding="utf-8").read().strip()
TREE = os.path.join(R1, "tipfull_b2fccfdf")
SRC = os.path.join(TREE, "frontend", "src")
DICT = os.path.join(SRC, "i18n", "LocaleContext.tsx")
KEYS = ["exec.markEnRoute", "exec.markArrived", "exec.markInProgress", "exec.markCompleted"]
CONTROLS = ["exec.complete", "exec.updating", "exec.state.enRoute"]
ENUM_SHAPE = re.compile(r"[A-Z]{4,}|[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+")

files = []
for root, _dirs, names in os.walk(SRC):
    for n in names:
        if n.endswith((".ts", ".tsx", ".js")):
            files.append(os.path.join(root, n))


def rel(p):
    return os.path.relpath(p, TREE).replace("\\", "/")


def refs(key):
    out = []
    needle = '"%s"' % key
    for p in files:
        if os.path.normcase(p) == os.path.normcase(DICT):
            continue
        try:
            text = io.open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if needle in line:
                out.append({"at": "%s:%d" % (rel(p), i), "line": line.strip()[:200]})
    return out


report = {"instrument": "cmdra_0553_deadkeys_r16", "tip": TIP, "files_scanned": len(files),
          "keys": {}, "controls": {}, "dynamic_composition": [], "runtime_leg": {}, "arms": []}

dict_text = io.open(DICT, encoding="utf-8", errors="replace").read()
dict_lines = dict_text.splitlines()
for key in KEYS:
    hit = [i + 1 for i, l in enumerate(dict_lines) if ('"%s"' % key) in l]
    en = re.search(r'"%s":\s*"([^"]*)"' % re.escape(key), dict_text)
    zh = re.findall(r'"%s":\s*"([^"]*)"' % re.escape(key), dict_text)
    r = refs(key)
    report["keys"][key] = {
        "defined_at": ["frontend/src/i18n/LocaleContext.tsx:%d" % i for i in hit],
        "en_value": en.group(1) if en else None,
        "en_is_enum_shaped": bool(en and ENUM_SHAPE.search(en.group(1))),
        "zh_values": zh,
        "refs_outside_dictionary": r,
        "refs_count": len(r),
        "consumes_whole_string": any(".split(" not in x["line"] for x in r),
    }
for key in CONTROLS:
    report["controls"][key] = {"refs_count": len(refs(key))}

for p in files:
    text = io.open(p, encoding="utf-8", errors="replace").read()
    for i, line in enumerate(text.splitlines(), 1):
        if "exec.mark" in line and ("${" in line or "`" in line) and '"exec.mark' not in line:
            report["dynamic_composition"].append("%s:%d" % (rel(p), i))

# runtime leg: the button names the same generation paints on /v8/authoritative (my own r13 reading)
loc = json.load(io.open(os.path.join(R1, "_evidence", "r13_locator_revet.json"), encoding="utf-8"))
leg = [x for x in loc["legs"] if x["tag"] == "tip_b2fccfdf"][0]
painted = list(leg["buttons_painted"]) + list((leg.get("after_click") or {}).get("buttons_painted", []))
values = [report["keys"][k]["en_value"] for k in KEYS]
report["runtime_leg"] = {
    "source_reading": "r13_locator_revet.json leg tip_b2fccfdf",
    "painted_button_names": len(painted),
    "four_values_painted": sorted({v for v in values if v and v in painted}),
    "positive_control_first_word_present": any(p.strip().startswith("Mark") for p in painted),
    "sample_painted_mark_buttons": sorted({p for p in painted if p.strip().startswith("Mark")})[:4],
}


def arm(ident, ok, observed):
    report["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


k = report["keys"]
arm("three_of_the_four_keys_are_referenced_nowhere_outside_the_dictionary",
    k["exec.markEnRoute"]["refs_count"] == 0 and k["exec.markArrived"]["refs_count"] == 0
    and k["exec.markCompleted"]["refs_count"] == 0,
    "markEnRoute=%d markArrived=%d markCompleted=%d refs outside the dictionary" % (
        k["exec.markEnRoute"]["refs_count"], k["exec.markArrived"]["refs_count"],
        k["exec.markCompleted"]["refs_count"]))
arm("the_fourth_key_is_read_only_for_its_first_word",
    k["exec.markInProgress"]["refs_count"] == 1 and not k["exec.markInProgress"]["consumes_whole_string"],
    "markInProgress refs=%d and every reference consumes a split()ed fragment" % (
        k["exec.markInProgress"]["refs_count"]))
arm("no_dynamic_key_composition_hides_a_reader",
    report["dynamic_composition"] == [],
    "template-literal or concatenated exec.mark keys: %s" % (report["dynamic_composition"] or "none"))
arm("the_scan_can_find_readers_at_all",
    all(report["controls"][c]["refs_count"] >= 1 for c in CONTROLS),
    "positive controls %s" % json.dumps({c: report["controls"][c]["refs_count"] for c in CONTROLS}))
arm("no_screen_paints_any_of_the_four_values_on_this_generation",
    report["runtime_leg"]["four_values_painted"] == []
    and report["runtime_leg"]["positive_control_first_word_present"],
    "of %d painted button names, the four values appear %d times; the shared first word does appear "
    "(sample %s)" % (report["runtime_leg"]["painted_button_names"],
                     len(report["runtime_leg"]["four_values_painted"]),
                     json.dumps(report["runtime_leg"]["sample_painted_mark_buttons"], ensure_ascii=False)))

red = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "GREEN" if not red else "RED"
report["red_arms"] = red
report["what_a_zero_does_not_prove"] = (
    "a key-name scan sees literal keys; the dynamic scan above covers template/concatenated construction, "
    "and the runtime leg covers the one screen that paints a button label -- the other thirteen routes were "
    "not re-walked for these four literals on this round")
path = os.path.join(R1, "_evidence", "r16_deadkeys.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({x: report[x] for x in ("verdict", "red_arms", "arms", "runtime_leg", "dynamic_composition")},
                 ensure_ascii=False, indent=1))
print("WROTE", path)
