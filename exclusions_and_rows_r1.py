"""ORD-0424, the two readings the order asked for by name: the 22 rows, and the exclusions.

H6 is the exclusion proof the tip cannot give me by itself. The five seeded place names
(`Tech Art Center`, `Nexus River Cruise Pier`, `Central Food Hall`, `Riverside Museum`,
`Skyline Dinner House`) are data, not components - no panel writes them as a literal - so scanning the
real tree proves nothing about the veto. This builds one fixture per side of the rule from the tree's
own `data/mock/places.json`: the same element text, once with the seed directory supplied and once
without. With it the face must exclude and name the file and offset; without it the face must report
the hit. A veto that fires either way is a hard-coded list; a veto that flips with the data is a rule.

H7 prints the 22 rows as `file:line`, the tier the new face assigned, and whether ORD-0422's landing
removed it - the before/after pair the order asked for.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
INV = json.load(io.open(os.path.join(WORK, "inventory_r1.json"), encoding="utf-8"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def norm(p):
    return str(p).replace("\\", "/")


def h6(mod, tree):
    """One fixture, two runs: the seed veto must follow the data directory, not a name list."""
    fx = os.path.join(WORK, "fx_seed")
    if os.path.isdir(fx):
        shutil.rmtree(fx)
    src = os.path.join(tree, "frontend", "src")
    data = os.path.join(tree, "data", "mock")
    names = []
    places = os.path.join(data, "places.json")
    if os.path.isfile(places):
        txt = io.open(places, encoding="utf-8", errors="replace").read()
        names = re.findall(r'"name"\s*:\s*"([^"\n]{3,60})"', txt)[:3]
    assert names, "no seed names read out of %s" % places
    # a fixture that renders exactly those names, plus one brand word and one invented sentence
    body = ["import { useState } from \"react\";", "", "export function SeedShowcase() {",
            '  const [note] = useState("This sentence is not in the seed data at all");',
            "  return (", '    <div data-testid="seed-showcase">',
            "      <span>CityNexus Copilot</span>", "      <span>{note}</span>"]
    for n in names:
        body.append("      <span>%s</span>" % n)
    body += ["    </div>", "  );", "}", ""]
    os.makedirs(fx, exist_ok=True)
    io.open(os.path.join(fx, "SeedShowcase.tsx"), "w", encoding="utf-8",
            newline="\n").write("\n".join(body))
    fixture = os.path.join(fx, "SeedShowcase.tsx")
    text = io.open(os.path.join(fx, "SeedShowcase.tsx"), encoding="utf-8").read()
    lines = text.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    seeds_with = mod.seed_strings(data)
    hits_with = mod.fallback_hits(text, fx + "/SeedShowcase.tsx", lines, starts, seeds_with)
    hits_without = mod.fallback_hits(text, fx + "/SeedShowcase.tsx", lines, starts, {})
    def find(hits, needle):
        for h in hits:
            if needle in h[3]:
                return h
        return None
    rows = []
    for n in names:
        a, b = find(hits_with, n), find(hits_without, n)
        rows.append({"seed_name": n,
                     "with_seed_directory": (a[0] + " " + a[4][:70]) if a else "no row at all",
                     "without_seed_directory": (b[0]) if b else "no row",
                     "veto_follows_the_data": bool(a and a[0] == "C-skipped" and b and b[0] == "C")})
    brand = find(hits_with, "CityNexus Copilot")
    invented = find(hits_with, "This sentence is not in the seed data")
    return {"fixture_lines": len(lines), "seed_names_taken_from": norm(places),
            "seed_names_used": names, "rows": rows,
            "brand_word_row": (brand[0] + " | " + brand[4]) if brand else None,
            "invented_sentence_row": (invented[0] + " | " + invented[4][:60]) if invented else None,
            "all_seed_vetoes_flip_with_data": all(r["veto_follows_the_data"] for r in rows)}


def h7(mod, before, after, tree_hits):
    """The 22 rows as the new face sees them, before and after ORD-0422 landed."""
    def scan(tree):
        hits, _p, _f = mod.scan_tree(os.path.join(tree, "frontend", "src"),
                                     os.path.join(tree, "data", "mock"))
        return hits
    hb, ha = scan(before), scan(after)

    def look(hits, f, line, string):
        for h in hits:
            if norm(h[1]).endswith(f) and abs(h[2] - line) <= 2 and (
                    string.strip()[:22] in h[3] or h[3][:22] in string.strip()):
                return h
        return None
    rows = []
    for item in INV["rows"]:
        f = item["file"].replace("frontend/src/", "")
        b = look(hb, f, item["line"], item["string"])
        a = look(ha, f, item["line"], item["string"])
        rows.append({"file": f, "inventory_line": item["line"], "string": item["string"][:64],
                     "origin_shape": item["origin_shape"], "seen_in_zh_receipt": item["seen_in_zh_receipt"],
                     "before_hit": None if not b else "%s:%d tier %s render %s shape %s" % (
                         f, b[2], b[0], b[6], b[4].split(":")[0]),
                     "before_render_tier": None if not b else b[6],
                     "after_hit": None if not a else "%s:%d tier %s" % (f, a[2], a[0]),
                     "removed_by_ord0422": bool(b and not a)})
    return rows


def main():
    mod = load(os.path.join(TOOLS, "cnx_copy_tiers_r2.py"), "tiers_r2")
    before, after = os.path.join(WORK, "tree_before"), os.path.join(WORK, "tree_after")
    out = {"h6_seed_veto": h6(mod, before), "h7_rows": h7(mod, before, after, None)}
    io.open(os.path.join(WORK, "exclusions_and_rows.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    h6r = out["h6_seed_veto"]
    print("H6 fixture lines", h6r["fixture_lines"], "| seed names taken from", h6r["seed_names_taken_from"])
    for r in h6r["rows"]:
        print("   %-26s with=%-14s without=%-8s flips=%s" % (
            r["seed_name"], r["with_seed_directory"][:14], r["without_seed_directory"],
            r["veto_follows_the_data"]))
    print("   brand row:", (h6r["brand_word_row"] or "")[:110])
    print("   invented row:", (h6r["invented_sentence_row"] or "")[:90])
    print("   all seed vetoes flip with the data:", h6r["all_seed_vetoes_flip_with_data"])
    rows = out["h7_rows"]
    print("H7: %d rows, before-hit %d, removed by ORD-0422 %d" % (
        len(rows), sum(1 for r in rows if r["before_hit"]),
        sum(1 for r in rows if r["removed_by_ord0422"])))
    for r in rows:
        print("   %-52s :%-5d %-16s %s | %s" % (r["file"], r["inventory_line"], r["origin_shape"],
                                                (r["before_hit"] or "MISSING")[:46],
                                                (r["after_hit"] or "gone after ORD-0422")[:34]))
    return 0 if h6r["all_seed_vetoes_flip_with_data"] else 1


if __name__ == "__main__":
    sys.exit(main())
