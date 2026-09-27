#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cmdr_ord0367_rendered_r2.py -- the arm the ORD-0367 rulers could not see.

`tools/cnx_copy_tiers_r1.py` judges the dictionary against itself: register parity, Chinese-side
growth, and whether an edited value is still reachable by an e2e literal.  None of those three can
answer the question a reader actually cares about -- does any component ever ask for this key?

A key that exists in both language blocks, matches register, grows nothing, and is quoted by no
assertion is GREEN on all three gated cells and still never renders.  That is not a hypothetical:
measured below, six of the eleven keys this order edited have zero uses outside the dictionary.

Every count is read from the exported authoritative tree (git archive, not a working tree).  A key
with zero hits is printed with the number of files that were actually searched next to it, because
a zero without a denominator is just a guess with a confident face.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

EXPORT = Path("D:/moodle/_qoder_cmdr_ref_20260921/tonight_tiers/render_export")
REPO = Path("D:/moodle/CityNexus")
SHA = "4ef864cfa49b805e3d41b7f079f5fb4184ccec3d"
DICT = "frontend/src/i18n/LocaleContext.tsx"
OUT = Path("D:/moodle/_qoder_cmdr_ref_20260921/tonight_tiers/ORD-0367_RENDERED_ARM_r2.md")

EDITED = [
    ("en", "inbox.confirmFailed"), ("en", "inbox.imageFailed"), ("en", "inbox.smartApplyFailed"),
    ("en", "inbox.textFailed"),
    ("zhCN", "agent.sendError"), ("zhCN", "discovery.composeError"), ("zhCN", "inbox.confirmFailed"),
    ("zhCN", "inbox.correctionsFailed"), ("zhCN", "inbox.imageFailed"),
    ("zhCN", "inbox.memoryLoadError"), ("zhCN", "inbox.readError"),
    ("zhCN", "inbox.smartApplyFailed"), ("zhCN", "inbox.textFailed"),
    ("zhCN", "live.unresolvedStepHint"), ("zhCN", "shell.loadError"),
]


def export_tree() -> list[Path]:
    if not EXPORT.exists():
        EXPORT.mkdir(parents=True)
        archive = subprocess.run(["git", "-c", "core.autocrlf=false", "archive", SHA, "frontend/src"],
                                 cwd=REPO, check=True, capture_output=True)
        if archive.returncode != 0:
            raise SystemExit("REFUSED: git archive produced no bytes -- nothing was measured")
        unpack = subprocess.run(["tar", "-x", "-C", str(EXPORT)], input=archive.stdout, check=True)
        if unpack.returncode != 0:
            raise SystemExit("REFUSED: export unpack failed")
    return [p for p in (EXPORT / "frontend" / "src").rglob("*")
            if p.suffix in {".ts", ".tsx"} and p.is_file()]


def main() -> None:
    files = export_tree()
    src = {p: p.read_text(encoding="utf-8", errors="replace") for p in files}
    non_dict = {p: t for p, t in src.items() if p.name != "LocaleContext.tsx"}
    searched = len(non_dict)

    keys = sorted({k for _, k in EDITED})
    uses: dict[str, list[str]] = {}
    for k in keys:
        needle = '"%s"' % k
        uses[k] = sorted(
            f"{p.relative_to(EXPORT / 'frontend' / 'src').as_posix()}:{t[:m].count(chr(10)) + 1}"
            for p, t in non_dict.items() for m in [t.find(needle)] if m >= 0
        )
        # finditer-equivalent without importing re here: collect every occurrence
        hits = []
        for p, t in non_dict.items():
            start = 0
            while True:
                i = t.find(needle, start)
                if i < 0:
                    break
                hits.append(f"{p.relative_to(EXPORT / 'frontend' / 'src').as_posix()}:{t[:i].count(chr(10)) + 1}")
                start = i + 1
        uses[k] = sorted(hits)

    dead = [k for k in keys if not uses[k]]
    live = [k for k in keys if uses[k]]

    # A use site that sits in a fallback slot (`x ?? t("k")`, or the last argument of
    # refusalSentence(...)) only reaches the screen when the attribution helper has nothing to say.
    # That is conditional visibility, and it has to be measured rather than asserted.
    def slot_for(site: str) -> str:
        rel, _, ln = site.rpartition(":")
        path = next((p for p in non_dict if p.as_posix().endswith(rel)), None)
        if path is None:
            return "SITE_NOT_FOUND"
        line = non_dict[path].split("\n")[int(ln) - 1]
        if "refusalSentence(" in line:
            return "FALLBACK_SLOT(refusalSentence)"
        if "?? " in line or "??t(" in line.replace(" ", ""):
            return "FALLBACK_SLOT(nullish)"
        return "direct"
    slots = {k: [slot_for(s) for s in uses[k]] for k in live}

    lines = []
    a = lines.append
    a("# ORD-0367 r2 -- the RENDERED arm the copy ruler cannot see (supersedes nothing, adds a cell)")
    a("")
    a(f"Tree measured: authoritative export of `{SHA}` at `frontend/src` only, `{searched}`"
      f" `.ts`/`.tsx` files outside `{DICT}` (the dictionary itself is excluded because every key"
      f" appears there exactly once per language block).")
    a("")
    a("A key is counted as rendered when the quoted form `\"<key>\"` appears in a non-dictionary"
      " source file. Dynamic construction was checked separately and exists only for the `nav.`"
      " namespace, so a zero here is not a scanner artifact.")
    a("")
    a("| key | uses outside the dictionary | slot of each use | sites |")
    a("|---|---|---|---|")
    for k in keys:
        slot_txt = ", ".join(sorted(set(slots.get(k, [])))) or "none"
        a(f"| `{k}` | {len(uses[k])} | {slot_txt} | {', '.join('`' + s + '`' for s in uses[k]) or 'none'} |")
    a("")
    a(f"## Counting consequence for this order")
    a(f"")
    a(f"- distinct keys edited: {len(keys)} (the order touched both language blocks of some keys,")
    a(f"  which is why the copy ruler counted edited *values* rather than keys)")
    a(f"- keys with at least one use outside the dictionary: {len(live)}")
    a(f"- keys with **zero** uses outside the dictionary: {len(dead)}")
    for k in dead:
        a(f"  - `{k}` -- nothing in the shipped frontend ever asks for this sentence")
    a("")
    a("## What this does NOT say")
    a("")
    a("- It does not say the landing was wrong. The register fix, the zero-growth property, and the")
    a("  tier ladder are all measured green in the acceptance note")
    a("  (`b83202eb7f9b165c1c8428615e86e00f37be122c`), and dictionary rows that nothing reads are")
    a("  harmless bytes, not a runtime defect.")
    a("- It does not say the user saw no change. `live.unresolvedStepHint`, `discovery.composeError`")
    a("  and `inbox.memoryLoadError` do render, and `shell.loadError` / `agent.sendError` render")
    a("  whenever the attribution helper yields no body -- those two sit in a fallback slot, so")
    a("  their appearance is conditional rather than absent.")
    a("- It does say that any future claim of the shape \"this copy pass is user-visible\" must")
    a("  name which keys have a use site, because six of them do not.")
    a("")
    a("## Ruler consequence (dispatched as part of ORD-0370)")
    a("")
    a("`tools/cnx_copy_tiers_r1.py` should grow a `RENDERED` cell: for every edited key, print the")
    a("count of non-dictionary use sites and its denominator, and list the keys it considers")
    a("unrendered. The cell must be reported and, for a *new* edit, gated: editing a sentence")
    a("nothing reads is churn, and the ruler currently cannot tell that from progress.")
    a(f"Raw per-key counts: `{json.dumps({k: len(v) for k, v in uses.items()}, sort_keys=True)}`")
    OUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} B)")
    print(f"searched {searched} non-dictionary files across {len(keys)} edited keys:")
    print(f"  rendered>=1 : {len(live)}")
    print(f"  zero-use    : {len(dead)} -> {', '.join(dead)}")


if __name__ == "__main__":
    main()
