"""Generate the color-token inventory by reading the code -- no hand copying.

    TIP=<40 hex> python token_inventory_r1.py [out.json]

This is the first cell of the building the commander named for lane 2d2d7428: every colour that can be
painted on screen must be able to answer "what is it called, where does it come from, what is it in each
of the two themes". The drawings are explicit that the list is generated, not transcribed, and that any
colour we miss is a hole a future change will drift into -- so this script reads:

  1. every `--token: value` declaration, per file, with the line it sits on;
  2. which of the three families it belongs to: the light block (`:root`), the dark block
     (`:root[data-theme="dark"]`), or the always family (`--cn-always-*`);
  3. every reference site (`var(--token)`) per file with its line;
  4. the holes the drawings name:
       defined but never referenced  -> a token nobody paints (either dead weight or a missing call site)
       referenced but never defined -> a hole the browser resolves to nothing (the "absent" that once
                                        masqueraded as a value in another lane's log)
       equal in both themes but not named `always` -> the declaration the token file itself calls a
                                        "missed declaration" (its own gate reads that as red)

Values are kept as written; resolution (`var()` chains) and measured contrast are the next cell, and
this script deliberately does not pretend to answer them.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
SRC = WT / "frontend" / "src"
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0522_20261001")
OUT = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "token_inventory_r1.json")

tip = subprocess.run(["git", "-C", str(WT), "rev-parse", "HEAD"], capture_output=True,
                     text=True).stdout.strip()
if not re.fullmatch(r"[0-9a-f]{40}", tip):
    raise SystemExit("REFUSE: HEAD is not a 40-hex: {!r}".format(tip))
expected = os.environ.get("TIP", "")
if expected and tip != expected:
    raise SystemExit("REFUSE: checkout is {} but the caller named {}".format(tip, expected))

DECL = re.compile(r"(--[a-zA-Z0-9-]+)\s*:\s*([^;{}]+)")
REF = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
COMMENT = re.compile(r"/\*.*?\*/", re.S)
DARK = re.compile(r':root\s*\[\s*data-theme\s*=\s*["\']dark["\']\s*\]')

def block_ranges(text):
    """Byte ranges of the bodies of blocks whose selector names the dark scheme.

    Brace matching, not a linear boundary: design-tokens.css opens a second top-level `:root { }` below the
    dark block, and treating "everything after the dark selector" as dark mislabelled the nav geometry
    (touch floor, item height, safe-area) as dark-only when those are theme-independent.
    """
    ranges = []
    depth = 0
    start = None
    sel_start = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth == 1 and start is not None and DARK.search(text[sel_start:start]):
                ranges.append((start + 1, i))
            depth = max(0, depth - 1)
            if depth == 0:
                start = None
        elif ch == ";" and depth == 0:
            sel_start = i + 1
        if ch == "}" and depth == 0:
            # The selector of the NEXT block starts after this one ends. Without this reset the selector
            # window still contained the dark block's text, so every later top-level block inherited it.
            sel_start = i + 1
    return ranges


tokens = {}
references = {}
css_files = 0
declarations = 0

for path in sorted(SRC.rglob("*.css")):
    rel = path.relative_to(WT).as_posix()
    css_files += 1
    raw = path.read_text(encoding="utf-8", errors="replace")
    # Comments are blanked for PARSING only. Line numbers must be counted on the ORIGINAL text: stripping
    # comments shifts every offset after them, which silently moved the first version's call sites by
    # whole rules -- a generator that misreports where a token comes from is worse than no generator.
    text = COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), raw)
    # Which declarations sit inside a dark-scheme block? NOT "everything after the first dark selector":
    # design-tokens.css opens a second top-level :root { } (nav geometry, touch floor) below the dark
    # block, and a linear boundary called all of it dark. Brace matching is the only honest way -- walk
    # each selector block and ask whether ITS selector names the dark scheme.
    dark_ranges = block_ranges(text)
    for d in DECL.finditer(text):
        name, value = d.group(1), " ".join(d.group(2).split())
        line = text.count("\n", 0, d.start()) + 1
        rec = tokens.setdefault(name, {"name": name, "light": None, "dark": None, "always": None,
                                       "decl_sites": [], "refs": []})
        in_dark = any(a <= d.start() < b for a, b in dark_ranges)
        if name.startswith("--cn-always-"):
            rec["always"] = {"value": value, "file": rel, "line": line}
            # an always token must never be re-declared inside the dark block: the token file calls that
            # a contradiction and its own gate reads it red.
            if in_dark:
                rec["decl_sites"].append({"file": rel, "line": line, "value": value, "block": "dark",
                                          "contradiction": True})
            else:
                rec["decl_sites"].append({"file": rel, "line": line, "value": value, "block": "always"})
            continue
        if in_dark:
            rec["dark"] = {"value": value, "file": rel, "line": line}
            rec["decl_sites"].append({"file": rel, "line": line, "value": value, "block": "dark"})
        else:
            if rec["light"] is None:
                rec["light"] = {"value": value, "file": rel, "line": line}
            rec["decl_sites"].append({"file": rel, "line": line, "value": value, "block": "light"})
        declarations += 1
    for r in REF.finditer(text):
        name = r.group(1)
        line = text.count("\n", 0, r.start()) + 1
        # `var(--x, fallback)` is a second, unnamed colour source written inline at the call site: the
        # token is absent AND the value is spelled out here, so nobody can answer "what is this colour,
        # where does it come from" from the inventory alone. These are the holes that drift silently.
        tail = text[r.end():r.end() + 160]
        fb = None
        if tail.lstrip().startswith(","):
            depth = 0
            buf = ""
            for ch in tail:
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    if depth == 0:
                        break
                    depth -= 1
                elif ch == ")" and depth == 0:
                    break
                buf += ch
            fb = " ".join(buf.split()).lstrip(",").strip()
        site = {"file": rel, "line": line, "fallback": fb}
        references.setdefault(name, []).append(site)
        if name in tokens:
            tokens[name]["refs"].append(site)

for name, sites in references.items():
    tokens.setdefault(name, {"name": name, "light": None, "dark": None, "always": None,
                             "decl_sites": [], "refs": []})
    tokens[name]["refs"] = sites

rows = []
holes = {"defined_never_referenced": [], "referenced_never_defined_but_locally_defaulted": [],
         "referenced_never_defined_no_fallback": [],
         "defined_but_shadowed_by_inline_fallback": [],
         "equal_in_both_themes_not_always": [], "always_redeclared_in_dark": [],
         "defined_in_dark_only": []}
for name, rec in sorted(tokens.items()):
    light = (rec["light"] or {}).get("value")
    dark = (rec["dark"] or {}).get("value")
    always = (rec["always"] or {}).get("value")
    nref = len(rec["refs"])
    rows.append({"name": name, "light": light, "dark": dark, "always": always,
                 "light_site": [rec["light"]["file"], rec["light"]["line"]] if rec["light"] else None,
                 "dark_site": [rec["dark"]["file"], rec["dark"]["line"]] if rec["dark"] else None,
                 "n_reference_sites": nref,
                 "reference_files": sorted({s["file"] for s in rec["refs"]}),
                 # the call sites, capped per file so the inventory stays readable: a token named in 90
                 # places lists its first three, and `reference_files` carries the rest of the shape.
                 "reference_sites": [[s["file"], s["line"]] for s in rec["refs"][:12]]})
    if rec["decl_sites"] and nref == 0:
        holes["defined_never_referenced"].append(name)
    if not rec["decl_sites"] and nref > 0:
        if all(s.get("fallback") for s in rec["refs"]):
            holes["referenced_never_defined_but_locally_defaulted"].append(name)
        else:
            holes["referenced_never_defined_no_fallback"].append(name)
    # A fallback on a token that IS defined is dead weight, and it is the dangerous kind: the token can be
    # deleted or renamed later, the fallback silently takes over, and the screen keeps rendering a colour
    # that no inventory row names. That is a hole waiting for the next change -- exactly what the drawings
    # say a missed colour is.
    if rec["decl_sites"] and any(s.get("fallback") for s in rec["refs"]):
        holes["defined_but_shadowed_by_inline_fallback"].append(name)
    if any(s.get("contradiction") for s in rec["decl_sites"]):
        holes["always_redeclared_in_dark"].append(name)
    if rec["dark"] and not rec["light"] and not rec["always"]:
        holes["defined_in_dark_only"].append(name)
    if light and dark and light == dark and not always:
        holes["equal_in_both_themes_not_always"].append(name)

colorish = [r for r in rows
            if re.search(r"#|rgb|hsl|oklch|color-mix|var\(", r["light"] or r["dark"] or r["always"] or "")]
# Inline fallbacks are colour sources too, and they are invisible to a token-only inventory. Collect them
# as first-class rows so the wall covers every colour that can reach the screen, named or not.
inline = []
for name, sites in references.items():
    for s in sites:
        if s.get("fallback") and re.search(r"#|rgb|hsl|oklch|color\(", s["fallback"]):
            inline.append({"token": name, "fallback": s["fallback"],
                           "file": s["file"], "line": s["line"]})

out = {"tip": tip, "css_files_read": css_files, "declarations": declarations,
       "inline_colour_fallbacks": inline, "n_inline_colour_fallbacks": len(inline),
       "tokens_seen": len(rows), "colour_valued_tokens": len(colorish),
       "tokens": rows, "colour_tokens": colorish,
       "holes": {k: sorted(v) for k, v in holes.items()},
       "hole_counts": {k: len(v) for k, v in holes.items()},
       "note": ("values are as written in the source; var() chains are not resolved and no contrast is "
                "measured here -- those are the next cells of the building, deliberately not faked")}
OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print("尖 {}；读了 {} 枚样式表、{} 条声明，认到 {} 枚令牌（其中带色值 {} 枚）".format(
    tip, css_files, declarations, len(rows), len(colorish)))
for k, v in sorted(out["hole_counts"].items()):
    print("  {}: {} 枚 {}".format(k, v, sorted(holes[k])[:6]))