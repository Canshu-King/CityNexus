# -*- coding: utf-8 -*-
"""ORD-0408 (value-level data flow) r1 - the BEFORE reading, before any ruler byte changes.

The item as the ledger words it: `enumTokenEvidence` compares *every* uppercase token it can find on a
cell's chain against the contract's closed set, so a token that belongs to some other field sitting in
the same text can drag this cell red.  Narrowing it to "only the literal assigned to that field" needs
value-level data flow.

This script does not narrow anything.  It records, for each shipped-bytes fixture with one knob turned,
and against three contracts:
  - what r7b4 (published) decides,
  - what r8 (my structured-exemption revision) decides,
  - the exact tokens each of them counted, and
  - for every counted token, the source line it was lifted from and what that line does to the field
    (`assigns_to_field` / `compares_the_field` / `other_field` / `not_in_the_assignment`).
That last column is the whole question: a token whose only role is in another field's expression must
not be able to answer for this one, and "must not" is only a claim once you have printed where each
token came from.

Read-only over files that already exist. No ports, no DB, no authoritative line.
"""
import io
import json
import os
import re
import subprocess

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0536"
FX = r"D:\moodle\_qoder_lane_S4_0926\work\ord0408\jia\fx2"
CONTRACTS = {
    "inline_enum_names_the_set": r"D:\moodle\_qoder_lane_S4_0926\work\ord0408\jia\openapi_inline_enum.yaml",
    "block_enum_names_the_set": r"D:\moodle\_qoder_lane_S4_0926\work\ord0408\jia\openapi_block_enum.yaml",
    "enum_owned_by_another_field": r"D:\moodle\_qoder_lane_S4_0926\work\ord0408\jia\openapi_enum_other_field_only.yaml",
}
R7B4 = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\ui_exposure_taint_ast_r7b4.cjs"
R8 = os.path.join(WORK, "ui_exposure_taint_ast_r8.cjs")
ENV = dict(os.environ)
ENV.pop("HTTP_PROXY", None)
ENV.pop("HTTPS_PROXY", None)
FIELD = "reason_code"


def run(ruler, fixture, contract):
    p = subprocess.run(["node", ruler, "--file", fixture, "--contract", contract],
                       capture_output=True, env=ENV, timeout=600)
    out = p.stdout.decode("utf-8", "replace")
    i = out.find("{")
    if i < 0:
        return {"rc": p.returncode, "error": out[:200]}
    doc = json.loads(out[i:])
    cells = doc.get("cells") or [{"cell_id": None, "verdict": "RED", "rule": h.get("rule"),
                                  "line": h.get("line")} for h in doc.get("hits") or []]
    red = [c for c in cells if (c.get("verdict") or "RED") == "RED"]
    ex = [c for c in cells if c.get("verdict") == "EXEMPTED"]
    blocked = doc.get("contract_blocked") or []
    tokens = []
    for b in blocked:
        tokens += list(b.get("examples") or [])
    for c in ex:
        tokens += list((c.get("exemption_detail") or {}).get("tokens_seen") or [])
    for c in doc.get("contract_exempted") or []:
        tokens += list(c.get("tokens_seen") or [])
    return {"rc": p.returncode, "cells_total": len(cells), "red": len(red), "exempted": len(ex),
            "contract_exempted": len(doc.get("contract_exempted") or []),
            "contract_blocked": len(blocked),
            "whys": sorted({b.get("why") for b in blocked if b.get("why")}),
            "tokens_counted": sorted(set(tokens)),
            "fold_exempted": len(doc.get("attributed_in_fold") or [])}


def token_provenance(fixture, tokens):
    """For each counted token, what is the only thing the file does with it?"""
    text = io.open(fixture, encoding="utf-8").read().split("\n")
    rows = []
    for t in tokens:
        hits = []
        for n, line in enumerate(text, 1):
            if '"' + t + '"' not in line:
                continue
            s = line.strip()
            if re.search(r"(code|reason)\s*(===|==|!==|!=)\s*\"" + t + "\"", s):
                role = "compares_the_field"
            elif re.search(r"(const|let)\s+code\s*=.*\|\|\s*\"" + t + "\"", s) or \
                    re.search(r"code\s*[:=]\s*\"" + t + "\"", s):
                role = "assigned_to_the_field"
            elif re.search(r"\b" + t + r"\b", s) and "code" not in s:
                role = "other_field"
            else:
                role = "unclear"
            hits.append({"line": n, "role": role, "text": s[:120]})
        rows.append({"token": t, "where": hits})
    return rows


def main():
    out = {"method": "each fixture run through both rulers with each contract, `--file` mode, cwd "
                      "D:/moodle/_qoder_cmdr_ref_20260921/live_checks; no ruler byte was changed for this file",
           "field_the_contract_names": FIELD, "fixtures": {}, "contracts": {}}
    for name, path in CONTRACTS.items():
        raw = io.open(path, "rb").read()
        out["contracts"][name] = {"path": path, "bytes": len(raw)}
    for fx in sorted(os.listdir(FX)):
        if not fx.endswith(".tsx"):
            continue
        full = os.path.join(FX, fx)
        row = {"path": full}
        for cname, cpath in CONTRACTS.items():
            row[cname] = {"r7b4": run(R7B4, full, cpath), "r8": run(R8, full, cpath)}
        # provenance under the contract that names the set (the case where a token can be blamed)
        toks = set()
        for cname in CONTRACTS:
            for side in ("r7b4", "r8"):
                toks |= set(row[cname][side].get("tokens_counted") or [])
        row["token_provenance"] = token_provenance(full, sorted(toks))
        out["fixtures"][fx.replace("__JourneyTrashPanel.tsx", "")] = row
    io.open(os.path.join(WORK, "value_flow_baseline_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    for fx, row in out["fixtures"].items():
        r8i = row["inline_enum_names_the_set"]["r8"]
        r7i = row["inline_enum_names_the_set"]["r7b4"]
        print("%-18s r7b4 red %s / exempt %s | r8 red %s / exempt %s | tokens %s" % (
            fx, r7i["red"], r7i["contract_exempted"], r8i["red"], r8i["contract_exempted"],
            ",".join(r8i["tokens_counted"]) or "-"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
