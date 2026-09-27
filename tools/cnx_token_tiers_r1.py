#!/usr/bin/env python
"""Tier and constant gate for frontend/src/design-tokens.css.

Two structural claims are enforced, both of them cheap to check and expensive
to lose:

  PARITY   introducing tiers must not move a single computed colour. Every
           token that existed in the baseline still resolves to the same value.
  TIERS    the two theme blocks carry no inline rgba() any more; every alpha
           comes from the closed --cn-tint-* ladder.
  CONSTANT a token that resolves identically in light and dark must be named
           --cn-always-*, and an --cn-always-* must never be re-declared in
           the dark block. Either direction of the mistake reads as red.

Every verdict is derived from measured lines; nothing here prints a literal
"PASS". --mutant proves the ruler can see: it injects four defects and each
one must be caught, or the ruler itself is the defect.
"""
import argparse
import re
import sys
from pathlib import Path

BLOCK_RE = re.compile(r"^[ \t]*:root([^\{]*)\{", re.M)
DECL_RE = re.compile(r"^\s*(--[A-Za-z0-9-]+)\s*:\s*([^;]+);")
VAR_RE = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)\s*(?:,[^)]*)?\)")


def theme_blocks(text: str, name: str):
    """Return {'light': {tok:(value,line)}, 'dark': {...}} for :root blocks."""
    out = {"light": {}, "dark": {}}
    for m in BLOCK_RE.finditer(text):
        selector = (m.group(1) or "").strip()
        is_dark = 'data-theme="dark"' in selector
        if selector and not is_dark:
            continue  # :root.foo / :root, .bar are not the theme roots
        start = m.end()
        depth = 1
        i = start
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        line0 = text.count("\n", 0, start) + 1
        for off, raw in enumerate(text[start:i].split("\n")):
            d = DECL_RE.match(raw)
            if d:
                key = "dark" if is_dark else "light"
                out[key].setdefault(d.group(1), (d.group(2).strip(), line0 + off))
    if not out["light"]:
        raise SystemExit(f"FATAL no :root block parsed in {name}")
    return out


def resolve(tok, maps, scope, seen=None):
    """Expand var() chains down to a literal, light as the fallback scope."""
    seen = seen or set()
    if tok in seen:
        return None
    seen = seen | {tok}
    val = None
    for s in (scope, "light"):
        if tok in maps[s]:
            val = maps[s][tok][0]
            break
    if val is None:
        return None
    for inner in set(VAR_RE.findall(val)):
        sub = resolve(inner, maps, scope, seen)
        if sub is None:
            return None
        val = re.sub(r"var\(\s*" + re.escape(inner) + r"\s*(?:,[^)]*)?\)", sub, val)
    return None if VAR_RE.search(val) else val.strip()


def norm(v):
    """Compare colour values ignoring spacing and case only."""
    v = re.sub(r"\s*,\s*", ",", v)
    v = re.sub(r"\s+", " ", v).strip().lower()
    v = v.replace("rgba(", "rgb(").replace("rgb(", "rgb(")
    return re.sub(r"^(#[0-9a-f]{3})\1$", r"\1\1", v)


def audit(text, base_text, styles_text, path_label):
    maps = theme_blocks(text, path_label)
    findings = []

    # ---- PARITY: baseline tokens must resolve unchanged -------------------
    # Each (token, scope) pair is checked on its own. Collapsing this into one
    # dict keyed by token lets the dark entry overwrite the light one, which
    # silently hides any movement of a token declared in both blocks -- canvas,
    # surface and ink are exactly that case. The M1 mutant exists to prove the
    # two scopes stay independent.
    parity_checked = 0
    if base_text:
        bmaps = theme_blocks(base_text, "baseline")
        checks = [(t, "light") for t in bmaps["light"]] + [(t, "dark") for t in bmaps["dark"]]
        moved = []
        for tok, scope in checks:
            before = resolve(tok, bmaps, scope)
            if before is None:
                continue
            parity_checked += 1
            after = resolve(tok, maps, scope)
            if after is None or norm(before) != norm(after):
                moved.append(f"{tok}@{scope}: {before} -> {after}")
        findings.append((
            "PARITY",
            f"{parity_checked} (token,scope) baseline readings re-resolved",
            not moved,
            "; ".join(moved[:5]) or "none moved",
        ))

    # ---- TIERS: no inline alpha inside the two theme blocks ---------------
    # The ladder itself is the one place a literal alpha is allowed to exist,
    # so --cn-tint-* declarations are exempt. Every other token must reach an
    # alpha through var(); a mixed value (part var(), part literal rgba) is a
    # violation on purpose, because it lets a ninth tier slip in unnamed.
    inline = []
    for scope in ("light", "dark"):
        for tok, (val, line) in maps[scope].items():
            if tok.startswith("--cn-tint-"):
                continue
            if re.search(r"rgba?\(", val):
                inline.append(f"{path_label}:{line} {scope}:{tok} = {val}")
    findings.append((
        "TIERS",
        f"inline rgba() remaining inside :root theme blocks: {len(inline)}",
        not inline,
        " | ".join(inline[:4]) or "none",
    ))

    # ---- TIER LADDER: every tint token must be consumed -------------------
    tints = {t for t in maps["light"] if t.startswith("--cn-tint-")}
    body = text + ("\n" + styles_text if styles_text else "")
    unused = sorted(t for t in tints if body.count(t) < 2)
    findings.append((
        "LADDER_USED",
        f"tint tiers defined {len(tints)}, unreferenced {len(unused)}",
        not unused,
        " ".join(unused[:5]) or "every tier has at least one consumer",
    ))

    # ---- CONSTANT: two directions ----------------------------------------
    both = set(maps["light"]) & set(maps["dark"])
    same_unnamed = [
        t for t in sorted(both)
        if norm(maps["light"][t][0]) == norm(maps["dark"][t][0])
        and not t.startswith("--cn-always-")
    ]
    always_in_dark = [t for t in sorted(maps["dark"]) if t.startswith("--cn-always-")]
    findings.append((
        "CONSTANT_DUP",
        f"tokens re-declared identically in the dark block: {len(same_unnamed)}",
        not same_unnamed,
        " ".join(same_unnamed[:5]) or "none",
    ))
    findings.append((
        "CONSTANT_IN_DARK",
        f"--cn-always-* present inside :root[data-theme=dark]: {len(always_in_dark)}",
        not always_in_dark,
        " ".join(always_in_dark[:5]) or "none",
    ))
    return findings


def mutants(workdir: Path, src: str, base: str, styles: str):
    """Inject defects; each must be caught by a named check."""
    cases = {
        "M1_value_moved": lambda s: s.replace("--cn-canvas: #f5f5f7;", "--cn-canvas: #f5f5f6;", 1),
        "M2_inline_alpha": lambda s: s.replace(
            "--cn-hairline: var(--cn-tint-black-08);",
            "--cn-hairline: rgba(0, 0, 0, 0.08);", 1),
        "M3_always_in_dark": lambda s: s.replace(
            '  :root[data-theme="dark"] {',
            '  :root[data-theme="dark"] {\n    --cn-always-accent-solid: #0a66ff;', 1),
        "M4_identical_not_always": lambda s: s.replace(
            '  :root[data-theme="dark"] {',
            '  :root[data-theme="dark"] {\n    --cn-danger: #d70015;', 1),
    }
    out = []
    for label, fn in cases.items():
        mutated = fn(src)
        if mutated == src:
            out.append((label, "mutation did not apply", False))
            continue
        p = workdir / f"{label}.css"
        p.write_text(mutated, encoding="utf-8", newline="\n")
        try:
            res = audit(mutated, base, styles, str(p))
            caught = sorted(n for n, _, ok, _ in res if not ok)
        finally:
            p.unlink(missing_ok=True)
        out.append((label, "caught by " + ",".join(caught) if caught else "NOT CAUGHT", bool(caught)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--styles")
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()

    src = Path(a.tokens).read_text(encoding="utf-8")
    base = Path(a.baseline).read_text(encoding="utf-8") if a.baseline else None
    styles = Path(a.styles).read_text(encoding="utf-8") if a.styles else None
    label = Path(a.tokens).name

    rc = 0
    print(f"== cnx_token_tiers_r1  tokens={a.tokens}"
          f" baseline={a.baseline or 'none'} styles={'yes' if styles else 'none'}")
    for name, measure, ok, detail in audit(src, base, styles, label):
        print(f"  [{'MET' if ok else 'VIOLATION'}] {name:18s} {measure}")
        print(f"          detail: {detail}")
        rc |= 0 if ok else 1

    if a.mutant:
        print("  -- ruler self-test: injected defects must all be caught --")
        workdir = Path(a.tokens).parent
        for label_m, detail, ok in mutants(workdir, src, base, styles):
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label_m:26s} {detail}")
            rc |= 0 if ok else 1

    print(f"exit={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
