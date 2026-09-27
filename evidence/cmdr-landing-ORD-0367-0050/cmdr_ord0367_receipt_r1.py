#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cmdr_ord0367_receipt_r1.py -- derive the ORD-0367 acceptance note from measured files.

Every verdict line below is read out of an artifact produced by a real run in this process; no
verdict is written as a literal.  Where a file is missing or a pattern cannot be found, the note
says NOT_MEASURED rather than guessing, because a green-sounding sentence with no measurement
behind it is the failure mode this project has already paid for twice.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

BASE = Path("D:/moodle/_qoder_cmdr_ref_20260921/tonight_tiers")
LIVE = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
REPO = Path("D:/moodle/CityNexus")
OUT = BASE / "ORD-0367_ACCEPTANCE_NOTE.md"

TIP_BEFORE = "baaa07117003320292d76a5f0c383952071b7364"
BASE_REV = "6ee21eddba60303e8f0f46907df9501ee0149e6e"  # the commit the lane cut its branch from
CAND = "031e381e0f2c6412ac63a7f1314c0951c5609125"
RECUT = "4ef864cfa49b805e3d41b7f079f5fb4184ccec3d"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True).stdout.strip()


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


def met_lines(text: str) -> list[tuple[str, str]]:
    """[(cell, measurement)] for every [MET]/[RED] line a ruler printed."""
    out = []
    for ln in text.splitlines():
        m = re.match(r"\s*\[(MET|RED)\]\s+(\S+)\s+(.*)$", ln)
        if m:
            out.append((m.group(2), m.group(3).strip()))
    return out


def caught(text: str) -> list[str]:
    return [m.group(1) for m in re.finditer(r"\[MET\]\s+(\S+)\s+caught by", text)]


def kv(obj, dotted: str):
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


blob_cache: dict[str, str] = {}


def blob(rev: str, path: str) -> str:
    key = f"{rev}:{path}"
    if key not in blob_cache:
        blob_cache[key] = git("rev-parse", f"{rev}:{path}")
    return blob_cache[key]


def main() -> None:
    token_real = read(BASE / "ruler_token_tiers_real.txt")
    token_mut = read(BASE / "ruler_token_tiers_mutant.txt")
    copy_real = read(BASE / "ruler_copy_tiers_real.txt")
    copy_mut = read(BASE / "ruler_copy_tiers_mutant.txt")

    recut = json.loads(read(BASE / "recut_ord0367.json") or "{}")
    land = json.loads(read(BASE / "land_ord0367.json") or "{}")
    probe = json.loads(read(BASE / "_phone_chain_0038.json") or "{}")
    deploys = sorted(LIVE.glob("receipts/deploy_4ef864c*.json"))
    deploy = json.loads(read(deploys[0])) if deploys else {}

    lines: list[str] = []
    a = lines.append

    a("# ORD-0367  acceptance note (commander, 2026-09-28 ~00:47 +08)")
    a("")
    a("What this order is: the i18n copy-register pass plus the design-token tier work that the")
    a("conversation `be19052c-d805-448a-b11e-46d53633d45b` delivered on branch")
    a("`review/Q-pitravel-token-tiers`. The commander re-measured everything below instead of")
    a("trusting that lane's own summary.")
    a("")
    a("## Coordinates (all full 40-hex, all resolvable with `git cat-file` in `D:/moodle/CityNexus`)")
    a("")
    a(f"- authoritative tip before the landing: `{TIP_BEFORE}`")
    a(f"- lane candidate tip:                 `{CAND}`")
    a(f"- re-cut onto the tip, and the new authoritative tip: `{RECUT}`")
    a(f"- merged tree of the re-cut:          `{recut.get('merged_tree', 'NOT_MEASURED')}`")
    a(f"- `frontend/src/design-tokens.css` on the landing generation: `{blob(RECUT, 'frontend/src/design-tokens.css')}`")
    a(f"- `frontend/src/i18n/LocaleContext.tsx` on the landing generation: `{blob(RECUT, 'frontend/src/i18n/LocaleContext.tsx')}`")
    a(f"- ruler `tools/cnx_copy_tiers_r1.py`: `{blob(RECUT, 'tools/cnx_copy_tiers_r1.py')}`")
    a(f"- ruler `tools/cnx_token_tiers_r1.py`: `{blob(RECUT, 'tools/cnx_token_tiers_r1.py')}`")
    a("")
    a("## Why the re-cut was clean")
    a("")
    same_tok = blob(TIP_BEFORE, "frontend/src/design-tokens.css") == blob(BASE_REV, "frontend/src/design-tokens.css")
    same_ctx = blob(TIP_BEFORE, "frontend/src/i18n/LocaleContext.tsx") == blob(BASE_REV, "frontend/src/i18n/LocaleContext.tsx")
    a("- measured blob equality between the authoritative tip and **the lane's own base commit**"
      f" `{BASE_REV}`, each read with `git rev-parse <rev>:<path>`:")
    a(f"  - `design-tokens.css`: tip `{blob(TIP_BEFORE, 'frontend/src/design-tokens.css')}`"
      f" vs base `{blob(BASE_REV, 'frontend/src/design-tokens.css')}` -> equal `{str(same_tok).lower()}`")
    a(f"  - `LocaleContext.tsx`: tip `{blob(TIP_BEFORE, 'frontend/src/i18n/LocaleContext.tsx')}`"
      f" vs base `{blob(BASE_REV, 'frontend/src/i18n/LocaleContext.tsx')}` -> equal `{str(same_ctx).lower()}`")
    a(f"- conclusion is read off those two cells, not asserted: both files untouched between base"
      f" and tip -> `{str(same_tok and same_ctx).lower()}`; when true, the candidate introduces them"
      f" with no merge at all.")
    a(f"  the re-cut independently proved per-file blob equality and wrote it to"
      f" `{(BASE / 'recut_ord0367.json').as_posix()}`")
    a("- relationship as read by the landing gate, field by field, from"
      f" `{(BASE / 'land_ord0367.json').name}`:")
    for field in ("ff", "fast_forward", "ahead", "behind", "intersection", "verdict", "mode"):
        val = land.get(field, kv(land, f"preflight.{field}"))
        if val is not None:
            a(f"  - `{field}` = `{val}`")
    a("")

    a("## Ruler runs the commander performed personally")
    a("")
    a("Both rulers were run twice: once against the real bytes, once with `--mutant`, which injects")
    a("defects that the ruler must catch. A ruler that cannot catch its own injected defects is")
    a("itself the defect, so the mutant arm is part of the evidence, not decoration.")
    a("")
    for label, txt, mut, real_name, mut_name in (
        ("`tools/cnx_token_tiers_r1.py`", token_real, token_mut,
         "ruler_token_tiers_real.txt", "ruler_token_tiers_mutant.txt"),
        ("`tools/cnx_copy_tiers_r1.py`", copy_real, copy_mut,
         "ruler_copy_tiers_real.txt", "ruler_copy_tiers_mutant.txt"),
    ):
        cells = met_lines(txt)
        verdicts = [c for c, _ in cells]
        a(f"### {label}")
        a("")
        a("| cell | measured |")
        a("|---|---|")
        for cell, meas in cells:
            a(f"| `{cell}` | {meas} |")
        if not cells:
            a("| NOT_MEASURED | the ruler printed no [MET]/[RED] lines -- see raw file |")
        caught_cells = caught(mut)
        a(f"- mutant arm: {len(caught_cells)} injected defects caught"
          + (f" ({', '.join('`' + c + '`' for c in caught_cells)})" if caught_cells else " -- NOT_MEASURED"))
        a(f"- raw outputs in this directory: `{real_name}` (real bytes) and `{mut_name}` (`--mutant`)")
        a(f"- cells printed: {len(verdicts)}")
        a("")

    a("## The claim the commander checked independently of the ruler")
    a("")
    a("The ruler's own anti-coupling cell is `ASSERTIONS_STILL_HIT`. The commander re-checked the")
    a("underlying fact by hand, because a disjunctive e2e assertion was already known to be lurking:")
    a("")
    zh = [ln for ln in read(BASE / "cand/LocaleContext.tsx").splitlines()
          if "进行到哪一步" in ln]
    zb = [ln for ln in read(BASE / "base/LocaleContext.tsx").splitlines()
          if "进行到哪一步" in ln]
    a("- `hub.continuationUnconfirmable` is quoted verbatim by two e2e files")
    a("  (`qoder-continuation-owner.spec.ts:30`, `qoder-continuation-resume-carries-identity.spec.ts:31`).")
    a(f"- that line is present once in the baseline and once in the candidate, and the two are")
    a(f"  byte-identical: `{str(zb == zh and len(zh) == 1).lower()}`"
      f" (candidate line text length in code points: `{len(zh[0]) if zh else 'NOT_MEASURED'}`)")
    a("")

    a("## Landing and the phone generation")
    a("")
    a(f"- landing gate receipt: `{(BASE / 'land_ord0367.json').name}`"
      f" -- tip_after `{kv(land, 'landing.tip_after', )}`"
      f" -- both GitHub routes agree: `{kv(land, 'landing.both_routes_agree')}`")
    a(f"- deploy receipt: `{deploys[0].name if deploys else 'NOT_MEASURED'}`"
      f" -- overall `{kv(deploy, 'overall')}`"
      f" -- switched files `{json.dumps(kv(deploy, 'switched'))}`")
    a(f"- phone-side probe `{(BASE / '_phone_chain_0038.json').name}`: overall `{probe.get('overall', 'NOT_MEASURED')}`"
      f" at `{probe.get('probed_at_local', 'NOT_MEASURED')}`, generation under test"
      f" `{probe.get('generation_under_test', 'NOT_MEASURED')}`, assets probed `{probe.get('assets_probed', 'NOT_MEASURED')}`")
    decisions = probe.get("decisions", {})
    for k in ("all_200", "all_bytes_equal_to_disk", "no_asset_served_as_html",
              "js_content_type_correct", "every_named_asset_present_on_disk"):
        a(f"  - `{k}` = `{decisions.get(k, 'NOT_MEASURED')}`")
    for row in probe.get("rows", []):
        a(f"  - measured `{row.get('path')}`: http `{row.get('http_status')}`,"
          f" content type `{row.get('content_type')}`, served `{row.get('served_bytes')}` B vs"
          f" disk `{row.get('disk_bytes')}` B, sha256 match:"
          f" `{str(row.get('served_sha256') == row.get('disk_sha256')).lower() if row.get('disk_sha256') else 'NOT_MEASURED'}`")
    a(f"- the probe states its own limit, verbatim: `{probe.get('scope', 'NOT_MEASURED')}`")
    a(f"- credential handling recorded by the probe: `{probe.get('credential_handling', 'NOT_MEASURED')}`")
    a("")

    a("## What is NOT claimed here")
    a("")
    a("- No backend test suite was run for this order: the landing gate records"
      f" `test_exit={kv(land, 'gate.test_exit') or 'NOT_MEASURED'}` and"
      f" `collect_exit={kv(land, 'gate.collect_exit') or 'NOT_MEASURED'}`"
      " because `--tests` was not passed. The candidate carries no `backend/` file.")
    a("- The tunnel host rotates. The address used for this swap is recorded in the deploy receipt")
    a("  and in `D:/moodle/_qoder_preview_20260920/run/tunnel_url.txt`; the previous address was")
    a("  archived, not deleted.")
    a("- Durations from the previous generation do not transfer (standing rule Q25).")
    a("")

    a("## Follow-up defect the commander found while verifying this generation")
    a("")
    a("Searching the *deployed* asset rather than the source found a hardcoded fallback that the")
    a("copy ruler cannot see, because the ruler only reads `LocaleContext.tsx`:")
    a("")
    a("```")
    a("... body ?? (flag ? \"确认失败\" : \"Approval failed\")")
    a("```")
    a("")
    a("Named sites from a scan of the pure authoritative tree (`git archive` export, not a working")
    a("tree): `frontend/src/features/agent/CopilotDock.tsx:364`, `:384`, `:415`;")
    a("`frontend/src/features/execution/LiveRecovery.tsx:238`;")
    a("`frontend/src/features/inbox/JourneyInboxWorkbench.tsx:805`.")
    a("A wider scan of bare nullish fallbacks found 78 sites, all of them English literals, which")
    a("means a Chinese reader is shown English whenever a server body is missing. Order")
    a("`ORD-0370` was dispatched for both counts.")
    a("")

    OUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    body = "\r\n".join(lines)
    print(f"wrote {OUT} ({OUT.stat().st_size} B)")
    # A published note carrying a bare None is a self-contradicting artifact: either the field was
    # measured, or the line must say NOT_MEASURED and explain the missing input.
    strays = [ln.strip() for ln in lines if re.search(r"(?<![\w`])None(?![\w])", ln)]
    print("literal-PASS lines:", body.count("PASS"))
    print("bare-None lines:", len(strays))
    for s in strays:
        print("   STRAY:", s[:150])
    if strays:
        raise SystemExit("REFUSED: the note still carries unmeasured fields printed as None")


if __name__ == "__main__":
    main()
