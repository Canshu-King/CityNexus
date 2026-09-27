#!/usr/bin/env python
"""Measure how much of the light/dark colour pairing in design-tokens.css is
checkable by name, and how much still only exists as a diff of two blocks.

This is a measuring instrument, not a gate: it prints the three denominators
ORD-0380 asks for and dumps the raw per-token tables next to them, so a reading
can be re-derived from the artifact instead of trusted.

Block model (this is where a measurement goes wrong, so it is stated):
  LIGHT_SCOPE  a rule whose selector list contains a bare `:root` branch and no
               [data-theme] qualifier -- e.g. `:root {` (line 8) *and*
               `:root, .v8-product-shell {` (line 172). Both write light values.
               A parser that only accepts `:root{` with an empty selector drops
               the compound block, and --cn-nav-bg's light value lives there.
  DARK_SCOPE   a rule qualified with [data-theme="dark"] whose base is :root.
  Cascade      dark wins over light for the same token: `:root[data-theme=dark]`
               is specificity (0,2,0) against (0,1,0) for a bare `:root` branch,
               so source order cannot rescue a later light declaration.
  Within a scope the last declaration wins, which is what makes the compound
  block override line 8 rather than merely coexist with it.

Colour test: a value is a colour when it carries a hex, rgb()/rgba() or
hsl()/hsla() literal. Anything else (px, ms, cubic-bezier, env(), a font stack)
is not a colour and is reported as such rather than guessed at.
"""
import argparse
import json
import re
import sys
from pathlib import Path

DECL_RE = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*(?P<val>[^;{}]+)")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)\s*(?P<fb>,[^)]*)?\)")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(")
COLOR_TEXT_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)")
ALWAYS_PREFIX = "--cn-always-"

# Families whose members are declared theme-neutral by their name alone.
#   --cn-always-*  says it out loud (a colour something else is painted on top of).
#   --cn-tint-*    is the closed alpha ladder: a tier is an ingredient, and the
#                  theme switch happens one level up, at the consumer. Evidence
#                  in this very file -- --cn-hairline picks black-08 in light and
#                  white-10 in dark while neither tier is ever re-themed.
# Anything else that does not flip is unaccounted, not neutral.
INVARIANT_FAMILIES = (ALWAYS_PREFIX, "--cn-tint-")


def strip_comments(text: str) -> str:
    """Blank out /* */ but keep every newline, so line numbers stay true."""
    out, i = [], 0
    while True:
        j = text.find("/*", i)
        if j < 0:
            out.append(text[i:])
            break
        k = text.find("*/", j + 2)
        if k < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        out.append("\n" * text.count("\n", j, k + 2))
        i = k + 2
    return "".join(out)


# A root branch is `:root` with attached qualifiers only -- no descendant or
# child combinator. `:root`, `:root[data-theme="dark"]`, `:root.dark` qualify;
# `:root[data-theme="dark"] .v8-topbar` does not, because a custom property
# written there never reaches the theme root and cannot pair with anything.
ROOT_BRANCH_RE = re.compile(r'^:root(?:\[[^\]]*\])*(?:\.[-\w]+)*(?::[-\w]+)*$')


def classify(selector: str):
    """Return None / 'light' / 'dark' for a rule selector."""
    sel = " ".join(selector.split())
    if not sel:
        return None
    branches = [b.strip() for b in sel.split(",")]
    root_branches = [b for b in branches if ROOT_BRANCH_RE.match(b)]
    if not root_branches:
        return None
    has_dark = any('data-theme="dark"' in b or "data-theme='dark'" in b for b in root_branches)
    has_light = any("data-theme" not in b for b in root_branches)
    if has_dark and has_light:
        # e.g. `:root, :root[data-theme="dark"]` -- one rule that is both themes.
        # Refused rather than guessed: a pairing measurement that had to pick a
        # side here would be silently wrong.
        return None
    if has_dark:
        return "dark"
    return "light"


def parse(text: str, label: str):
    """Every token declaration in a root-level theme scope, in source order."""
    clean = strip_comments(text)
    decls = []          # [{token, scope, raw, line, block}]
    blocks = []         # block inventory, so the splitting is auditable
    pos = 0
    # walk rules by finding each '{' and its matching '}' to keep nesting honest
    while True:
        b = clean.find("{", pos)
        if b < 0:
            break
        depth, i = 1, b + 1
        while i < len(clean) and depth:
            if clean[i] == "{":
                depth += 1
            elif clean[i] == "}":
                depth -= 1
            i += 1
        sel = clean[max(pos, 0):b]
        sel = sel[sel.rfind("}") + 1:] if "}" in sel else sel
        scope = classify(sel)
        body = clean[b + 1:i - 1]
        line0 = clean.count("\n", 0, b) + 1
        n = 0
        pure = " ".join(sel.split()) == ":root"
        if scope:
            for dm in DECL_RE.finditer(body):
                tok, val = dm.group(1), dm.group("val").strip()
                ln = line0 + body.count("\n", 0, dm.start())
                decls.append({"token": tok, "scope": scope, "raw": val,
                              "line": ln, "block_line": line0, "file": label,
                              "pure_root_selector": pure})
                n += 1
        blocks.append({"selector": " ".join(sel.split())[:70], "scope": scope or "refused",
                       "brace_line": line0, "decls_taken": n, "pure_root_selector": pure})
        pos = i
    return decls, blocks


def effective_maps(decls):
    """light/dark maps of (raw, line) honouring the cascade stated above."""
    light, dark = {}, {}
    for d in decls:
        if d["scope"] == "light":
            light[d["token"]] = d          # later light decl wins
        elif d["scope"] == "dark":
            dark[d["token"]] = d
    return light, dark


def raw_for(tok, light, dark, scope):
    """Effective declared value in a scope. Dark falls back to light, which is
    exactly the cascade a token without a pairing rides on."""
    if scope == "dark":
        if tok in dark:
            return dark[tok]["raw"]
        return light.get(tok, {}).get("raw")
    return light.get(tok, {}).get("raw")


def chain(tok, light, dark, scope, seen=None, depth=0):
    """Walk var() down to literal colour. Returns leaves/lits/ok.

    `ok` is False as soon as one branch of the chain leaves the colour world
    (undefined token, or a leaf holding a length/time/ident), so a non-colour
    token is reported as not-a-colour instead of being forced into a bucket.
    A leaf token that writes its own literal counts as a base; a token that only
    forwards var() does not, which is what separates N1's population from N2's.
    """
    seen = seen or set()
    if tok in seen or depth > 12:
        return {"ok": False, "leaves": [], "lits": [], "cycle": True}
    seen = seen | {tok}
    raw = raw_for(tok, light, dark, scope)
    if raw is None:
        return {"ok": False, "leaves": [], "lits": []}
    inline = [x.strip() for x in COLOR_TEXT_RE.findall(raw)]
    inner = [v for v, _ in VAR_RE.findall(raw)]
    if not inner and not inline:
        return {"ok": False, "leaves": [], "lits": []}
    leaves, lits, ok = [], list(inline), True
    if inline:
        leaves.append(tok)
    for v in inner:
        sub = chain(v, light, dark, scope, seen, depth + 1)
        leaves += sub["leaves"]
        lits += sub["lits"]
        ok = ok and sub["ok"]
    return {"ok": ok, "leaves": sorted(set(leaves)), "lits": lits}


def chain_nodes(tok, light, dark, scope, seen=None, depth=0):
    """Every token this one's var() chain passes through, excluding itself.

    A chain can move in dark without any *leaf* being re-themed, because an
    intermediate was re-declared (--v8-line -> --cn-hairline -> tint: the tint
    never changes, --cn-hairline does). Counting only leaves would hide that.
    """
    seen = seen or set()
    if tok in seen or depth > 12:
        return []
    seen = seen | {tok}
    raw = raw_for(tok, light, dark, scope)
    if raw is None:
        return []
    out = []
    for v, _ in VAR_RE.findall(raw):
        out.append(v)
        out += chain_nodes(v, light, dark, scope, seen, depth + 1)
    return sorted(set(out))


def norm(v):
    """Compare colour values ignoring spacing and case only."""
    v = re.sub(r"\s*,\s*", ",", v)
    v = re.sub(r"\s+", " ", v).strip().lower()
    return re.sub(r"^(#[0-9a-f]{3})\1$", r"\1\1", v)


def colour_tuple(lit):
    """Canonical (r,g,b,a) for one literal, or None when it is not parsable.

    Question 3 of ORD-0380 asks whether a dark re-write changes the *colour*,
    which a string compare cannot answer: #ffffff and rgba(255, 255, 255, 1) and
    rgba(255,255,255,1.00) are one colour written three ways. Comparing tuples
    makes 'identical' a colour claim instead of a typographic one.
    """
    s = lit.strip().lower()
    m = re.match(r"^#([0-9a-f]{3,8})$", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "ff"
        if len(h) != 8:
            return None
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(int(h[6:8], 16) / 255, 4))
    m = re.match(r"^rgba?\(([^)]*)\)$", s)
    if m:
        parts = [p.strip() for p in re.split(r"[,/]", m.group(1)) if p.strip()]
        if len(parts) not in (3, 4):
            return None
        try:
            rgb = tuple(int(float(p)) for p in parts[:3])
        except ValueError:
            return None
        a = 1.0
        if len(parts) == 4:
            try:
                a = float(parts[3])
            except ValueError:
                return None
        return (rgb[0], rgb[1], rgb[2], round(a, 4))
    return None


def canonical(lits):
    """Sorted canonical keys, plus the literals that refused to parse."""
    keys, unparsed = [], []
    for x in lits:
        t = colour_tuple(x)
        if t is None:
            unparsed.append(x)
            keys.append("raw:" + norm(x))
        else:
            keys.append("rgb%s" % (t,))
    return sorted(set(keys)), sorted(set(unparsed))


def resolved_key(tok, light, dark, scope):
    """A comparable identity for 'what colour does this token paint', or None.

    A literal that refuses to parse keeps its normalised text as the key and is
    listed in `unparsed_literals`, so an odd colour form shows up as a caveat on
    the reading instead of quietly turning a real pair into 'no change'.
    """
    c = chain(tok, light, dark, scope)
    if not c["ok"] or not c["lits"]:
        return None
    keys, _unparsed = canonical(c["lits"])
    return " | ".join(keys)


def unparsed_literals(tok, light, dark):
    out = []
    for scope in ("light", "dark"):
        c = chain(tok, light, dark, scope)
        if c["ok"]:
            _k, u = canonical(c["lits"])
            out += u
    return sorted(set(out))


def pairing_status(r, dark):
    """Where a colour token stands on the light/dark axis, as a name-checkable label.

    PAIRED_IN_DARK      the token itself is re-written in the dark block and moves.
    PAIRED_INHERITED    the token never appears in the dark block yet still moves,
                        because a node above it in its var() chain is re-written.
                        This is the population no block diff of either theme block
                        can see, and it is where --v8-* lives.
    NEUTRAL_BY_NAME     it does not move and its name declares why (invariant family).
    DEAD_PAIR           it is re-written in dark and the rewrite changes nothing.
    DARK_ORPHAN         the dark block writes a token light never declared.
    UNACCOUNTED         it does not move and nothing says it is meant not to.
    """
    if not r["light_declared"]:
        return "DARK_ORPHAN" if r["dark_declared"] else "NOT_COLOUR"
    if r["colour_moves_light_to_dark"]:
        return "PAIRED_IN_DARK" if r["dark_declared"] else "PAIRED_INHERITED"
    if r["dark_declared"]:
        return "DEAD_PAIR"
    leaves = r["var_bases"] or [r["token"]]
    if all(any(l.startswith(f) for f in INVARIANT_FAMILIES) for l in leaves):
        return "NEUTRAL_BY_NAME"
    return "UNACCOUNTED"


def measure(text: str, label: str):
    decls, blocks = parse(text, label)
    light, dark = effective_maps(decls)

    rows = []
    for tok in sorted(set(light) | set(dark)):
        lraw = light[tok]["raw"] if tok in light else None
        draw = dark[tok]["raw"] if tok in dark else None
        lline = light[tok]["line"] if tok in light else None
        dline = dark[tok]["line"] if tok in dark else None
        cl = chain(tok, light, dark, "light")
        cd = chain(tok, light, dark, "dark")
        writes_literal = bool(lraw and COLOR_RE.search(lraw))
        # bases only count for a token that forwards through var(); if it writes
        # its own literal the "base" is itself and N1 already owns it.
        bases = [b for b in cl["leaves"] if b != tok] if (lraw and VAR_RE.search(lraw)) else []
        swapped = [b for b in bases if b in dark]
        nodes = chain_nodes(tok, light, dark, "light") if (lraw and VAR_RE.search(lraw)) else []
        nodes_swapped = [n for n in nodes if n in dark and n != tok]
        l_key = resolved_key(tok, light, dark, "light")
        d_key = resolved_key(tok, light, dark, "dark")
        rows.append({
            "token": tok,
            "light_declared": lraw is not None,
            "light_raw": lraw, "light_line": lline,
            "light_scope_pure_root": bool(light.get(tok, {}).get("pure_root_selector")),
            "dark_declared": draw is not None,
            "dark_raw": draw, "dark_line": dline,
            "light_writes_literal": writes_literal,
            "is_colour": bool(cl["ok"] and cl["lits"]),
            "light_is_literal_colour": writes_literal and cl["ok"] and bool(cl["lits"]),
            "light_is_var_colour": (not writes_literal) and cl["ok"] and bool(cl["lits"]),
            "light_non_colour": (not writes_literal) and not cl["ok"],
            "resolves_light": l_key,
            "resolves_dark": d_key,
            "resolvable": cl["ok"],
            "colour_moves_light_to_dark": bool(l_key and d_key and l_key != d_key),
            "var_bases": bases,
            "var_bases_swapped_in_dark": swapped,
            "var_chain_nodes": nodes,
            "var_chain_nodes_swapped_in_dark": nodes_swapped,
            "unparsed_literals": unparsed_literals(tok, light, dark),
            "named_always": tok.startswith(ALWAYS_PREFIX),
        })

    for r in rows:
        r["pairing_status"] = pairing_status(r, dark) if r["is_colour"] else "NOT_COLOUR"
    by_status = {}
    for r in rows:
        by_status.setdefault(r["pairing_status"], []).append(r["token"])
    colours = [r for r in rows if r["is_colour"]]
    hidden = [r for r in colours if not r["light_scope_pure_root"]]

    lit = [r for r in rows if r["light_is_literal_colour"]]
    lit_paired = [r for r in lit if r["dark_declared"]]
    lit_unpaired = [r for r in lit if not r["dark_declared"]]
    lit_unpaired_constant = [r for r in lit_unpaired if r["named_always"]]
    indirect = [r for r in rows if r["light_is_var_colour"]]
    all_bases = sorted({b for r in indirect for b in r["var_bases"]})
    swapped_bases = sorted({b for r in indirect for b in r["var_bases_swapped_in_dark"]})
    moved = [r for r in indirect if r["colour_moves_light_to_dark"]]
    same_raw = [r for r in rows if r["dark_declared"] and r["light_raw"] is not None
                and norm(r["light_raw"]) == norm(r["dark_raw"])]
    same_resolved = [r for r in rows if r["dark_declared"] and r["light_raw"] is not None
                     and r["resolves_light"] and r["resolves_light"] == r["resolves_dark"]]
    differ_but_equal = [r for r in same_resolved if r not in same_raw]
    dark_only = [r for r in rows if r["dark_declared"] and not r["light_declared"]]
    non_colour = [r for r in rows if r["light_non_colour"]]
    unresolvable_colour = [r for r in rows if r["dark_declared"] and not r["resolves_dark"]]

    summary = {
        "file": label,
        "blocks": blocks,
        "n1_light_literal_colour_tokens": len(lit),
        "n1_redefined_in_dark": len(lit_paired),
        "n1_not_redefined_in_dark": len(lit_unpaired),
        "n1_not_redefined_and_not_always": [r["token"] for r in lit_unpaired if not r["named_always"]],
        "n1_not_redefined_named_always": [r["token"] for r in lit_unpaired_constant],
        "n1_redefined_rows": [_pair_row(r) for r in lit_paired],
        "n1_not_redefined_rows": [_pair_row(r) for r in lit_unpaired],
        "n2_var_dependent_colour_tokens": len(indirect),
        "n2_distinct_base_colour_tokens": len(all_bases),
        "n2_base_colour_token_list": all_bases,
        "n2_base_tokens_swapped_in_dark": len(swapped_bases),
        "n2_base_tokens_swapped_list": swapped_bases,
        "n2_var_tokens_whose_computed_colour_moves": len(moved),
        "n2_indirect_rows": [_pair_row(r) for r in indirect],
        "n3_dark_redefined_raw_identical": [r["token"] for r in same_raw],
        "n3_dark_redefined_resolved_identical": [r["token"] for r in same_resolved],
        "n3_resolved_identical_written_differently": [r["token"] for r in differ_but_equal],
        "pairing_status_counts": {k: len(v) for k, v in sorted(by_status.items())},
        "pairing_status_lists": {k: v for k, v in sorted(by_status.items())},
        "pairing_status_rows": {k: [_pair_row(r) for r in rows if r["pairing_status"] == k]
                                for k in sorted(by_status)},
        "n_total_colour_tokens": len(colours),
        "n_unparsed_literal_forms": sorted({x for r in colours for x in r["unparsed_literals"]}),
        "n_intermediate_nodes_swapped_in_dark": {
            r["token"]: [n for n in r["var_chain_nodes_swapped_in_dark"]]
            for r in indirect if r["var_chain_nodes_swapped_in_dark"]},
        "visibility_derived_by_a_non_pure_root_block": sorted(
            r["token"] for r in colours if not r["light_scope_pure_root"]),
        "visibility_count_derived_by_a_non_pure_root_block": len(hidden),
        "extra_dark_only_tokens": [r["token"] for r in dark_only],
        "extra_non_colour_tokens_in_theme_scopes": [r["token"] for r in non_colour],
        "extra_unresolvable_colour_chains": [r["token"] for r in unresolvable_colour],
        "rows": rows,
    }
    return summary


def _pair_row(r):
    return {k: r[k] for k in ("token", "light_line", "light_raw", "dark_line", "dark_raw",
                              "resolves_light", "resolves_dark", "colour_moves_light_to_dark",
                              "var_bases", "var_bases_swapped_in_dark", "named_always",
                              "dark_declared")}


def print_report(s):
    print(f"== blocks parsed in {s['file']}")
    taken = 0
    for b in s["blocks"]:
        if b["scope"] in ("light", "dark"):
            print(f"   line {b['brace_line']:5d}  {b['scope']:6s} pure-root={str(b['pure_root_selector']):5s}"
                  f" decls={b['decls_taken']:3d}  {b['selector']}")
            taken += b["decls_taken"]
        else:
            taken += 0
    refused = [b for b in s["blocks"] if b["scope"] not in ("light", "dark")]
    print(f"   {len(s['blocks'])} rules seen, {taken} token declarations taken,"
          f" {len(refused)} rules carry no :root branch (correctly not treated as theme roots)")
    print("\n== N1  light :root writes a literal colour")
    print(f"   literal-colour tokens            : {s['n1_light_literal_colour_tokens']}")
    print(f"   re-declared in the dark block    : {s['n1_redefined_in_dark']}")
    print(f"   NOT re-declared in the dark block: {s['n1_not_redefined_in_dark']}")
    print(f"     of which named --cn-always-*   : {len(s['n1_not_redefined_named_always'])} {s['n1_not_redefined_named_always']}")
    print(f"     of which unnamed (real gap)    : {len(s['n1_not_redefined_and_not_always'])}")
    for t in s["n1_not_redefined_and_not_always"]:
        print(f"         {t}")
    print("\n== N2  colour reached only through var()")
    print(f"   var-dependent colour tokens      : {s['n2_var_dependent_colour_tokens']}")
    print(f"   distinct base colour tokens      : {s['n2_distinct_base_colour_tokens']}")
    print(f"   base tokens swapped in dark      : {s['n2_base_tokens_swapped_in_dark']} {s['n2_base_tokens_swapped_list']}")
    print(f"   var tokens whose colour moves    : {s['n2_var_tokens_whose_computed_colour_moves']}")
    print("\n== N3  re-declared in dark, value identical to light")
    print(f"   raw-identical                    : {len(s['n3_dark_redefined_raw_identical'])} {s['n3_dark_redefined_raw_identical']}")
    print(f"   resolved-identical               : {len(s['n3_dark_redefined_resolved_identical'])} {s['n3_dark_redefined_resolved_identical']}")
    print(f"   written differently, equal value : {len(s['n3_resolved_identical_written_differently'])} {s['n3_resolved_identical_written_differently']}")
    print("\n== pairing status (name-checkable classification of every colour token)")
    print(f"   colour tokens in root theme scopes : {s['n_total_colour_tokens']}")
    for k, v in sorted(s["pairing_status_counts"].items()):
        if k == "NOT_COLOUR":
            continue
        print(f"   {k:18s} : {v:3d}  {' '.join(s['pairing_status_lists'][k])}")
    pure_gap = s["visibility_count_derived_by_a_non_pure_root_block"]
    print(f"   light value written by a NON-bare ':root' block (invisible to a diff of"
          f" only the bare block): {pure_gap}")
    print("     " + " ".join(s["visibility_derived_by_a_non_pure_root_block"]))
    print("\n== N2 var-chain nodes re-written in dark (a chain can move with no leaf swapping)")
    for tok, nodes in sorted(s["n_intermediate_nodes_swapped_in_dark"].items()):
        print(f"   {tok:18s} <- {' '.join(nodes)}")
    print("\n== extras (measured, no verdict attached)")
    print(f"   dark-only tokens                 : {s['extra_dark_only_tokens']}")
    print(f"   non-colour tokens in scope       : {len(s['extra_non_colour_tokens_in_theme_scopes'])}")
    print(f"   unresolvable colour chains       : {s['extra_unresolvable_colour_chains']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--json", help="write the raw tables here")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    text = Path(a.tokens).read_text(encoding="utf-8")
    s = measure(text, Path(a.tokens).name)
    if not a.quiet:
        print_report(s)
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(s, indent=2, ensure_ascii=False, sort_keys=True),
                                 encoding="utf-8", newline="\n")
        print(f"json written: {a.json} ({Path(a.json).stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
