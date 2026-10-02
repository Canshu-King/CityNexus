"""ORD-0500 r16: run the emitter copy that lives INSIDE each published ref, and record what answers.

Why this exists: every hand here says "the tool is in the branch".  That sentence is worthless if the
copy in the branch cannot actually run -- and the r15 copy cannot: it asks the coordinates file for a
blob of `tools/r9_block.py`, which that file never listed, so it dies on an empty slot.  The lane copy
that produced the page was fine, which is exactly the trap: two files share a name and only one of them
is what the commander receives.

For each ref in this order's family that carries an emitter, this extracts the three files the emitter
imports, runs the copy with the generation names read out of the LANE's current evidence (so every ref
is measured against today's receipts at today's head, and a ref whose copy is simply older answers with
its own abort rather than with my guess), and stores the return code plus the last line printed.  A copy
that writes a page file gets that file put back exactly as it was -- a delivered sheet is evidence, and
this arm measures whether a tool runs, it does not publish anything.

`R10_SUB=1` stops the arm recursing once a future ref carries an emitter that runs this same arm.

Writes evidence/branch_emit_arm_<BRANCH_EMIT_OUT or r15>.json.
"""
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = os.path.join(LANE, "wt22")
REPO = r"D:/moodle/CityNexus"
RUN = os.path.join(LANE, "run")
EV = os.path.join(LANE, "evidence")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
FAMILY = "refs/heads/review/newlane-ord0500-phone-checkin-entry-"
NEED = ["r10_block.py", "r9_block.py", "reanchor_r8.py"]
NL = chr(10)


def sh(args, cwd=REPO):
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
    env["NO_PROXY"] = "*"
    p = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=300, env=env)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def refs_in_family():
    rc, out = sh(["ls-remote", "--refs", "origin"])
    if rc:
        raise SystemExit("ABORT_REF_DISCOVERY %s" % out[:200])
    found = [l.split()[1] for l in out.splitlines() if len(l.split()) == 2
             and l.split()[1].startswith(FAMILY)]
    if not found:
        raise SystemExit("ABORT_NO_REFS")
    return sorted(set(found), key=lambda r: int(re.search(r"(\d+)$", r).group(1)))


def newest_evidence(pattern):
    """The generation the page is being written against, read off the lane's own evidence -- not
    remembered, and not taken from the ref under test (that would measure the wrong thing)."""
    hits = sorted(glob.glob(os.path.join(EV, pattern)), key=os.path.getmtime)
    if not hits:
        raise SystemExit("ABORT_NO_EVIDENCE " + pattern)
    return os.path.basename(hits[-1])


def run_copy(rev, ref, names):
    scratch = os.path.join(LANE, "scratch_emit", ref.split("-")[-1])
    os.makedirs(scratch, exist_ok=True)
    for name in NEED:
        rc, src = sh(["show", "%s:review/ord0500-checkin/tools/%s" % (rev, name)], cwd=WT)
        if rc:
            return {"ref": ref.split("/")[-1], "commit": rev, "verdict": "NO_EMITTER_COPY",
                    "missing": name}
        open(os.path.join(scratch, name), "w", encoding="utf-8", newline=NL).write(src)
    env = dict(os.environ)
    env.update({"R10_GEN": names["gen"], "R10_REF_GEN": ref.split("-")[-1],
                "AUD_RECEIPT": names["audit"], "RECHECK_RECEIPT": names["recheck"],
                "ARM_RECEIPT": names["arm"], "R10_SUB": "1"})
    page = os.path.join(RUN, "%s_block_page.md" % names["gen"])
    before = open(page, "rb").read() if os.path.exists(page) else None
    p = subprocess.run([sys.executable, os.path.join(scratch, "r10_block.py")],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, env=env,
                       cwd=scratch)
    out = p.stdout.decode("utf-8", "replace")
    now = open(page, "rb").read() if os.path.exists(page) else None
    if before is None:
        wrote = now is not None
        if wrote:
            os.remove(page)                   # this arm's own by-product, not a reading
        restored = False
    else:
        wrote = now != before
        if now != before:
            open(page, "wb").write(before)     # a delivered sheet is evidence; put it back byte for byte
        restored = True
    lines = [l for l in out.strip().splitlines() if l.strip()]
    return {"ref": ref.split("/")[-1], "commit": rev,
            "verdict": "RUNS" if p.returncode == 0 else "ABORTS", "returncode": p.returncode,
            "last_line": (lines or [""])[-1][:220], "generation_named": names["gen"],
            "receipts_named": [names["gate"], names["audit"], names["recheck"]],
            "page_file_this_arm_wrote": wrote, "previous_page_restored": restored,
            "scratch": "scratch_emit/%s/" % ref.split("-")[-1]}


def main():
    rc, listed = sh(["ls-remote", "--refs", "origin", TIP_REF])
    tip = (listed.split() or [None])[0]
    if not tip:
        raise SystemExit("ABORT_NO_TIP " + listed[:160])
    gate = newest_evidence("citation_gate_r[0-9]*[0-9].json")   # not the *_mutants sibling
    gen = re.findall(r"r(\d+)", gate)[-1]
    names = {"gen": "r%s" % gen, "gate": gate,
             "audit": newest_evidence("citation_audit_r*.json"),
             "recheck": newest_evidence("day*_anchor_recheck_r*.json"),
             "arm": os.environ.get("BRANCH_EMIT_OUT") or "branch_emit_arm_r%s.json" % gen}
    rows = []
    # The ref being written right now cannot be measured by this arm: its copy is the one running the
    # page that quotes this receipt, and it would have to read a receipt that does not exist until it
    # finished.  It is proven a different way -- byte equality with the copy that ran.  Match on the
    # trailing generation NUMBER, because callers hand this over either as `r16` or as a full ref name.
    exclude_raw = os.environ.get("BRANCH_EMIT_EXCLUDE") or ""
    m_ex = re.search(r"(\d+)$", exclude_raw)
    exclude = "r%s" % m_ex.group(1) if m_ex else None
    for ref in refs_in_family():
        m_ref = re.search(r"(\d+)$", ref)
        if exclude and m_ref and "r%s" % m_ref.group(1) == exclude:
            continue
        rc, got = sh(["ls-remote", "--refs", "origin", ref])
        if rc or not got.split():
            rows.append({"ref": ref.split("/")[-1], "verdict": "ABSENT"})
            continue
        rev = got.split()[0]
        rc2, _ = sh(["cat-file", "-e", "%s:review/ord0500-checkin/tools/r10_block.py" % rev], cwd=WT)
        if rc2:
            rows.append({"ref": ref.split("/")[-1], "commit": rev, "verdict": "NO_EMITTER_IN_REF"})
            continue
        rows.append(run_copy(rev, ref, names))
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    out = {"tool": os.environ.get("BRANCH_EMIT_TOOL") or "branch_emit_arm_r%s" % gen,
           "took_local": datetime.now().astimezone().isoformat(timespec="seconds"),
           "tip": tip, "named_generation": names["gen"],
           "ref_excluded_and_proven_by_bytes": exclude or None, "receipts_named": [names["gate"],
                                                                            names["audit"],
                                                                            names["recheck"]],
           "refs": rows, "verdict_tally": tally}
    dest = os.path.join(EV, names["arm"])
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"tally": tally, "receipt": os.path.basename(dest), "tip": tip[:12],
                      "rows": [(r["ref"], r["verdict"], r.get("returncode"),
                                r.get("last_line", "")[:60]) for r in rows]},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
