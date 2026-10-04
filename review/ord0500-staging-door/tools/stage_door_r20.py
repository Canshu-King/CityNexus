"""The staging leg's own refusal door (ORD-0500, the sibling of the page door built for 裁①).

The page door refuses to WRITE A PAGE on red readings.  This one refuses to leave red readings in the
tree that the next commit would carry: the tool that performs the writes is the tool that judges them,
and on red it puts the bytes back the way it found them.  A rule that lives in a script which runs
after the writer is a promise; a rule inside the writer is a gate -- which is the shape this lane has
been asked for repeatedly (and which I violated once with `;` instead of `&&`).

What it judges is the receipt-derived subset of the page door's inventory, because those are the bytes
being written.  Remote-side checks (the ref head, the coordinate list, the emitter's own bytes) belong
to the page door and are named here as NOT_THIS_DOOR rather than quietly dropped.

Reading "absent" as "fine" is the one-directional-blindness defect this lane has been corrected for
twice, so a missing or unparseable receipt is a RED item, not a skipped one.
"""
import json
import os

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
ABORTS = "STAGING_READINGS_RED"

GATE = os.environ.get("CITATION_GATE_OUT") or "citation_gate_r19.json"
MUT = os.environ.get("CITATION_MUT_OUT") or "citation_gate_r19_mutants.json"
AUD = os.environ.get("CITATION_AUDIT_OUT") or "citation_audit_r19.json"
RECHECK = os.environ.get("RECHECK_OUT") or "day26_anchor_recheck_r19.json"
FMT = os.environ.get("FMTLINT_OUT") or "fmt_lint_r19.json"
REFDISC = os.environ.get("REFDISC_OUT") or "ref_discovery_arm_r19.json"
COLLECT = os.environ.get("COLLECT_OUT") or "pytest_collectonly_r19.json"

# fixed-name receipts: the same files the page cites, whichever generation last re-ran them
PYTEST = "pytest_r6.json"
ROWS = "checkin_copy_rows_r6.json"
ROWS_MUT = "checkin_copy_rows_mutants_r6.json"


def _load(rc_dir, name):
    """Return (ok, data, why).  A receipt the door cannot read is a finding, never a pass."""
    p = os.path.join(rc_dir, name)
    if not os.path.exists(p):
        return False, None, "MISSING_RECEIPT " + name
    try:
        return True, json.load(open(p, encoding="utf-8")), ""
    except Exception as exc:
        return False, None, "UNPARSEABLE_RECEIPT %s %s" % (name, str(exc)[:80])


def _arms(data):
    return {r.get("id"): r.get("verdict") for r in (data.get("runs") or [])}


# (name, receipt, predicate over that receipt) -- mirrors tools/r9_block.refuse_on_red's list, subset to
# what this leg writes; the page door keeps the whole eleven and cites this receipt for the division.
CHECKS = [
    ("引文闸判语", GATE, lambda d: d.get("verdict") == "GREEN",
     lambda d: d.get("verdict_tally")),
    ("引文闸反件全咬", MUT, lambda d: bool(d.get("every_arm_bit")) and bool(d.get("green")),
     lambda d: [(r.get("id"), r.get("bite")) for r in (d.get("runs") or [])]),
    ("换代复读无腐烂", RECHECK, lambda d: not (d.get("rot") or {}), lambda d: d.get("rot")),
    ("后端臂退出码", PYTEST, lambda d: d.get("exit") == 0,
     lambda d: (d.get("summary_lines") or [""])[-1:]),
    ("词汇闸判语", ROWS, lambda d: d.get("verdict") == "GREEN", lambda d: d.get("rows_checked")),
    ("词汇闸反件", ROWS_MUT, lambda d: bool(d.get("every_mutant_bit")),
     lambda d: d.get("control_verdict")),
    ("全线尺只判自己名下", AUD, lambda d: d.get("mechanically_red") == 0,
     lambda d: {"red": d.get("mechanically_red"), "declined": d.get("citations_declined")}),
    ("静态 arity 尺绿且自检咬下", FMT,
     lambda d: d.get("verdict") == "GREEN" and (d.get("selftest") or {}).get("verdict") == "PASS",
     lambda d: {"calls_checked": d.get("calls_checked"),
                "mismatched": len(d.get("mismatched") or []),
                "selftest": (d.get("selftest") or {}).get("verdict")}),
    ("枝清单臂三形咬下", REFDISC,
     lambda d: bool(d.get("every_arm_bit")) and _arms(d).get("M1_alternating_short_full") == "REFUSED"
     and _arms(d).get("M2_every_read_short") == "REFUSED"
     and _arms(d).get("C1_two_full_reads") == "RETURNED",
     lambda d: _arms(d)),
    ("收集尺退出码", COLLECT, lambda d: d.get("exit") == 0,
     lambda d: {"collected": d.get("collected"), "exit": d.get("exit")}),
]

NOT_THIS_DOOR = ["枝里那份发射器＝刚跑这页的这枚", "读数提交到枝尖只多了件", "枝清单两趟一致且含本枝（远端侧）"]


def judge(rc_dir):
    """(verdict, rows, red_names).  Reads the staged bytes only -- nothing under evidence/."""
    rows, red = [], []
    for name, receipt, ok_pred, detail in CHECKS:
        got, data, why = _load(rc_dir, receipt)
        if not got:
            rows.append({"check": name, "receipt": receipt, "verdict": "RED",
                         "reason": why, "detail": None})
            red.append(name)
            continue
        passed = bool(ok_pred(data))
        rows.append({"check": name, "receipt": receipt, "verdict": "GREEN" if passed else "RED",
                     "reason": "" if passed else "PREDICATE_FALSE",
                     "detail": detail(data) if not passed else None})
        if not passed:
            red.append(name)
    forced = os.environ.get("R20_FORCE_STAGING_RED") or ""
    if forced:
        for r in rows:
            if r["check"] == forced:
                r["verdict"] = "RED"
                r["reason"] = "FORCED_BY_ARM"
                r["injected"] = True
                if forced not in red:
                    red.append(forced)
    return ("GREEN" if not red else "RED"), rows, red


def snapshot(dest):
    """Every byte under the staging destination before this tool touches anything."""
    snap = {}
    for root, _, files in os.walk(dest):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, dest).replace("\\", "/")
            snap[rel] = open(p, "rb").read()
    return snap


def restore(dest, snap):
    """Put the tree back exactly: rewrite what changed, delete what this run created."""
    wrote, removed, mism = 0, 0, []
    now = set()
    for root, _, files in os.walk(dest):
        for f in files:
            now.add(os.path.relpath(os.path.join(root, f), dest).replace("\\", "/"))
    removed_names = []
    for rel in sorted(now - set(snap)):
        p = os.path.join(dest, rel.replace("/", os.sep))
        os.remove(p)
        removed += 1
        removed_names.append(rel)
    for rel, data in sorted(snap.items()):
        p = os.path.join(dest, rel.replace("/", os.sep))
        cur = open(p, "rb").read() if os.path.exists(p) else None
        if cur != data:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "wb").write(data)
            wrote += 1
        if open(p, "rb").read() != data:
            mism.append(rel)
    # a count with no inventory is the shape I have been told to stop publishing: name what was taken away
    return {"files_written_back": wrote, "files_removed": removed, "removed_paths": removed_names,
            "every_path_matches_the_snapshot": not mism, "mismatched": mism}


def refuse(gen, dest, snap, verdict, rows, red):
    """Red at this door means: nothing stays in the tree, and a named failure sheet is the only output."""
    back = restore(dest, snap)
    sheet = {"schema": "CNX_ORD0500_STAGING_DOOR_V1", "aborts": ABORTS, "gen": gen,
             "verdict": verdict, "failed": red, "checks_run": [r["check"] for r in rows],
             "not_this_door": NOT_THIS_DOOR, "rows": rows, "restore": back,
             "force_arm": os.environ.get("R20_FORCE_STAGING_RED") or ""}
    out = os.path.join(LANE, "run", "%s_STAGING_RED.json" % gen)
    json.dump(sheet, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if not back["every_path_matches_the_snapshot"]:
        raise SystemExit("ABORT_STAGING_ROLLBACK_INCOMPLETE %s -- refused red but could not put the "
                         "tree back, do NOT commit" % back["mismatched"])
    raise SystemExit("%s %s -- red items %s; tree restored (%s written back, %s removed); "
                     "failure sheet at %s" % (ABORTS, gen, "、".join(red),
                                              back["files_written_back"], back["files_removed"], out))
