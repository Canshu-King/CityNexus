"""Locate the RENDER SITE of machine vocabulary that a zh user reads on screen, and say plainly when the
render site is a file another order owns.

Why: ORD-0425 will only be dispatched if I can name files that nobody else is editing.  `PLANNED`,
`PlanVersion 1 · INITIAL`, `NOT_CONFIGURED`, `ADVISORY`, `Asia/Shanghai` and a raw place id are all proven
ON SCREEN (receipts blob bf772e96e171e7cc33b3b3b27b9b7ca7d6360950), but "in a file" is not "rendered from
that file" - an enum constant can sit in ten files and render from one.  So this looks for the shapes that
actually put text on the DOM:
  JSX_TEXT      >TEXT<                       a literal text node
  ATTR_TEMPLATE ${...} inside a template      composed at render time
  BRACE_EXPR    {expr} rendered directly
and reports the enclosing JSX attribute/element so a human can see which expression produced it.

It also prints, per hit, whether the file is claimed by another order, so I never dispatch into a collision.
Read-only.  ASCII stdout only (GBK console).
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"D:\moodle\_qoder_cmdr_scan_8a7665be\frontend\src"
OUT = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\_render_sites_0425_r1.json"

CLAIMED = {
    "app/V8Experience.tsx": "ORD-0419 / ORD-0420 (parallel commander)",
    "styles.css": "ORD-0419 (parallel commander)",
    "features/traveler-twin/TwinPanel.tsx": "ORD-0422",
    "features/recovery/V14RecoveryTruthPanel.tsx": "ORD-0422",
    "features/discovery/RealCityDiscoveryPanel.tsx": "ORD-0422",
    "i18n/LocaleContext.tsx": "ORD-0420 / ORD-0422 (shared dictionary)",
    "features/inbox/JourneyInboxWorkbench.tsx": "ORD-0423",
}

# what a zh user was shown, and the plausible runtime producer to look for
NEEDLES = [
    {"shown": "PLANNED", "screen": "authoritative", "producers": [r"\bPLANNED\b", r"item\.status", r"status"]},
    {"shown": "PlanVersion 1 · INITIAL", "screen": "authoritative",
     "producers": [r"PlanVersion", r"INITIAL", r"plan_version"]},
    {"shown": "NOT_CONFIGURED", "screen": "intelligence", "producers": [r"NOT_CONFIGURED", r"availability"]},
    {"shown": "ADVISORY", "screen": "intelligence", "producers": [r"ADVISORY", r"severity"]},
    {"shown": "Asia/Shanghai", "screen": "live", "producers": [r"Asia/Shanghai", r"time_zone", r"timezone"]},
    {"shown": "place-river-cruise", "screen": "bookings", "producers": [r"place_id", r"place-river-cruise", r"\bid\b"]},
]

files = {}
for dp, dn, fn in os.walk(SRC):
    dn[:] = [d for d in dn if d not in ("node_modules", "dist", ".git")]
    for f in fn:
        if f.endswith((".tsx", ".ts")):
            p = os.path.relpath(os.path.join(dp, f), SRC).replace("\\", "/")
            files[p] = io.open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
print("files:", len(files))

rows = []
for nd in NEEDLES:
    shown = nd["shown"]
    hits = []
    for rel, body in files.items():
        lines = body.split("\n")
        for i, ln in enumerate(lines):
            if shown in ln:
                # classify: does this line actually put the text into the DOM?
                kind = "OTHER"
                if re.search(r">\s*[^<>]*" + re.escape(shown), ln) or re.search(r">\s*" + re.escape(shown), ln):
                    kind = "JSX_TEXT"
                elif re.search(r"\{[^{}]*" + re.escape(shown), ln):
                    kind = "BRACE_EXPR"
                elif re.search(r'aria-|title=|content=|data-', ln):
                    kind = "ATTRIBUTE"
                elif rel == "generated/api.ts":
                    kind = "GENERATED_CONTRACT"
                elif re.search(r"^\s*(export )?(const|type|enum|interface)\b", ln) or '": ' in ln:
                    kind = "DEFINITION_OR_MAP"
                hits.append({"file": rel, "line": i + 1, "kind": kind,
                             "claimed_by": CLAIMED.get(rel, "unclaimed"),
                             "text": ln.strip()[:150]})
    # the render site is a DOM-putting hit; definitions are supporting evidence only
    dom = [h for h in hits if h["kind"] in ("JSX_TEXT", "BRACE_EXPR", "ATTRIBUTE")]
    rows.append({"shown": shown, "screen": nd["screen"], "total_hits": len(hits),
                 "dom_putting_hits": len(dom),
                 "render_candidates": dom[:8],
                 "definition_hits": [h for h in hits if h["kind"] == "DEFINITION_OR_MAP"][:6],
                 "generated_hits": len([h for h in hits if h["kind"] == "GENERATED_CONTRACT"]),
                 "all_files": sorted({h["file"] for h in hits})})

res = {"generated_by": "_render_sites_0425_r1.py", "source_tree": SRC,
       "authoritative_sha": "8a7665be2061a2f38aa2227f81c57003ca4caacb",
       "claimed_files": CLAIMED, "rows": rows}
with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(res, fh, ensure_ascii=False, indent=1)

for r in rows:
    print("=== shown %r on %s | total %d | dom-putting %d | generated %d" % (
        r["shown"], r["screen"], r["total_hits"], r["dom_putting_hits"], r["generated_hits"]))
    for h in r["render_candidates"]:
        print("     DOM  %-58s %5d %-18s claimed=%s" % (h["file"], h["line"], h["kind"], h["claimed_by"]))
    for h in r["definition_hits"]:
        print("     DEF  %-58s %5d" % (h["file"], h["line"]))
    print("     files:", ", ".join(r["all_files"][:8]))
print("wrote", OUT, os.path.getsize(OUT), "B")
