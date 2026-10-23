"""Cold-start readiness check: open every native file from a clean extracted copy.

The task book's remaining instruction after the P0s is a readiness pass, not new
features, so this takes the noon bundle, extracts it to a directory that has never
held these files, and asks the real applications to open each one read-only - Visio
reporting shapes and connectors per page, Project reporting rows, links, cost and
finish. Anything that will not open from a cold directory will not open on the
projector either, and a file that only opens next to its own folder is a defect worth
finding at 07:30 rather than at 11:50.

Nothing is written back: every document is opened with the file made read-only at the
filesystem level, and the digests are compared afterwards.
"""
import hashlib
import json
import os
import shutil
import stat
import sys
import time
import zipfile
import win32com.client as w32

HERE = os.path.dirname(os.path.abspath(__file__))
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
ZIP = r"D:\moodle\CityNexus_20261023_Noon_Ready.zip"
TMP = os.path.join(HERE, "_ready")
LOG = open(os.path.join(HERE, "se_classroom_readiness_r1.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def sha(p, n=16):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:n]


def pages(path):
    import re
    data = open(path, "rb").read()
    hits = [int(x) for x in re.findall(rb"/Count\s+(\d+)", data)]
    return max(hits) if hits else 0


shutil.rmtree(TMP, ignore_errors=True)
os.makedirs(TMP)
zipfile.ZipFile(ZIP).extractall(TMP)
ROOT = os.path.join(TMP, "CityNexus_Noon_20261023")
log("extracted %s -> %s" % (os.path.basename(ZIP), ROOT))

# every extracted file must be byte-identical to the one in the delivery tree
man = open(os.path.join(ROOT, "MANIFEST.sha256"), encoding="utf-8").read().splitlines()
bad = []
for line in man:
    digest, name = line.split("  ", 1)
    p = os.path.join(ROOT, *name.split("/"))
    if not os.path.exists(p):
        bad.append("missing " + name)
    elif hashlib.sha256(open(p, "rb").read()).hexdigest() != digest:
        bad.append("digest " + name)
log("manifest entries %d, failures %d" % (len(man), len(bad)))

VSDX = [f for f in os.listdir(os.path.join(ROOT, "Visio")) if f.endswith(".vsdx")]
MPP = [f for f in os.listdir(os.path.join(ROOT, "Microsoft_Project"))
       if f.endswith(".mpp")] + [f for f in os.listdir(os.path.join(ROOT, "Classroom"))
                                 if f.endswith(".mpp")]
report = {"manifestFailures": bad, "visio": [], "project": [], "pdf": [],
          "checkedAt": time.strftime("%Y-%m-%d %H:%M")}

vis = w32.DispatchEx("Visio.Application")
vis.Visible = True
try:
    vis.AlertResponse = 7
except Exception:
    pass
for f in sorted(VSDX):
    p = os.path.join(ROOT, "Visio", f)
    os.chmod(p, stat.S_IREAD)
    rec = {"file": f, "sha256_16": sha(p)}
    try:
        d = vis.Documents.Open(p)
        pages_n = d.Pages.Count
        shapes = 0
        connects = 0
        props = 0
        for i in range(1, pages_n + 1):
            pg = d.Pages.Item(i)
            shapes += pg.Shapes.Count
            connects += pg.Connects.Count
            for sh in pg.Shapes:
                try:
                    props += len([n for n in sh.SectionNames if n == "Prop"]) and \
                        sh.SectionRowCount("Prop", 0)
                except Exception:
                    pass
        rec.update({"ok": True, "pages": pages_n, "shapes": shapes,
                    "connects": connects, "propRows": props})
        d.Saved = True
        d.Close()
    except Exception as exc:
        rec.update({"ok": False, "error": "%s: %s" % (type(exc).__name__,
                                                      str(exc)[:120])})
    os.chmod(p, stat.S_IWRITE)
    report["visio"].append(rec)
    log("  visio %-46s %s" % (f, json.dumps(rec, ensure_ascii=False)[:120]))
try:
    vis.Quit()
except Exception:
    pass

mp = w32.DispatchEx("MSProject.Application")
mp.Visible = True
try:
    mp.DisplayAlerts = 0
except Exception:
    pass
for f in sorted(MPP):
    for sub in ("Microsoft_Project", "Classroom"):
        p = os.path.join(ROOT, sub, f)
        if os.path.exists(p):
            break
    os.chmod(p, stat.S_IREAD)
    rec = {"file": f, "sha256_16": sha(p)}
    try:
        mp.FileOpen(p)
        time.sleep(1.0)
        t = mp.ActiveProject
        links = 0
        for i in range(1, t.Tasks.Count + 1):
            try:
                links += t.Tasks.Item(i).TaskDependencies.Count
            except Exception:
                pass
        rec.update({"ok": True, "rows": t.Tasks.Count,
                    "resources": t.Resources.Count,
                    "linkRecords": links, "cost": round(float(t.Cost), 2),
                    "start": str(t.Start)[:10], "finish": str(t.Finish)[:10],
                    "readOnly": bool(t.ReadOnly)})
        mp.FileCloseEx(0)
    except Exception as exc:
        rec.update({"ok": False, "error": "%s: %s" % (type(exc).__name__,
                                                      str(exc)[:120])})
        try:
            mp.FileCloseEx(0)
        except Exception:
            pass
    os.chmod(p, stat.S_IWRITE)
    report["project"].append(rec)
    log("  project %-46s %s" % (f, json.dumps(rec, ensure_ascii=False)[:150]))
try:
    mp.Quit()
except Exception:
    pass

for pdf in (os.path.join(ROOT, "Presentation", "CityNexus_SE2026_Briefing_Deck.pdf"),):
    report["pdf"].append({"file": os.path.basename(pdf), "pages": pages(pdf),
                          "bytes": os.path.getsize(pdf) if os.path.exists(pdf) else 0})
    log("  pdf %s -> %d pages" % (os.path.basename(pdf), pages(pdf)))
for png in sorted(os.listdir(os.path.join(ROOT, "Classroom", "previews"))):
    p = os.path.join(ROOT, "Classroom", "previews", png)
    from PIL import Image
    im = Image.open(p)
    report["pdf"].append({"file": "Classroom/previews/" + png, "px": list(im.size)})
    log("  png %-32s %dx%d" % (png, im.size[0], im.size[1]))

report["allOpen"] = bool(all(r["ok"] for r in report["visio"] + report["project"])
                         and not bad)
json.dump(report, open(os.path.join(HERE, "se_classroom_readiness_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False)
shutil.rmtree(TMP, ignore_errors=True)
if not report["allOpen"]:
    log("READINESS FAILED")
    LOG.close()
    sys.exit(1)
log("READINESS OK: %d .vsdx and %d .mpp opened from a clean directory, manifest clean"
    % (len(report["visio"]), len(report["project"])))
LOG.close()
sys.exit(0)
