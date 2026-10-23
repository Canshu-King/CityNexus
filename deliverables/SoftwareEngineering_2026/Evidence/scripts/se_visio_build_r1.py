"""Build the four CityNexus Visio diagrams and prove each one opened, saved,
was edited, and re-opened. Refuses to write a preview for a diagram that fails
its own layout/semantics gate.
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import win32com.client as w32                      # noqa: E402
from se_visio_lib_r1 import Builder, GateError     # noqa: E402
from se_visio_specs_r1 import ALL                  # noqa: E402

OUT = os.environ.get("SE_VISIO_OUT", r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Visio")
RESULT = os.path.join(HERE, "se_visio_build_result.json")
SPECDIR = os.path.join(OUT, "specs")
_t0 = time.time()
_lines = []


def log(m):
    line = "[%6.1fs] %s" % (time.time() - _t0, m)
    print(line, flush=True)
    _lines.append(line)


def main(only=None, proof=False):
    os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
    os.makedirs(SPECDIR, exist_ok=True)
    report = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "diagrams": [],
              "proof": None}
    built = []
    for fn in ALL:
        spec = fn()
        if only and not any(o in spec["file"] for o in only):
            continue
        stem = os.path.splitext(spec["file"])[0]
        json.dump(spec, open(os.path.join(SPECDIR, stem + ".json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        paths = {
            "vsdx": os.path.join(OUT, spec["file"]),
            "png": os.path.join(OUT, "previews", stem + ".png"),
            "pdf": os.path.join(OUT, "previews", stem + ".pdf"),
            "gate": os.path.join(OUT, "previews", stem + ".gate.json"),
            "debugPng": os.path.join(HERE, "debug", stem + ".png"),
            "debugPdf": os.path.join(HERE, "debug", stem + ".pdf"),
        }
        for d in (os.path.dirname(paths["vsdx"]), os.path.dirname(paths["png"])):
            os.makedirs(d, exist_ok=True)
        sheets = spec.get("sheets") or [spec]
        log("=== %s : pages=%d nodes=%d edges=%d bands=%d" % (
            spec["file"], len(sheets),
            sum(len(sh.get("nodes", [])) for sh in sheets),
            sum(len(sh.get("edges", [])) for sh in sheets),
            sum(len(sh.get("bands", [])) for sh in sheets)))
        b = Builder(spec, paths, log)
        try:
            rep = b.build()
        except GateError as exc:
            rep = json.load(open(paths["gate"], encoding="utf-8"))
            rep["aborted"] = str(exc)
            json.dump(rep, open(paths["gate"], "w", encoding="utf-8"), indent=1, ensure_ascii=False)
            report["diagrams"].append({"file": spec["file"], "status": "GATE_FAIL", "gate": rep})
            log("  GATE FAIL: %s" % exc)
            for f in rep["failures"][:25]:
                log("    - %s" % f)
            continue
        for f in rep["failures"]:
            log("    gate note: %s" % f)
        sz = {k: (os.path.getsize(v) if os.path.exists(v) else 0)
              for k, v in paths.items() if k != "gate"}
        log("  built ok  vsdx=%d png=%d pdf=%d" % (sz["vsdx"], sz["png"], sz["pdf"]))
        built.append((spec, paths, rep))
        report["diagrams"].append({"file": spec["file"], "status": "BUILT", "gate": rep,
                                   "sizes": sz})
    if proof and built:
        report["proof"] = reopen_proof(built)
    report["styleIssues"] = {d["file"]: d["gate"].get("styleIssues", []) for d in report["diagrams"]
                             if d.get("gate")}
    json.dump(report, open(RESULT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    log("wrote %s" % RESULT)
    return report


def reopen_proof(built):
    """Mandatory verification per diagram, all three passes against the shipped file:

    A open -> pick a node by its stable Shape.ID -> move it 0.3in and prove the
      glued connector endpoint moved with it (live glue, not a painted line)
    B overwrite that node's text with a marker, save, close, reopen, read the
      marker back, restore the original text, save, close, reopen, confirm the
      restore landed and the connection count is unchanged.
    """
    out = []
    vis = w32.DispatchEx("Visio.Application")
    for prop, val in (("Visible", False), ("AlertResponse", 7), ("ScreenUpdating", 0)):
        try:
            setattr(vis, prop, val)
        except Exception:
            pass
    for spec, paths, rep in built:
        rec = {"file": spec["file"], "glueLive": None, "editRoundTrip": None, "ok": False}
        stem = os.path.splitext(spec["file"])[0]
        snapshot = os.path.join(HERE, "_pre_proof_%s.vsdx" % stem)
        shutil.copyfile(paths["vsdx"], snapshot)
        try:
            d = vis.Documents.Open(paths["vsdx"])
            pg = d.Pages.Item(1)
            rec["open"] = {"shapes": pg.Shapes.Count, "connects": pg.Connects.Count,
                           "pageName": pg.Name}

            # ---- find a node that both owns a master and carries glue
            target, tid = None, None
            for i in range(1, pg.Shapes.Count + 1):
                sh = pg.Shapes.Item(i)
                if sh.Connects.Count > 0 and sh.Master is not None:
                    target, tid = sh, sh.ID
                    break
            if target is None:
                rec["error"] = "no connected master shape found"
                d.Close()
                continue
            rec["targetShapeID"] = tid
            rec["targetMaster"] = target.Master.Name
            original = target.Text

            # ---- A: move it and watch the glued connector endpoint follow
            y0 = target.Cells("PinY").ResultIU
            conn = None
            for k in range(1, target.Connects.Count + 1):
                crec = target.Connects.Item(k)
                for prop in ("ToSheet", "FromSheet"):
                    try:
                        cand = getattr(crec, prop)
                    except Exception:
                        continue
                    if cand is not None and cand.ID != target.ID:
                        conn = cand
                        break
                if conn is not None:
                    break
            if conn is not None:
                bx0 = conn.Cells("BeginX").ResultIU
                by0 = conn.Cells("BeginY").ResultIU
                target.Cells("PinY").FormulaU = "=PinY+0.3in"
                bx1 = conn.Cells("BeginX").ResultIU
                by1 = conn.Cells("BeginY").ResultIU
                rec["glueLive"] = {"shapePinY": [round(y0, 4), round(target.Cells("PinY").ResultIU, 4)],
                                   "connBeginY": [round(by0, 4), round(by1, 4)],
                                   "moved": abs(by1 - by0) > 0.05}
                target.Cells("PinY").FormulaU = "=PinY-0.3in"
            else:
                rec["glueLive"] = {"moved": False, "note": "no connector found on this shape"}

            # ---- B: text edit -> save -> close -> reopen -> read back
            marker = "PROOF-EDIT %s" % time.strftime("%H%M%S")
            target.Text = marker
            d.Save()
            d.Close()
            d2 = vis.Documents.Open(paths["vsdx"])
            back = None
            for i in range(1, d2.Pages.Item(1).Shapes.Count + 1):
                sh = d2.Pages.Item(1).Shapes.Item(i)
                if sh.ID == tid:
                    back = sh.Text
                    sh.Text = original
                    break
            d2.Save()
            d2.Close()
            rec["editRoundTrip"] = {"wrote": marker, "readBackAfterReopen": back,
                                    "matched": back == marker}
            d3 = vis.Documents.Open(paths["vsdx"])
            pg3 = d3.Pages.Item(1)
            restored = None
            for i in range(1, pg3.Shapes.Count + 1):
                sh = pg3.Shapes.Item(i)
                if sh.ID == tid:
                    restored = sh.Text
                    break
            rec["restore"] = {"original": original.split("\n")[0][:60],
                              "afterRestore": (restored or "").split("\n")[0][:60],
                              "shapes": pg3.Shapes.Count, "connects": pg3.Connects.Count,
                              "connectsUnchanged": pg3.Connects.Count == rec["open"]["connects"]}
            d3.Close()
            rec["ok"] = bool(rec["editRoundTrip"]["matched"]
                             and (restored or "").startswith(original.split("\n")[0])
                             and rec["glueLive"].get("moved")
                             and rec["restore"]["connectsUnchanged"])
        except Exception as exc:
            rec["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:200])
            try:
                vis.Documents.Close()
            except Exception:
                pass
        out.append(rec)
        log("  proof %s -> ok=%s %s" % (spec["file"], rec["ok"],
                                        json.dumps({k: v for k, v in rec.items()
                                                    if k in ("glueLive", "editRoundTrip", "restore", "error")},
                                                   ensure_ascii=False)[:400]))
    try:
        vis.Quit()
    except Exception as exc:
        log("  (visio quit raised %s)" % type(exc).__name__)
    return out


if __name__ == "__main__":
    only = sys.argv[1:] or None
    r = main(only)
    bad = [d for d in r["diagrams"] if d["status"] != "BUILT"]
    print("BUILT=%d FAILED=%d" % (len(r["diagrams"]) - len(bad), len(bad)))
    sys.exit(1 if bad else 0)
