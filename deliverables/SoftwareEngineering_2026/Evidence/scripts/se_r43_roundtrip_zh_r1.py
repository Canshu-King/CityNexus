"""R4.3 edit round-trip (zh): prove the loop is an editable, glued connector.

R42 edited the old bottom-left notes caption; R4.3 moved those notes to
page 2, so the non-critical edit target is now the docid meta line.

The reviewer's second acceptance step is "change one non-critical word, save under
another name, close, reopen, and check the nodes and arrows are still editable and
the line ends are still attached". A PNG cannot answer that, and a builder log
cannot either - so this writes the edited copy to E:, reopens it cold, and runs the
same ShapeSheet assertions `se_r42_loop_proof_r1.py` makes against the original.

The delivered drawing is opened read-only (chmod 0444) and is never the save
target; its digest is re-checked at the end and a change is a hard failure.
"""
import hashlib
import json
import os
import shutil
import sys
import time

import win32com.client as w

HERE = os.path.dirname(os.path.abspath(__file__))
CLS = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Classroom"
VSDX = os.path.join(CLS, "Teacher_02_Agent_User_Flow.vsdx")
COPY = r"E:\r43_review\_rt_Teacher_02_edited_copy.vsdx"
OUT = os.path.join(HERE, "se_r43_roundtrip_zh.json")
# a non-critical word: the caption of the note block, not a node and not an arrow
# R4.3: the notes block moved to page 2, so the non-critical caption on
# page 1 is now the docid meta line in the title block (not a node, not
# an arrow - same spirit as the r42 choice).
OLD_WORD = "课堂演示图"
NEW_WORD = "课堂演示图（可编辑）"
# what the loop must still look like after the round trip (page inches, y up)
LOOP = {"tail": (6.625, 4.360), "head": (6.625, 5.130)}
T0 = time.time()
rec = {"copy": COPY, "notes": []}


def log(msg):
    print("[%5.1fs] %s" % (time.time() - T0, msg), flush=True)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def num(sh, name):
    try:
        return float(sh.Cells(name).ResultIU)
    except Exception:
        return None


def txt(sh, name):
    try:
        return str(sh.Cells(name).FormulaU).strip().strip('"')
    except Exception:
        return ""


def find_loop(page):
    """The connector glued to both t2n7 and t2n3, with its ends and arrow cells."""
    conn_ids, glued = set(), {}
    for i in range(1, page.Connects.Count + 1):
        c = page.Connects.Item(i)
        fid = int(c.FromSheet.ID)
        conn_ids.add(fid)
        glued.setdefault(fid, []).append(int(c.ToSheet.ID))
    by_id = {int(page.Shapes.Item(i).ID): page.Shapes.Item(i)
             for i in range(1, page.Shapes.Count + 1)}
    for sid in conn_ids:
        names = [txt(by_id[v], "prop.NodeId") for v in glued.get(sid, [])
                 if v in by_id]
        if "t2n7" in names and "t2n3" in names:
            sh = by_id[sid]
            return {"shape": sh, "gluedTo": sorted(names),
                    "begin": (num(sh, "BeginX"), num(sh, "BeginY")),
                    "end": (num(sh, "EndX"), num(sh, "EndY")),
                    "endArrow": num(sh, "EndArrow"),
                    "beginArrow": num(sh, "BeginArrow"),
                    "flowEdge": txt(sh, "prop.FlowEdge")}
    return None


def text_hits(page, needle):
    """How many shapes on the page carry `needle` in their text."""
    n = 0
    for i in range(1, page.Shapes.Count + 1):
        sh = page.Shapes.Item(i)
        try:
            if needle in str(sh.Text):
                n += 1
        except Exception:
            pass
    return n


before = sha(VSDX)
os.chmod(VSDX, 0o444)
os.makedirs(os.path.dirname(COPY), exist_ok=True)
if os.path.exists(COPY):
    os.chmod(COPY, 0o644)
    os.remove(COPY)
app = None
try:
    app = w.DispatchEx("Visio.Application")
    app.Visible = False
    try:
        app.AlertResponse = 7
    except Exception:
        pass
    doc = app.Documents.OpenEx(VSDX, 2)
    page = doc.Pages(1)
    loop = find_loop(page)
    if loop is None:
        raise RuntimeError("the loop connector is not in the source file at all")
    rec["sourceLoop"] = {"gluedTo": loop["gluedTo"], "flowEdge": loop["flowEdge"],
                         "begin": loop["begin"], "end": loop["end"],
                         "endArrow": loop["endArrow"],
                         "beginArrow": loop["beginArrow"]}
    log("source loop %r glued %s begin %s end %s"
        % (loop["flowEdge"], loop["gluedTo"], loop["begin"], loop["end"]))
    edited = 0
    for i in range(1, page.Shapes.Count + 1):
        sh = page.Shapes.Item(i)
        try:
            t = str(sh.Text)
        except Exception:
            continue
        if OLD_WORD in t:
            sh.Text = t.replace(OLD_WORD, NEW_WORD)
            edited += 1
    rec["shapesEdited"] = edited
    log("edited %d shape(s): %r -> %r" % (edited, OLD_WORD, NEW_WORD))
    if edited == 0:
        raise RuntimeError("the non-critical word was not found - nothing was "
                           "edited, so the round trip would prove nothing")
    doc.SaveAs(COPY)
    log("saved copy to %s" % COPY)
    doc.Close()
    copy_sha = sha(COPY)

    # cold reopen: a fresh document object, not the one that was edited
    doc2 = app.Documents.OpenEx(COPY, 2)
    page2 = doc2.Pages(1)
    loop2 = find_loop(page2)
    rec["reopenTextFound"] = text_hits(page2, NEW_WORD)
    rec["reopenShapes"] = int(page2.Shapes.Count)
    rec["reopenConnects"] = int(page2.Connects.Count)
    if loop2 is None:
        rec["findings"] = ["after reopen the loop connector is gone"]
    else:
        rec["reopenedLoop"] = {"gluedTo": loop2["gluedTo"],
                               "flowEdge": loop2["flowEdge"],
                               "begin": loop2["begin"], "end": loop2["end"],
                               "endArrow": loop2["endArrow"],
                               "beginArrow": loop2["beginArrow"]}
        log("reopened loop glued %s begin %s end %s"
            % (loop2["gluedTo"], loop2["begin"], loop2["end"]))
        # detach-and-reattach test: move 继续调整方案 and see the line follow it,
        # which is what "the end is attached" means in Visio
        mover = None
        for i in range(1, page2.Shapes.Count + 1):
            sh = page2.Shapes.Item(i)
            if txt(sh, "prop.NodeId") == "t2n7":
                mover = sh
                break
        if mover is None:
            rec["notes"].append("t2n7 not found by NodeId on the copy")
        else:
            px, py = num(mover, "PinX"), num(mover, "PinY")
            tail_before = find_loop(page2)["begin"]
            mover.Cells("PinX").ResultIU = px + 0.5
            mover.Cells("PinY").ResultIU = py + 0.3
            tail_after = find_loop(page2)["begin"]
            moved = (abs(tail_after[0] - tail_before[0]) > 0.05
                     or abs(tail_after[1] - tail_before[1]) > 0.05)
            rec["dragTest"] = {"boxPinBefore": [px, py],
                               "tailBefore": list(tail_before),
                               "tailAfter": list(tail_after),
                               "followed": moved}
            log("drag test: tail %s -> %s after moving the box (+0.5,+0.3) => %s"
                % (tail_before, tail_after, "follows" if moved else "STAYED"))
            if not moved:
                rec.setdefault("findings", []).append(
                    "the connector tail did not follow 继续调整方案 - the end is not "
                    "glued even though it is in the right place")
            mover.Cells("PinX").ResultIU = px
            mover.Cells("PinY").ResultIU = py
            tail_back = find_loop(page2)["begin"]
            rec["dragTest"]["tailAfterUndo"] = list(tail_back)
            head = find_loop(page2)["end"]
            if head is None or abs(head[0] - LOOP["head"][0]) > 0.03 \
                    or abs(head[1] - LOOP["head"][1]) > 0.03:
                rec.setdefault("findings", []).append(
                    "after putting the box back the head reads %s, expected %s"
                    % (head, LOOP["head"]))
    doc2.Close()
    app.Quit()
    app = None
    rec["copyDigest"] = copy_sha[:16]
except Exception as exc:
    rec.setdefault("findings", []).append("%s: %s" % (type(exc).__name__, exc))
    log("FAILED %s: %s" % (type(exc).__name__, str(exc)[:200]))
finally:
    if app is not None:
        try:
            app.Quit()
        except Exception:
            pass
    os.chmod(VSDX, 0o644)

after = sha(VSDX)
rec["digestBefore"] = before[:16]
rec["digestAfter"] = after[:16]
rec["sourceUnchanged"] = before == after
if not rec["sourceUnchanged"]:
    rec.setdefault("findings", []).append("the round trip rewrote the delivered "
                                         "drawing - hard failure")
json.dump(rec, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
bad = rec.get("findings") or []
log("ROUND TRIP %s (%d findings)" % ("OK" if not bad else "FAILED", len(bad)))
for b in bad:
    log("   %s" % b[:200])
sys.exit(0 if not bad else 1)
