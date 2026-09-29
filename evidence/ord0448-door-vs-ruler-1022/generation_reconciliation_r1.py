"""Three ruler generations, one identical byte-for-byte export, one command.

The order's two readings that disagreed (the door's 12 cells and this lane's 11) were never compared
generation-to-generation. `cells_tip.json` was r7b, `id_tip.json` was r7b1 -- different rulers, both
honest, and nobody had checked whether the newer one still sees what the older one saw.
One `git archive` of the tip, then every generation runs over the SAME files.
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
TIP = "0fee131d02b7c7c85f59aab8307f28594bf0d65f"
NUL = chr(0).encode()
GENS = [("r7b", "ui_exposure_taint_ast_r7b.cjs", "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"),
        ("r7b1", "ui_exposure_taint_ast_r7b1.cjs", "b6716d9a3c67dafc72fef501bfaff101c84e918a"),
        ("r7b4", "ui_exposure_taint_ast_r7b4.cjs", "cefcb38c8d01a5996f3f705531a127c85f16c0b3")]
EXPORT = os.path.join(WORK, "_gen_export")


def blob_of(path):
    raw = io.open(path, "rb").read()
    return hashlib.sha1(b"blob %d" % len(raw) + NUL + raw).hexdigest(), len(raw)


def extract_once():
    if os.path.isdir(EXPORT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", EXPORT], timeout=600)
    os.makedirs(EXPORT, exist_ok=True)
    src = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, TIP, EXPORT),
                         shell=True, capture_output=True, timeout=900)
    assert src.returncode == 0, src.stderr[:300]
    n = len(glob.glob(os.path.join(EXPORT, "frontend", "src", "**", "*.ts*"), recursive=True))
    return n


def main():
    tsx = extract_once()
    out = {"tip_rev": TIP, "export_tsx_files": tsx, "generations": []}
    base = os.path.join(EXPORT, "frontend", "src")
    for tag, name, pin in GENS:
        path = os.path.join(REF, name)
        got, size = blob_of(path)
        rec = {"generation": tag, "file": name, "bytes": size, "blob_declared_by_lane": pin,
               "blob_measured": got, "blob_matches": got == pin}
        if got != pin:
            rec["status"] = "SKIPPED_IDENTITY_MISMATCH"
            out["generations"].append(rec)
            continue
        js = os.path.join(EXPORT, "ruler_%s.json" % tag)
        r = subprocess.run(["node", path, "--tree", base, "--out", js],
                           capture_output=True, timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if not os.path.isfile(js):
            rec.update(status="RULER_FAILED", rc=r.returncode, stderr=r.stderr[:300].decode("utf-8", "replace"))
            out["generations"].append(rec)
            continue
        doc = json.load(io.open(js, encoding="utf-8"))
        cells = ["%s:%s|%s" % (str(h["file"]).split("/")[-1], h["line"], h.get("rule"))
                 for h in doc.get("hits", [])]
        rec.update(status="ok", cells_total=doc.get("cells_total"), hits=len(cells),
                   keys=sorted(set(cells)))
        out["generations"].append(rec)
    ok = [g for g in out["generations"] if g["status"] == "ok"]
    # r7b4's contract machinery reads `contracts/openapi.yaml` by walking up from the scanned tree.
    # The door exports frontend/src only, so a blind re-point would consult no contract at all; measure
    # both scopes rather than assert it.
    r7b4 = [g for g in out["generations"] if g["generation"] == "r7b4" and g["status"] == "ok"]
    if r7b4:
        cdir = os.path.join(EXPORT, "contracts")
        os.makedirs(cdir, exist_ok=True)
        y = subprocess.run("git -C %s show %s:contracts/openapi.yaml > %s" %
                           (REPO, TIP, os.path.join(cdir, "openapi.yaml").replace("/", "\\")),
                           shell=True, capture_output=True, timeout=300)
        cpath = os.path.join(cdir, "openapi.yaml")
        with_contract = {"generation": "r7b4_with_contract", "file": "ui_exposure_taint_ast_r7b4.cjs",
                         "blob_measured": blob_of(os.path.join(REF, "ui_exposure_taint_ast_r7b4.cjs"))[0],
                         "contract_bytes": os.path.getsize(cpath) if y.returncode == 0 else None}
        if y.returncode == 0:
            js2 = os.path.join(EXPORT, "ruler_r7b4_contract.json")
            subprocess.run(["node", os.path.join(REF, "ui_exposure_taint_ast_r7b4.cjs"),
                            "--tree", base, "--out", js2, "--contract", cpath],
                           capture_output=True, timeout=1800,
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
            if os.path.isfile(js2):
                d2 = json.load(io.open(js2, encoding="utf-8"))
                k2 = sorted({"%s:%s|%s" % (str(h["file"]).split("/")[-1], h["line"], h.get("rule"))
                             for h in d2.get("hits", [])})
                with_contract.update(status="ok", cells_total=d2.get("cells_total"),
                                     hits=len(k2), keys=k2,
                                     differs_from_door_scope=r7b4[0]["keys"] != k2)
        out["generations"].append(with_contract)
    if len(ok) >= 2:
        anchor = ok[0]
        for g in ok[1:]:
            out.setdefault("pairwise", [])
            out["pairwise"].append({
                "older": anchor["generation"], "newer": g["generation"],
                "lost_from_newer": sorted(set(anchor["keys"]) - set(g["keys"])),
                "gained_by_newer": sorted(set(g["keys"]) - set(anchor["keys"]))})
    io.open(os.path.join(WORK, "generation_reconciliation_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    for g in out["generations"]:
        print("%-5s %-34s bytes %-7s blob_ok %-5s hits %s" %
              (g["generation"], g["file"], g["bytes"], g["blob_matches"], g.get("hits", "-")))
    for p in out.get("pairwise", []):
        print("%-4s -> %-4s lost %d gained %d  %s" % (p["older"], p["newer"], len(p["lost_from_newer"]),
                                                      len(p["gained_by_newer"]), p["lost_from_newer"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
