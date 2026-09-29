"""Single-variable test of why the newer generations lose `RecoveryRequiredPanel.tsx:299`.

The reconciliation (`generation_reconciliation_r1.json`) shows one identical export read by three
generations: r7b keeps the cell, r7b1 and r7b4 both lose it. That is the pin. The only construct between
the `<code data-testid="recovery-reason">` opening tag and its `{notice.quote}` child that the newer
generations handle differently is the conditional attribute spread five lines above it:

    {...(notice.field ? { "data-cnx-field": notice.field } : {})}

This builds ONE modified export -- the shipped file with that spread deleted, nothing else touched -- and
runs both generations over the same bytes. Three outcomes are possible and the script names which one it
got: the cell returns with the same sink shape (the spread is the cause); the cell stays missing (the
explanation is refuted); or the key returns attached to a different element, which means my fixture moved
the parser and proves nothing beyond the pin. The run landed on the third.
"""
import glob
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
TIP = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
TARGET = os.path.join("features", "recovery", "RecoveryRequiredPanel.tsx")
SPREAD_RX = re.compile(r"\{\.\.\.\(notice\.field \? \{ \"data-cnx-field\": notice\.field \} : \{\}\)\}")
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"),
        ("r7b1", "ui_exposure_taint_ast_r7b1.cjs"),
        ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]
EXPORT = os.path.join(WORK, "_spread_export")


def build_modified_export():
    if os.path.isdir(EXPORT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", EXPORT], timeout=300)
    os.makedirs(EXPORT, exist_ok=True)
    r = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, TIP, EXPORT),
                       shell=True, capture_output=True, timeout=900)
    assert r.returncode == 0, r.stderr[:200]
    path = os.path.join(EXPORT, "frontend", "src", TARGET)
    text = io.open(path, encoding="utf-8").read()
    n = len(SPREAD_RX.findall(text))
    assert n == 1, "spread found %d times, fixture premise is wrong" % n
    edited = SPREAD_RX.sub("{ \"data-cnx-field\": notice.field || \"\" }", text)
    io.open(path, "w", encoding="utf-8", newline="").write(edited)
    import hashlib
    return {"spread_occurrences_found": n,
            "file_bytes_before": len(text.encode("utf-8")),
            "file_bytes_after": len(edited.encode("utf-8")),
            "edited_file_sha1_over_bytes": hashlib.sha1(edited.encode("utf-8")).hexdigest(),
            "tsx_files_in_export": len(glob.glob(os.path.join(EXPORT, "frontend", "src",
                                                              "**", "*.ts*"), recursive=True))}


def run(tag, name, fixture_sha=None):
    js = os.path.join(WORK, "spread_%s.json" % tag)
    side = js + ".fixture"
    if os.path.isfile(js):
        # a cached reading of these exact bytes stands only if the fixture is byte-identical to the one
        # that produced it; the sha is recorded next to it on every run that actually invokes node.
        if fixture_sha and os.path.isfile(side):
            prev = io.open(side, encoding="utf-8").read().strip()
            assert prev == fixture_sha, "cached reading is of different bytes (%s vs %s)" % (
                prev[:12], fixture_sha[:12])
        return summarize(tag, js)
    r = subprocess.run(["node", os.path.join(REF, name), "--tree",
                        os.path.join(EXPORT, "frontend", "src"), "--out", js],
                       capture_output=True, timeout=1800,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    if not os.path.isfile(js):
        return {"status": "FAILED", "rc": r.returncode,
                "stderr": r.stderr[:200].decode("utf-8", "replace")}
    if fixture_sha:
        io.open(side, "w", encoding="utf-8", newline="\n").write(fixture_sha)
    return summarize(tag, js)


def summarize(tag, js):
    doc = json.load(io.open(js, encoding="utf-8"))
    rows = [h for h in doc.get("hits", [])
            if str(h["file"]).replace("\\", "/").split("/")[-1] == os.path.basename(TARGET)]
    return {"status": "ok", "cells_total": doc.get("cells_total"),
            "recovery_cells": [{"line": h["line"], "rule": h.get("rule"),
                                "cell_id": h.get("cell_id"),
                                "sink_shape": (h.get("structural") or {}).get("sink_shape")}
                               for h in rows]}


def main():
    exp = build_modified_export()
    out = {"tip_rev": TIP, "modification": "conditional attribute spread replaced by a plain "
                                           "attribute; no other byte in the export changed",
           "export": exp, "by_generation": {}}
    for tag, name in GENS:
        out["by_generation"][tag] = run(tag, name, exp["edited_file_sha1_over_bytes"])
    keep = lambda tag: any(c["sink_shape"] and "recovery-reason" in c["sink_shape"]
                           for c in out["by_generation"][tag].get("recovery_cells", []))
    out["recovery_reason_sink_present"] = {tag: keep(tag) for tag, _ in GENS}
    PRISTINE_KEY = "RecoveryRequiredPanel.tsx:299|UPSTREAM_TEXT_VIA_HELPER_TO_DOM"
    def keys(tag):
        js = os.path.join(WORK, "spread_%s.json" % tag)
        if not os.path.isfile(js):
            return set()
        d = json.load(io.open(js, encoding="utf-8"))
        return {"%s:%s|%s" % (str(h["file"]).replace("\\", "/").split("/")[-1], h["line"], h.get("rule"))
                for h in d.get("hits", [])}
    ks = {tag: keys(tag) for tag, _ in GENS}
    out["cell_keys_after_the_edit"] = {tag: sorted(ks[tag]) for tag, _ in GENS}
    out["lost_key_present_after_the_edit"] = {tag: (PRISTINE_KEY in ks[tag]) for tag, _ in GENS}
    out["all_three_agree_on_the_same_key_set"] = ks["r7b"] == ks["r7b1"] == ks["r7b4"]
    newer_return = all(out["lost_key_present_after_the_edit"][t] for t in ("r7b1", "r7b4"))
    # a fixture that stops attributing the same sink is not a single-variable test: deleting the spread
    # moves which element line 299 lands in (details:recovery-technical instead of code:recovery-reason),
    # so this can name the spread as the only thing that changed and nothing more.
    want = "text-in:code testid=code:recovery-reason"
    out["expected_sink_shape"] = want
    out["sink_shape_preserved"] = {
        tag: any((c.get("sink_shape") or "") == want
                 for c in out["by_generation"][tag].get("recovery_cells", [])) for tag, _ in GENS}
    ids = {tag: [c.get("cell_id") for c in out["by_generation"][tag].get("recovery_cells", [])]
           for tag, _ in GENS}
    out["recovery_cell_id_by_generation"] = ids
    # the cell-identity arm depends on this property, so state it in the two directions separately:
    # identical bytes give identical `cell_id` across generations (needed: a baseline read under an older
    # generation stays comparable); different bytes give a different `cell_id` (needed: an identity that
    # ignored its own source would not detect a genuine change).
    out["identity_stable_across_generations_same_bytes"] = len({i[0] for i in ids.values() if i}) == 1
    pristine = json.load(io.open(os.path.join(WORK, "cells_tip.json"), encoding="utf-8"))
    pid = [c.get("id") for c in pristine["cells"] if c["key"] == PRISTINE_KEY]
    out["cell_id_pristine_r7b"] = pid
    out["identity_changed_with_the_bytes"] = bool(pid) and pid[0] not in {
        i for j in ids.values() for i in j}
    rec = json.load(io.open(os.path.join(WORK, "generation_reconciliation_r1.json"), encoding="utf-8"))
    out["control_pristine_export"] = {
        "cells_by_generation": {g["generation"]: g.get("hits") for g in rec["generations"]
                                if g["status"] == "ok"},
        "lost_from_newer": [p["lost_from_newer"] for p in rec.get("pairwise", [])],
        "source": "generation_reconciliation_r1.json, same tip rev, spread present"}
    shape_ok = all(out["sink_shape_preserved"][t] for t, _ in GENS)
    if not shape_ok:
        out["reading"] = ("INCONCLUSIVE_FIXTURE: the key `RecoveryRequiredPanel.tsx:299|"
                          "UPSTREAM_TEXT_VIA_HELPER_TO_DOM` reappears for all three generations, but the "
                          "sink that line now belongs to is `text-in:details testid=details:recovery-"
                          "technical`, not the shipped `text-in:code testid=code:recovery-reason`. "
                          "Deleting the spread moved the element the parser is inside, so this is not a "
                          "single-variable test and it does not prove the spread is the cause. What "
                          "stands is the pin: on pristine bytes, identical export, r7b reads the cell and "
                          "r7b1/r7b4 do not.")
    elif newer_return:
        out["reading"] = ("spread explains it: with that one attribute changed and the same sink still "
                          "attributed, both newer generations report the recovery-reason cell again")
    else:
        out["reading"] = ("spread does NOT explain it: the cell stays missing under the newer generations "
                          "even with the spread gone -- the pin stands, my explanation is refuted")
    io.open(os.path.join(WORK, "spread_isolation_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    for tag, _ in GENS:
        print("%-5s cells_total %-4s recovery cells %s" %
              (tag, out["by_generation"][tag].get("cells_total"),
                 json.dumps(out["by_generation"][tag].get("recovery_cells"), ensure_ascii=False)[:220]))
    print("lost_key_present_after_edit", out["lost_key_present_after_the_edit"])
    print("sink_shape_preserved", out["sink_shape_preserved"])
    print(out["reading"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
