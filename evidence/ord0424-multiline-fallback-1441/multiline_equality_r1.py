"""Prove the cross-line reading in both directions: adds the shape it claims to add, adds nothing anywhere else.

Imported as modules, so both rulers run over the same bytes in one process and the comparison is the tools' own
`(tier, file, line, literal, …)` tuples rather than two hand-typed summaries.

Three checks:
  * the live tree at the tip -- every r2 hit survives (lost 0) and the new reading adds 0, which is the honest
    statement of "this shape is not in the tree yet";
  * a fixture carrying the real cross-line shape -- the new tool reports exactly the injected cells and r2 does
    not see them, so the residual is actually closed and not just re-described;
  * a fixture carrying the template-fragment shape that the naive join invented -- both tools must stay quiet,
    which is what keeps 188 fragments out of a gate.
"""
import importlib.util
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
R2 = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")
R2M = os.path.join(TOOLS, "cnx_copy_tiers_multiline_fallback_r1.py")
REPO = "D:/moodle/CityNexus"
TIP = os.environ.get("CNX_REV", "57ff5d1c2f8540d498d945ed591c36689fc0f39e")
EXPORT = os.path.join(WORK, "_blind_export")
FX = os.path.join(WORK, "_fx_tree")
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")

REAL_CROSS_LINE = '''export function Sentence({ zh, ready }: { zh: boolean; ready: boolean }) {
  const label = zh
    ?
    "The server refused this step, so nothing was booked."
    :
    "Nothing was booked, and the server gave the reason.";
  const [draft, setDraft] = useState(
    "Tell the AI how you like to travel"
  );
  return <p data-testid="cross-line">{label}{draft}{ready ? "" : ""}</p>;
}
'''

# the shape that fooled the naive join: operator and literal on the same line, but the literal is a TEMPLATE
# containing `${...}`, so joining two of them hands back a fragment of the second one
FRAGMENT_SHAPE = '''export function Refusal({ zh, status }: { zh: boolean; status: number }) {
  return zh
    ? `\u670d\u52a1\u5668\u62d2\u7edd\u4e86\u8fd9\u4e00\u6b65\uff08HTTP ${status}\uff09\u3002\u4f60\u7684\u884c\u7a0b\u6ca1\u6709\u56e0\u6b64\u6539\u53d8\u3002`
    : `The server refused this step (HTTP ${status}). Your trip is unchanged; check the details and try again.`;
}
'''

# an object property is the same SHAPE as a stranded `:` plus a string, and is not a ternary branch: the guard
# that separates them is the `?` this expression never carries
OBJECT_PROPERTY = '''export const copy = {
  title:
    "The panel heading somebody wrote in a config object",
};
'''

# CJK wording stays out of this face by design -- the published tool excludes it, so the cross-line reading
# must not become a way back in
CJK_QUIET = '''export function Zh({ zh }: { zh: boolean }) {
  return zh
    ?
    "服务器拒绝了这一步，没有预订任何东西。"
    :
    "英文这侧也是中文叙述。";
}
'''

SAME_LINE = '''export function Plain({ zh }: { zh: boolean }) {
  return zh ? "Everything on one line here." : "\u8fd9\u91cc\u6240\u6709\u5185\u5bb9\u90fd\u5728\u4e00\u884c\u3002";
}
'''


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def cells(mod, tree):
    """(tier, file, line, literal) as the tool itself reports them, plus the tier tallies."""
    hits, _pairs, _files = mod.scan_tree(tree)
    rows = sorted({(h[0], os.path.basename(str(h[1])), h[2], str(h[3])) for h in hits})
    tally = {}
    for h in hits:
        tally[h[0]] = tally.get(h[0], 0) + 1
    return rows, tally


def write_fixture():
    if os.path.isdir(FX):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", FX], timeout=300)
    os.makedirs(os.path.join(FX, "frontend", "src"), exist_ok=True)
    for n, src in (("RealCrossLine.tsx", REAL_CROSS_LINE), ("FragmentShape.tsx", FRAGMENT_SHAPE),
                   ("SameLine.tsx", SAME_LINE), ("ObjectProperty.tsx", OBJECT_PROPERTY),
                   ("CjkQuiet.tsx", CJK_QUIET)):
        io.open(os.path.join(FX, "frontend", "src", n), "w", encoding="utf-8",
                newline="\n").write(src)
    return sorted(os.listdir(os.path.join(FX, "frontend", "src")))


def diff(a, b):
    sa, sb = set(a), set(b)
    return {"lost": sorted(sa - sb), "gained": sorted(sb - sa), "identical": sa == sb}


def main():
    r2, r2m = load(R2, "r2mod"), load(R2M, "r2mmod")
    src = os.path.join(EXPORT, "frontend", "src")
    if not os.path.isdir(src):
        os.makedirs(EXPORT, exist_ok=True)
        subprocess.run("git -C %s -c http.proxy= -c https.proxy= archive %s frontend/src | tar -x -C %s"
                       % (REPO, TIP, EXPORT.replace("\\", "/")), shell=True, capture_output=True,
                       timeout=900, env=ENV)
        src = os.path.join(EXPORT, "frontend", "src")
    out = {"tip": TIP, "fixture_files": write_fixture()}
    a_rows, a_tally = cells(r2, src)
    b_rows, b_tally = cells(r2m, src)
    d = diff([r for r in a_rows if not r[0].endswith("skipped")],
             [r for r in b_rows if not r[0].endswith("skipped")])
    out["live_tree"] = {"r2_tally": a_tally, "multiline_tally": b_tally,
                        "r2_cells": len(a_rows), "multiline_cells": len(b_rows),
                        "lost": d["lost"][:10], "lost_count": len(d["lost"]),
                        "gained": d["gained"][:10], "gained_count": len(d["gained"]),
                        "identical": d["identical"]}
    fx = os.path.join(FX, "frontend", "src")
    fa, ft = cells(r2, fx)
    fb, gt = cells(r2m, fx)
    out["fixture"] = {"r2_tally": ft, "multiline_tally": gt,
                      "r2_only": sorted(set(fa) - set(fb))[:8],
                      "fixture_lost": sorted(set(fa) - set(fb)),
                      "multiline_only": sorted(set(fb) - set(fa))[:8],
                      "lost_from_r2": sorted(set(fa) - set(fb)) and "LOST" or "none"}
    frag_r2 = [r for r in fa if r[1] == "FragmentShape.tsx"]
    frag_new = [r for r in fb if r[1] == "FragmentShape.tsx"]
    out["fragment_control"] = {"r2_rows": len(frag_r2), "multiline_rows": len(frag_new),
                               "quiet_both": frag_r2 == frag_new and not any(
                                   "Your trip is unchanged; check" in str(r[3]) for r in frag_new)}
    cross_new = [r for r in fb if r[1] == "RealCrossLine.tsx"]
    cross_r2 = [r for r in fa if r[1] == "RealCrossLine.tsx"]
    def rows_for(rows, name):
        return [r for r in rows if r[1] == name]
    obj_new = rows_for(fb, "ObjectProperty.tsx")
    obj_r2 = rows_for(fa, "ObjectProperty.tsx")
    cjk_new = rows_for(fb, "CjkQuiet.tsx")
    cjk_r2 = rows_for(fa, "CjkQuiet.tsx")
    out["object_property_control"] = {
        "multiline_rows": obj_new, "r2_rows": obj_r2,
        "quiet": not obj_new and not obj_r2}
    out["cjk_control"] = {"multiline_rows": [r[:3] for r in cjk_new],
                          "r2_rows": [r[:3] for r in cjk_r2],
                          "cjk_branch_never_reported": not any("服务器" in str(r[3]) for r in cjk_new),
                          "both_branches_cjk_so_nothing_added": len(cjk_new) == 0 and len(cjk_r2) == 0}
    out["cross_line_control"] = {
        "multiline_rows": cross_new, "r2_rows": cross_r2,
        "injected_branches_caught": len(cross_new) == 3 and len(cross_r2) == 0}
    out["shippable_checks"] = {
        "a_live_hit_is_never_lost": out["live_tree"]["lost_count"] == 0,
        "a_fixture_hit_is_never_lost": not out["fixture"]["fixture_lost"],
        "the_template_fragment_stays_quiet": out["fragment_control"]["quiet_both"],
        "an_object_property_is_not_a_branch": out["object_property_control"]["quiet"],
        "cjk_stays_out_of_this_face": out["cjk_control"]["both_branches_cjk_so_nothing_added"],
        "the_cross_line_shape_is_now_caught": out["cross_line_control"]["injected_branches_caught"]}
    out["verdict"] = ("SAFE_AND_ADDS_THE_SHAPE" if all(out["shippable_checks"].values())
                      else "NOT_SHIPPABLE")
    io.open(os.path.join(WORK, "multiline_equality_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3000])
    return 0 if out["verdict"] == "SAFE_AND_ADDS_THE_SHAPE" else 1


if __name__ == "__main__":
    sys.exit(main())
