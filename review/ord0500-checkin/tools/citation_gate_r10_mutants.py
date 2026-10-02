"""ORD-0500 r10: prove the citation gate reddens on MY citations and stays out of everyone else's.

Arms, each editing a COPY under `scratch_cit_r9/`, judged against the real tracked path list with the
real blame taken from `wt22` (a scratch directory has no history, and the copied bytes are identical, so
blame from the worktree is the correct authority for the copy):

  C1  unmutated copy              -- control; not GREEN means the replica is wrong and nothing below
                                     would mean anything.
  M1  cited line beyond the file  -- ordinary generation drift.
  M2  cited line is blank         -- a number that shows a reader nothing.
  M3  cited file absent           -- the named path resolves to nothing.
  M4  wrong but in range          -- THE defect this order was re-cut three times for: the line exists,
                                     is not blank, and no longer says what the sentence claims.  A
                                     purely mechanical gate cannot see it, which is why the pins exist.
  C2  revert                      -- back to GREEN.
  M5  foreign line broken         -- a citation written by another order's commit must NOT be able to
                                     drive my verdict, even when it is genuinely broken.
  M6  same line, authorship mine  -- the direction that makes M5 mean something: claim that commit as
                                     ours and the identical mutation reddens.
  C3  foreign line restored       -- back to GREEN.

`wt22` is never written.  The run ends by comparing every copy's bytes with the worktree and by reading
the worktree's own status.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import citation_gate_r9 as G

LANE, WT, SCR = G.LANE, G.WT, os.path.join(G.LANE, "scratch_cit_r9")
TEST = "backend/tests/test_qoder_ord0500_journey_refusal.py"
MAIN = "backend/app/main.py"
NL = chr(10)


def sh(args, cwd=WT):
    p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def read_root(root, rel):
    return open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()


def cited_targets(live, sources):
    """Paths the scanned files cite, so the scratch tree carries what the gate will want to open."""
    want = set()
    for f in sources:
        if not os.path.exists(os.path.join(WT, f)):
            continue
        for m in G.PATH_CIT.finditer(read_root(WT, f)):
            r, _ = G.resolve(m.group(1), live, WT)
            if r:
                want.add(r)
    return sorted(want)


def build_scratch(live, sources):
    if os.path.isdir(SCR):
        shutil.rmtree(SCR)
    files = sorted(set(sources) | set(cited_targets(live, sources)) | set(G.OWNED))
    for rel in files:
        src = os.path.join(WT, rel)
        if not os.path.exists(src):
            continue
        dst = os.path.join(SCR, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    return files


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def patch(rel, old, new):
    """Swap one whole citation for another, literal for literal."""
    p = os.path.join(SCR, rel)
    s = read_root(SCR, rel)
    if old not in s:
        raise SystemExit("ABORT_MUTANT_ANCHOR %s -- %r is not in the copy, so this mutant would not "
                         "have moved anything" % (rel, old[:48]))
    open(p, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1))


def rewrite_number(rel, line_no, digits, newnum):
    """Move ONE cited number by slicing.  A regex replacement is how an earlier version of this driver
    ate the path around the number it was supposed to move, and the mutant then proved nothing."""
    p = os.path.join(SCR, rel)
    lines = read_root(SCR, rel).splitlines()
    line = lines[line_no - 1]
    hits = [m for m in re.finditer(r":(\d+)", line) if m.group(1) == str(digits)]
    if not hits:
        raise SystemExit("ABORT_MUTANT_NUMBER %s line %d holds no cited %s" % (rel, line_no, digits))
    m = hits[-1]
    lines[line_no - 1] = line[:m.start() + 1] + str(newnum) + line[m.end():]
    open(p, "w", encoding="utf-8", newline="").write(NL.join(lines) + NL)
    # keep BOTH lines: a page that shows only the mutation cannot be checked against what it replaced
    return {"before": line.strip()[:120], "after": lines[line_no - 1].strip()[:120],
            "digits_moved": "%s->%s" % (digits, newnum)}


def main():
    rc, listed = sh(["git", "ls-files"])
    # the driver must not change what the worktree reports.  It may not be clean to begin with -- this
    # lane stages its own receipts between runs -- so the test is "unchanged by this run", not "empty".
    rc0, dirty_before = sh(["git", "status", "--porcelain"])
    live = [t for t in listed.splitlines() if t.strip() and not t.startswith("review/")]
    owned = G.lane_write_set(WT)
    mine = G.lane_commits(WT)
    owners = {f: G.blame_map(WT, f) for f in owned}
    copied = build_scratch(live, owned)
    mlines = len(read_root(SCR, MAIN).splitlines())
    blank = next(i + 1 for i, l in enumerate(read_root(SCR, MAIN).splitlines())
                 if i > 50 and not l.strip())

    def gate(mine_=None):
        return G.run_gate(root=SCR, live=live, owned=owned, owners=owners,
                          mine=mine if mine_ is None else mine_)

    runs = []
    control = gate()
    runs.append({"id": "C1_control_copy", "verdict": control["verdict"], "expect": "GREEN",
                 "citations_judged": control["citations_judged"],
                 "bite": control["verdict"] == "GREEN"})

    for mid, num, expect in (("M1_beyond_file", mlines + 1, "CITED_LINE_BEYOND_FILE"),
                             ("M2_blank_line", blank, "CITED_LINE_IS_BLANK"),
                             ("M4_wrong_but_in_range", 810, "CITED_LINE_CONTENT_MISMATCH")):
        patch(TEST, "backend/app/main.py:818", "backend/app/main.py:%d" % num)
        res = gate()
        hit = [r for r in res["red_detail"] if r["verdict"] == expect]
        runs.append({"id": mid, "verdict": res["verdict"], "expect": expect,
                     "citation_written": "backend/app/main.py:%d" % num, "class_fired": bool(hit),
                     "co_firing": sorted({r["verdict"] for r in res["red_detail"]}),
                     "bite": res["verdict"] == "RED" and bool(hit)})
        patch(TEST, "backend/app/main.py:%d" % num, "backend/app/main.py:818")

    # M3 in its own shape: the path named stops resolving, the number stays fine
    patch(TEST, "(`backend/app/main.py:818`)", "(`backend/app/nowhere_gate_r9.py:818`)")
    res3 = gate()
    hit3 = [r for r in res3["red_detail"] if r["verdict"] == "CITED_FILE_ABSENT"]
    runs.append({"id": "M3_absent_file", "verdict": res3["verdict"], "expect": "CITED_FILE_ABSENT",
                 "citation_written": "`backend/app/nowhere_gate_r9.py:818`",
                 "class_fired": bool(hit3),
                 "co_firing": sorted({r["verdict"] for r in res3["red_detail"]}),
                 "bite": res3["verdict"] == "RED" and bool(hit3)})
    patch(TEST, "(`backend/app/nowhere_gate_r9.py:818`)", "(`backend/app/main.py:818`)")

    after = gate()
    runs.append({"id": "C2_after_revert", "verdict": after["verdict"], "expect": "GREEN",
                 "bite": after["verdict"] == "GREEN"})

    frow = next((r for r in after["rows"] if r["verdict"] == G.FOREIGN
                 and r.get("owner_commit") and r.get("mechanical_verdict") == "OK"
                 and r["cited_by"].split(":")[0] == MAIN), None)
    if frow is None:
        raise SystemExit("ABORT_NO_FOREIGN_CITATION the shared file carries no citation written by "
                         "another commit, so the ownership filter could not be tested")
    ln, fsha, fnum = int(frow["cited_by"].split(":")[1]), frow["owner_commit"], frow["line"]
    wrote = rewrite_number(MAIN, ln, fnum, mlines + 1)   # {"before","after","digits_moved"}
    res5 = gate()
    still = next((r for r in res5["rows"] if r["cited_by"] == frow["cited_by"]), {})
    runs.append({"id": "M5_foreign_line_not_judged", "verdict": res5["verdict"], "expect": "GREEN",
                 "citation_before": wrote["before"], "citation_after": wrote["after"],
                 "digits_moved": wrote["digits_moved"], "owner_commit": fsha,
                 "row_verdict": still.get("verdict"),
                 "row_mechanical_verdict": still.get("mechanical_verdict"),
                 "red_total": res5["red_total"],
                 "bite": (res5["verdict"] == "GREEN" and res5["red_total"] == 0
                          and still.get("verdict") == G.FOREIGN
                          and still.get("mechanical_verdict") == "CITED_LINE_BEYOND_FILE")})
    res6 = gate(mine_=set(list(mine) + [fsha]))
    hit6 = [r for r in res6["red_detail"] if r["verdict"] == "CITED_LINE_BEYOND_FILE"]
    runs.append({"id": "M6_same_line_claimed_mine", "verdict": res6["verdict"],
                 "expect": "CITED_LINE_BEYOND_FILE", "citation_before": wrote["before"],
                 "citation_after": wrote["after"], "digits_moved": wrote["digits_moved"],
                 "owner_claimed_as_mine": fsha, "class_fired": bool(hit6),
                 "bite": res6["verdict"] == "RED" and bool(hit6)})
    rewrite_number(MAIN, ln, mlines + 1, fnum)
    res7 = gate()
    runs.append({"id": "C3_after_foreign_revert", "verdict": res7["verdict"], "expect": "GREEN",
                 "bite": res7["verdict"] == "GREEN"})

    restored = {}
    for rel in copied:
        a, b = sha(os.path.join(WT, rel)), sha(os.path.join(SCR, rel))
        restored[rel] = {"wt": a, "scratch": b, "equal": a == b}
    rc, dirty = sh(["git", "status", "--porcelain"])
    unchanged = sorted(dirty.splitlines()) == sorted(dirty_before.splitlines())

    out = {"tool": os.environ.get("CITATION_MUT_TOOL") or "citation_gate_r10_mutants",
           "pairs_with_gate_receipt": os.environ.get("CITATION_GATE_OUT"),
           "gate_tree_tip": control.get("tip"), "gate_tree_branch": control.get("branch"),
           "took_local": G.datetime.now().astimezone().isoformat(timespec="seconds"),
           "scratch": SCR, "pairs_with_gate_receipt": os.environ.get("CITATION_GATE_OUT"),
           "files_scanned": owned, "lane_commits_in_set": len(mine),
           "files_copied": len(copied), "main_lines_in_scratch": mlines,
           "blank_line_used": blank, "control_verdict": control["verdict"],
           "after_revert_verdict": after["verdict"], "runs": runs,
           "every_arm_bit": all(r["bite"] for r in runs),
           "foreign_citation_used": {"cited_by": frow["cited_by"], "line": ln,
                                     "owner_commit": fsha, "was_citing": fnum},
           "wt22_dirty_lines_before": sorted(dirty_before.splitlines()),
           "wt22_dirty_lines_after": sorted(dirty.splitlines()),
           "wt22_worktree_unchanged_by_this_run": unchanged,
           "wt22_worktree_clean": dirty.strip() == "",
           "bytes_restored": restored,
           "all_bytes_restored": all(v["equal"] for v in restored.values())}
    out["green"] = bool(out["every_arm_bit"] and out["all_bytes_restored"] and unchanged)
    dest = os.path.join(LANE, "evidence", os.environ.get("CITATION_MUT_OUT")
                        or "citation_gate_r10_mutants.json")
    json.dump(out, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for r in runs:
        print("%-28s verdict=%-6s expect=%-28s bite=%s" % (
            r["id"], r["verdict"], str(r.get("expect"))[:28], r["bite"]))
    print("green=%s every_arm_bit=%s all_bytes_restored=%s wt22_unchanged=%s clean=%s copies=%d" % (
        out["green"], out["every_arm_bit"], out["all_bytes_restored"], unchanged,
        out["wt22_worktree_clean"], len(copied)))
    print("WROTE " + dest)
    return 0 if out["green"] else 3


if __name__ == "__main__":
    sys.exit(main())
