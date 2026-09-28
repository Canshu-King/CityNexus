"""ORD-0398 step 1 -- inventory only. Nothing is edited here.

Rows are grouped by what a reader needs to decide "does this need the named
constructor":

  fields            which whitelist readouts the line touches
  through_attribution  is it produced by frontend/src/lib/failureAttribution.ts's
                       Attribution shape (that module, or an import of it)
  hand_built        a `${...}` string assembled at the call site -- the shape the
                    order forbids
  reaches_text      could this string end up in innerText (rendered or state message)
  formats_moment    how a timestamp is turned into words on this line
"""
import io
import os
import re

TREE = os.environ.get("ORD0398_TREE", ".")
SRC = os.path.join(TREE, "frontend/src")
FIELDS = ["http_status", "content_type", "body_bytes", "response_received", "elapsed_ms", "request_id"]
MOMENTS = ["latest_provider_capture_at", "captured_at", "expires_at", "freshness"]
HAND = re.compile(r"\$\{[^}]*(status|bytes|\bms\b|elapsed|content_type|http_status)[^}]*\}")
FMT = re.compile(r"toLocaleTimeString|toLocaleDateString|toLocaleString|Intl\.DateTimeFormat|new Date\(|\bdate\(")

attr_module = "frontend/src/lib/failureAttribution.ts"
files_using_attr = set()
for root, _dirs, files in os.walk(SRC):
    for name in files:
        if not name.endswith((".ts", ".tsx")):
            continue
        p = os.path.join(root, name)
        rel = os.path.relpath(p, TREE).replace("\\", "/")
        t = io.open(p, encoding="utf-8", errors="replace").read()
        if re.search(r"failureAttribution|from \"[./]*lib/failureAttribution\"", t) or rel == attr_module:
            files_using_attr.add(rel)

rows = []
for rel in sorted(files_using_attr | {
    os.path.relpath(os.path.join(root, n), TREE).replace("\\", "/")
    for root, _d, fs in os.walk(SRC) for n in fs if n.endswith((".ts", ".tsx"))
}):
    p = os.path.join(TREE, rel)
    if not os.path.exists(p) or "/generated/" in rel:
        continue
    src = io.open(p, encoding="utf-8", errors="replace").read().split("\n")
    for i, ln in enumerate(src, 1):
        fl = [f for f in FIELDS if f in ln]
        mo = [m for m in MOMENTS if m in ln]
        if not fl and not mo:
            continue
        stripped = ln.strip()
        if stripped.startswith(("//", "*", "/*")):
            kind = "comment"
        elif re.match(r"^\s*[\w?]+\[?\]?\??:\s", stripped) and "=" not in stripped.split(":")[0]:
            kind = "type-or-interface member"
        elif re.match(r"^\s*(import|export type|export interface)\b", stripped):
            kind = "import/type surface"
        elif '="' in stripped or re.search(r"data-[a-z-]+=\{", stripped) and "{" not in stripped.split("data-")[0]:
            kind = "attribute"
        else:
            kind = "code"
        rows.append({
            "loc": "%s:%d" % (rel, i),
            "fields": ",".join(fl) or "-",
            "moments": ",".join(mo) or "-",
            "through": "yes" if rel == attr_module else ("importer" if rel in files_using_attr else "no"),
            "hand_built": "yes" if HAND.search(stripped) else "no",
            "kind": kind,
            "fmt": ",".join(sorted({m.group(0) for m in FMT.finditer(stripped)})) or "-",
            "text": stripped[:96].replace("\t", " "),
        })

out = []
P = out.append
P("# ORD-0398 step 1 -- where the freshness/attribution readouts are written today")
P("tip 0598e4d17202fd0619592a40e617c67b2108afd3")
P("command: python RELATION/ord0398_census.py (this file) -- scanner over frontend/src, excluding frontend/src/generated")
P("fields scanned: %s" % " ".join(FIELDS))
P("moment fields scanned: %s" % " ".join(MOMENTS))
P("Attribution shape owner: %s (type at :53, reason at :54, evidence_kind at :56)" % attr_module)
P("files importing/owning that shape: %d" % len(files_using_attr))
P("")
P("loc\tfields\tmoments\tthrough_attribution\thand_built\tkind\tformats_moment\tsource_line")
for r in rows:
    P("\t".join([r["loc"], r["fields"], r["moments"], r["through"], r["hand_built"], r["kind"], r["fmt"], r["text"]]))

code_rows = [r for r in rows if r["kind"] == "code"]
hand = [r for r in rows if r["hand_built"] == "yes"]
nonattr = [r for r in code_rows if r["through"] == "no"]
mom_rows = [r for r in rows if r["moments"] != "-"]
fmts = sorted({f for r in rows for f in r["fmt"].split(",") if f != "-"})
P("")
P("## totals")
P("rows_total=%d  code_rows=%d  comment_rows=%d  type_rows=%d  attribute_rows=%d" % (
    len(rows), len(code_rows),
    sum(1 for r in rows if r["kind"] == "comment"),
    sum(1 for r in rows if r["kind"].startswith(("type", "import"))),
    sum(1 for r in rows if r["kind"] == "attribute")))
P("hand_built_strings=%d" % len(hand))
P("code_rows_not_through_attribution=%d" % len(nonattr))
P("moment_rows=%d" % len(mom_rows))
P("format_entries_seen=%d (%s)" % (len(fmts), " ".join(fmts)))
P("attribution_shape_files=%d" % len(files_using_attr))
for r in hand:
    P("  HAND %s\t%s" % (r["loc"], r["text"][:88]))
P("moment rows:")
for r in mom_rows:
    P("  MOM %s\t%s\tfmt=%s\t%s" % (r["loc"], r["moments"], r["fmt"], r["text"][:70]))

dest = os.environ.get("ORD0398_OUT", os.path.join(TREE, "review"))
os.makedirs(dest, exist_ok=True)
io.open(os.path.join(dest, "ord0398_readout_census_r1.tsv"), "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print("rows_total=%d hand_built=%d code_not_through=%d moments=%d fmt_entries=%d" % (
    len(rows), len(hand), len(nonattr), len(mom_rows), len(fmts)))
