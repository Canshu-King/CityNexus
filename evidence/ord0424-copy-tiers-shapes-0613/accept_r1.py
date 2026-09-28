"""ORD-0424 acceptance harness: does the widened face hit the 22, and did the old face keep its own?

Nothing here is parsed out of a pretty-printed report; the two generations are imported as modules
and `scan_tree()` is called on real trees, so the hit tuples are the same objects the tool gates on.

Arms:
  H1  every one of the 22 inventory rows (blob 353d1c4f96945de517cacf1ef1c8856345d812f8) must appear
      as a tier C hit in the r2 reading of tip 8a7665be, at the same file and within +/-2 lines of
      the line the inventory names. Reported per row, with the slot and render tier the tool derived.
  H2  no hit of the published r1 reading may disappear from r2: the (file, line, literal) set of
      tiers A/B must be a subset of r2's, and the count must be equal. This is the "do not lose the
      73" criterion, checked as a set and not as a number.
  H3  brand words and seed place names are excluded, and the report names the rule and the data file
      and offset it matched - the 5 seeded names of this tip must show up as exclusions when a panel
      renders them verbatim.
  H4  ORD-0422 landed, so the same r2 run over the tree AFTER it must report fewer C hits in the
      three files it touched than the tree BEFORE it - a red reading and a green-ward reading from
      the same command, which is what a lane gets judged on.
  H5  the tool's own injected-defect arms still pass on r2, including the one the published face
      wrote to keep a media-type ternary quiet.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys

TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
INV = json.load(io.open(os.path.join(WORK, "inventory_r1.json"), encoding="utf-8"))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan(mod, tree):
    src = os.path.join(tree, "frontend", "src")
    data = os.path.join(tree, "data", "mock")
    data = data if os.path.isdir(data) else None
    try:
        return mod.scan_tree(src, data)
    except TypeError:
        # the published generation takes no seed directory: it has no shape exclusions to make
        return mod.scan_tree(src)


def norm(p):
    return p.replace("\\", "/")


def main():
    r1 = load(os.path.join(TOOLS, "cnx_copy_tiers_r1.py"), "tiers_r1")
    r2 = load(os.path.join(TOOLS, "cnx_copy_tiers_r2.py"), "tiers_r2")
    before = os.path.join(WORK, "tree_before")
    after = os.path.join(WORK, "tree_after")

    h1_before, pairs_b, files_b = scan(r1, before)
    h2_before, _p2, files2_b = scan(r2, before)
    h2_after, _p3, files2_a = scan(r2, after)

    old_ab = {(norm(h[1]), h[2], h[3]) for h in h1_before if h[0] in ("A", "B")}
    new_ab = {(norm(h[1]), h[2], h[3]) for h in h2_before if h[0] in ("A", "B")}
    new_c = [h for h in h2_before if h[0] == "C"]
    new_c_skipped = [h for h in h2_before if h[0] == "C-skipped"]

    # H1: per-row alignment with the inventory the commander pinned
    rows = []
    for item in INV["rows"]:
        f = item["file"].replace("frontend/src/", "")
        want_line = item["line"]
        want = item["string"]
        cand = [h for h in h2_before
                if norm(h[1]).endswith(f) and abs(h[2] - want_line) <= 2]
        exact = [h for h in cand if want.strip()[:24] in h[3] or h[3][:24] in want.strip()]
        rows.append({
            "file": f, "inventory_line": want_line, "string": want, "origin_shape": item["origin_shape"],
            "seen_in_zh_receipt": item["seen_in_zh_receipt"],
            "hits_within_2_lines": [
                {"line": h[2], "tier": h[0], "literal": h[3][:70], "why": h[4][:90],
                 "render_tier": h[6], "slot": h[7]} for h in cand],
            "matched_by_string": bool(exact),
            "matched_line": (exact[0][2] if exact else None),
            "render_tier": (exact[0][6] if exact else None),
            "slot": (exact[0][7] if exact else None),
        })

    # H3: which named exclusions fired, and what they point at
    excluded = [{"file": norm(h[1]), "line": h[2], "literal": h[3][:70], "why": h[4]}
                for h in new_c_skipped]

    # H4: the three files ORD-0422 touched, before vs after, same command
    touched = ("features/traveler-twin/TwinPanel.tsx",
               "features/recovery/V14RecoveryTruthPanel.tsx",
               "features/discovery/RealCityDiscoveryPanel.tsx")

    def c_in(hits, suffix):
        return [h for h in hits if h[0] == "C" and norm(h[1]).endswith(suffix)]

    after_by_file = {s: len(c_in(h2_after, s)) for s in touched}
    before_by_file = {s: len(c_in(h2_before, s)) for s in touched}

    # H5: the tool's own arms
    mt = subprocess.run([sys.executable, os.path.join(TOOLS, "cnx_copy_tiers_r2.py"),
                         "--i18n", os.path.join(before, "frontend/src/i18n/LocaleContext.tsx"),
                         "--src", os.path.join(before, "frontend", "src"),
                         "--mutant", "--baseline", "SELF"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        timeout=1200, cwd=before)

    out = {
        "schema": "CNX_S4_ORD0424_ACCEPT_R1",
        "trees": {"before": "8a7665be2061a2f38aa2227f81c57003ca4caacb",
                  "after": "live tip after ORD-0422 landed",
                  "files_scanned_r1": files_b, "files_scanned_r2_before": files2_b,
                  "files_scanned_r2_after": files2_a},
        "H1_inventory_alignment": {
            "rows": len(INV["rows"]),
            "matched_by_string": sum(1 for r in rows if r["matched_by_string"]),
            "missed": [r for r in rows if not r["matched_by_string"]],
            "per_row": rows},
        "H2_old_hits_preserved": {
            "r1_ab_hits": len(old_ab), "r2_ab_hits": len(new_ab),
            "lost": sorted("%s:%d %r" % x for x in (old_ab - new_ab)),
            "gained_within_ab": sorted("%s:%d %r" % x for x in (new_ab - old_ab)),
            "identical": old_ab == new_ab},
        "H3_shape_hits_and_exclusions": {
            "tier_C": len(new_c), "tier_C_skipped": len(new_c_skipped),
            "by_shape": {}, "exclusions": excluded[:40],
            "seed_directory_used": bool(os.path.isdir(os.path.join(before, "data/mock")))},
        "H4_before_after_same_command": {
            "by_file_before": before_by_file, "by_file_after": after_by_file,
            "total_C_before": len(new_c), "total_C_after": len([h for h in h2_after if h[0] == "C"])},
        "H5_selftest": {"exit": mt.returncode,
                        "tail": (mt.stdout or "").strip().splitlines()[-6:],
                        "stderr_tail": (mt.stderr or "").strip().splitlines()[-3:]},
    }
    shapes = {}
    for h in new_c:
        k = h[4].split(":")[0]
        shapes[k] = shapes.get(k, 0) + 1
    out["H3_shape_hits_and_exclusions"]["by_shape"] = shapes
    out["H3_shape_hits_and_exclusions"]["tier_C_total"] = len(new_c)
    out["H1_inventory_alignment"]["matched"] = sum(1 for r in rows if r["matched_by_string"])
    out["H1_inventory_alignment"]["rows_total"] = len(INV["rows"])

    io.open(os.path.join(WORK, "accept_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: out[k] for k in
                      ("trees", "H2_old_hits_preserved", "H4_before_after_same_command",
                       "H5_selftest")}, ensure_ascii=False, indent=1)[:1800])
    print("H1 matched %d / %d rows" % (out["H1_inventory_alignment"]["matched_by_string"],
                                       out["H1_inventory_alignment"]["rows"]))
    for r in out["H1_inventory_alignment"]["missed"]:
        print("  MISSED %s:%d %r shape=%s candidates=%s" % (
            r["file"], r["inventory_line"], r["string"][:40], r["origin_shape"],
            json.dumps(r["hits_within_2_lines"], ensure_ascii=False)[:220]))
    print("H3", json.dumps(out["H3_shape_hits_and_exclusions"]["by_shape"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
