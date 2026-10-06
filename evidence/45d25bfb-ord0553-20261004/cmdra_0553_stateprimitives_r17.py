"""ORD-0553 r17 -- the third ruling cell, measured: is the `replaceAll("_", " ")` fallback reachable?

`frontend/src/features/execution/V12StatePrimitives.tsx` carries a fallback that prints a status name with
its underscores turned into spaces.  For a contract name the screen's own map does not carry (PLANNED, READY,
CANCELLED), that prints the machine token to the traveller -- which is the defect this order is about.  The
open question was whether any screen can reach it today.  "No screen imports it" is a claim about a graph, so
this instrument walks the graph:

  * the fallback line itself, verbatim, and which exported components call the helper that holds it;
  * every importer of the module, with the names it imports;
  * reachability from the app entry (`frontend/src/main.tsx`) over relative imports -- a stories file is not
    reachable from an entry, and a panel that imports a *different* export is not evidence for this one;
  * dynamic imports of the module (a static import scan cannot see `import(...)`);
  * a runtime leg on the same generation: the fourteen-route census this lane already took, searched for
    spaced-enum remnants (ROUTE / PROGRESS / NOT / STARTED tokens), with a positive control from the same
    screen area so a zero is a reading and not a blind instrument.
"""
import io
import json
import os
import re

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
TIP = io.open(os.path.join(R1, "_tip_r11.txt"), encoding="utf-8").read().strip()
TREE = os.path.join(R1, "tipfull_b2fccfdf")
SRC = os.path.join(TREE, "frontend", "src")
MODULE_REL = "frontend/src/features/execution/V12StatePrimitives.tsx"
MODULE = os.path.join(TREE, MODULE_REL.replace("/", os.sep))
ENTRY = os.path.join(SRC, "main.tsx")

report = {"instrument": "cmdra_0553_stateprimitives_r17", "tip": TIP, "module": MODULE_REL,
          "fallback": {}, "callers": [], "importers": [], "dynamic_imports": [], "reachability": {},
          "runtime_leg": {}, "arms": []}

text = io.open(MODULE, encoding="utf-8", errors="replace").read()
lines = text.splitlines()
fb = [i + 1 for i, l in enumerate(lines) if 'replaceAll("_", " ")' in l]
report["fallback"] = {"line": ["%s:%d" % (MODULE_REL, i) for i in fb],
                      "verbatim": lines[fb[0] - 1].strip() if fb else None}

# exported components that call the helper holding the fallback
helper = re.search(r"function (\w+)\(state[^)]*\)", text)
helper_name = helper.group(1) if helper else None
report["fallback"]["helper"] = helper_name
blocks = re.split(r"\nexport function ", text)
for b in blocks[1:]:
    name = b.split("(", 1)[0].strip()
    if helper_name and re.search(r"\b%s\(" % re.escape(helper_name), b):
        report["callers"].append({"export": name, "line": "%s:%d" % (
            MODULE_REL, text[:text.index("export function " + name)].count("\n") + 1)})

# every importer of the module, and the names it takes
for root, _d, names in os.walk(SRC):
    for n in names:
        if not n.endswith((".ts", ".tsx")):
            continue
        p = os.path.join(root, n)
        if os.path.normcase(p) == os.path.normcase(MODULE):
            continue
        t = io.open(p, encoding="utf-8", errors="replace").read()
        for i, l in enumerate(t.splitlines(), 1):
            if "V12StatePrimitives" in l and l.lstrip().startswith("import"):
                taken = re.search(r"\{([^}]*)\}", l)
                report["importers"].append({
                    "file": os.path.relpath(p, TREE).replace("\\", "/"), "line": i,
                    "names": [x.strip() for x in (taken.group(1).split(",") if taken else []) if x.strip()]})
            if "import(" in l and "V12StatePrimitives" in l:
                report["dynamic_imports"].append("%s:%d" % (os.path.relpath(p, TREE).replace("\\", "/"), i))

# reachability from the app entry over relative imports
graph = {}
real = {}
for root, _d, names in os.walk(SRC):
    for n in names:
        if not n.endswith((".ts", ".tsx")):
            continue
        p = os.path.join(root, n)
        real[os.path.normcase(p)] = p
        t = io.open(p, encoding="utf-8", errors="replace").read()
        deps = set()
        # static imports and literal dynamic imports are both edges; a lazily mounted shell would
        # otherwise read as unreachable and the whole leg would answer "nothing is reachable".
        for m in re.finditer(r'(?:from\s+|import\()"(\.[^"]+)"', t):
            target = os.path.normpath(os.path.join(os.path.dirname(p), m.group(1)))
            for cand in (target + ".tsx", target + ".ts", target + os.sep + "index.ts",
                         target + os.sep + "index.tsx"):
                if os.path.exists(cand):
                    deps.add(os.path.normcase(cand))
                    break
        graph[os.path.normcase(p)] = deps
seen, stack = set(), [os.path.normcase(ENTRY)]
while stack:
    cur = stack.pop()
    if cur in seen:
        continue
    seen.add(cur)
    stack.extend(graph.get(cur, ()))
# the graph is keyed by normcase()d paths (Windows lowercases), so the display set has to be rebuilt from
# the real paths -- the first version of this leg compared lowercased keys against mixed-case relative
# paths and reported every file, including the app shell, as unreachable.
reachable = {os.path.relpath(real[k], TREE).replace("\\", "/") for k in seen if k in real}
report["reachability"] = {
    "entry": "frontend/src/main.tsx",
    "files_reachable": len(reachable),
    "module_reachable": MODULE_REL in reachable,
    "importers_reachable": {i["file"]: i["file"] in reachable for i in report["importers"]},
    "caller_exports_imported_by": {c["export"]: sorted(
        {i["file"] for i in report["importers"] if c["export"] in i["names"]}) for c in report["callers"]},
}

# runtime leg: the same generation's census, both arms
tokens = {}
for arm, f in (("en", "r11_walk_en_49881.json"), ("zh", "r11_walk_zh_49881.json")):
    d = json.load(io.open(os.path.join(R1, "_evidence", f), encoding="utf-8"))
    got = set()
    for route, v in d["perRoute"].items():
        for h in v.get("hits", []):
            if h.get("token"):
                got.add(h["token"])
    tokens[arm] = sorted(got)
REMNANTS = {"ROUTE", "PROGRESS", "NOT", "STARTED"}
report["runtime_leg"] = {
    "source": "r11_walk_{en,zh}_49881.json (fourteen routes, same tip generation)",
    "remnant_tokens_found": {a: sorted(set(t) & REMNANTS) for a, t in tokens.items()},
    "positive_control_tokens_from_the_same_area": sorted(
        set(tokens["en"]) & {"AUTHORITATIVE", "NEXT", "TRIP", "REALITY"}),
}


def arm(ident, ok, observed):
    report["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


arm("the_fallback_line_is_still_there", bool(report["fallback"]["line"]),
    "verbatim %r at %s" % (report["fallback"]["verbatim"], report["fallback"]["line"]))
arm("the_graph_can_see_the_app_shell_at_all",
    "frontend/src/app/V8Experience.tsx" in reachable
    and "frontend/src/features/studio/V12TripStudioPanel.tsx" in reachable,
    "%d files reachable from the entry; shell reachable=%s, studio panel reachable=%s" % (
        len(reachable), "frontend/src/app/V8Experience.tsx" in reachable,
        "frontend/src/features/studio/V12TripStudioPanel.tsx" in reachable))
arm("the_fallback_is_held_by_exactly_the_two_unused_components",
    [c["export"] for c in report["callers"]] == ["ActivityCard", "LiveJourney"],
    "callers of %s(): %s" % (helper_name, [c["export"] for c in report["callers"]]))
arm("no_reachable_screen_imports_those_components",
    all(not any(f in reachable for f in v) for v in report["reachability"]["caller_exports_imported_by"].values()),
    "imported by %s; reachable from the entry: %s" % (
        json.dumps(report["reachability"]["caller_exports_imported_by"]),
        json.dumps(report["reachability"]["importers_reachable"])))
arm("the_product_importer_takes_a_different_export",
    all(not set(i["names"]) & {c["export"] for c in report["callers"]}
        for i in report["importers"] if report["reachability"]["importers_reachable"].get(i["file"])),
    "reachable importer(s) take %s" % json.dumps(
        [i for i in report["importers"] if report["reachability"]["importers_reachable"].get(i["file"])]))
arm("no_dynamic_import_hides_a_screen",
    report["dynamic_imports"] == [],
    "dynamic imports of the module: %s" % (report["dynamic_imports"] or "none"))
arm("the_census_sees_this_screen_area_and_finds_no_spaced_enum",
    all(v == [] for v in report["runtime_leg"]["remnant_tokens_found"].values())
    and len(report["runtime_leg"]["positive_control_tokens_from_the_same_area"]) >= 1,
    "remnants %s; positive control tokens %s" % (
        json.dumps(report["runtime_leg"]["remnant_tokens_found"]),
        json.dumps(report["runtime_leg"]["positive_control_tokens_from_the_same_area"])))

red = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "GREEN" if not red else "RED"
report["red_arms"] = red
report["what_a_zero_does_not_prove"] = (
    "reachability is over relative imports from main.tsx; a screen mounted from a route table built at "
    "runtime (a string map of component names) would not appear here, so the graph leg is named as a graph "
    "leg.  The runtime leg covers the fourteen routes this lane walks, not every route the product has.")
path = os.path.join(R1, "_evidence", "r17_stateprimitives.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k: report[k] for k in ("verdict", "red_arms", "arms", "fallback", "callers",
                                         "reachability", "runtime_leg")}, ensure_ascii=False, indent=1))
print("WROTE", path)
