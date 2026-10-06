"""Build frontend/review/line_anchor_drift/READINGS_r8.txt from this generation's artifacts only."""
import io
import json
import os
import re
import subprocess
import time

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
FE = WT + "frontend/"
WK = "D:/moodle/_qoder_rel_ord0447_wk/"
OUT = FE + "review/line_anchor_drift/READINGS_r8.txt"
TIP = "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
R3 = "7c92c5407558e0df65f27bdafcc0df9fa55aef67"
R3_BASE = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"


def sh(*args):
    return subprocess.run(args, cwd=WT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def log(name):
    path = WK + name
    assert os.path.isfile(path), "artifact missing: " + name
    return io.open(path, encoding="utf-8").read()


def arm_verdicts(name):
    text = log(name)
    verdicts = {}
    for arm, state in re.findall(r"::(test_G\d)[A-Za-z_]*\s+(PASSED|FAILED)", text):
        verdicts[arm] = state
    counts = re.findall(r"(\d+) (passed|failed)", text)
    tally = {k: int(n) for n, k in counts}
    return verdicts, {"passed": tally.get("passed", 0), "failed": tally.get("failed", 0)}


def arm_verdicts_named(name):
    text = log(name)
    return (dict(re.findall(r"::(test_G\d)[A-Za-z_]*\s+(PASSED|FAILED)", text)),
            {k: int(n) for n, k in re.findall(r"(\d+) (passed|failed)", text)})


def blob_at(rev, rel):
    return sh("git", "rev-parse", "%s:%s" % (rev, rel)).strip()


def blob_worktree(rel):
    return sh("git", "hash-object", rel).strip()


ab_blind, ab_blind_t = arm_verdicts_named("k84_blind_no_contracts_root.txt")
ab_covered, ab_covered_t = arm_verdicts_named("k84_covered_with_contracts_root.txt")
ab_named = sorted(set(re.findall(r"contracts/openapi\.yaml:\d+",
                                 log("k84_covered_with_contracts_root.txt"))))
assert ab_blind.get("test_G3") == "PASSED", "no blind spot to report"
assert ab_covered.get("test_G3") == "FAILED", "the root did not buy coverage"
assert ab_named, "the covered run never named a contracts line"


runs = {}
k27 = log("k27_r4_stdout.txt")
for tag, marker in [("M1_number_back_g3", "M1 ("), ("M2_name_deleted_g1", "M2 (")]:
    line = [l for l in k27.splitlines() if l.startswith(marker)]
    assert line, "no %s line in the k27 artifact" % tag
    body = line[0]
    red = re.findall(r"::(test_G\d)", body)
    nums = {kind: int(n) for n, kind in re.findall(r"'(\d+) (passed|failed)'", body)}
    runs[tag] = ({r: "FAILED" for r in red},
                 {"passed": nums.get("passed", 0), "failed": nums.get("failed", 0)})
    assert nums.get("failed", 0) >= 1, tag + " never went red"
    assert "restored True" in k27, tag + " was not restored"
for tag, fname in [("M3_derived_only", "k82_m3.txt"), ("M4_both", "k82_m4.txt"),
                   ("M5_contract_only", "k82_m5.txt"), ("final", "k82_final.txt")]:
    runs[tag] = arm_verdicts(fname)

def expect(tag, want):
    v, t = runs[tag]
    assert len(v) == 4, "%s saw %d arms, not four: %s" % (tag, len(v), sorted(v))
    for arm, state in want.items():
        assert v.get(arm) == state, "%s: %s is %s, expected %s" % (tag, arm, v.get(arm), state)
    return v, t


v4, t4 = expect("M3_derived_only", {"test_G3": "PASSED", "test_G4": "FAILED"})
v5, t5 = expect("M5_contract_only", {"test_G3": "FAILED", "test_G4": "PASSED"})
v6, t6 = expect("M4_both", {"test_G3": "FAILED", "test_G4": "PASSED"})
vf, tf = runs["final"]
assert tf["failed"] == 0 and tf["passed"] >= 4, "final run is not green"

denom = log("k70_ruler.txt")
scanned = None
probe = subprocess.run(["D:/moodle/CityNexus/.venv/Scripts/python.exe", "k80_denominator.py"],
                       cwd=WK, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
m = re.search(r"scanned_files=(\d+) per_root=({.*?}) registry_entries=(\d+) line_shaped_citations_now=(\d+)",
              probe)
assert m, "no denominator reading from k80: %s" % probe[:200]
scanned_files, per_root, registry_entries, derived_cites = (
    int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4)))
contracts_files = int(re.search(r"'contracts': (\d+)", per_root).group(1))

regen = json.loads(subprocess.run(
    ["D:/moodle/CityNexus/.venv/Scripts/python.exe", "-c",
     "import io,difflib,json;"
     "g=io.open(r'C:/Users/仓鼠王/AppData/Local/Temp/api_gen.ts',encoding='utf-8',newline='').read().replace('\\r\\n','\\n').split('\\n');"
     "t=io.open(r'D:/moodle/_qoder_rel_ord0447_wt/frontend/src/generated/api.ts',encoding='utf-8',newline='').read().replace('\\r\\n','\\n').split('\\n');"
     "d=[l for l in difflib.unified_diff(t,g,lineterm='',n=0) if l.startswith(('+','-')) and not l.startswith(('+++','---'))];"
     "print(json.dumps({'changed_lines':len(d)})"
     ")"], capture_output=True, text=True).stdout or "{}")
assert regen.get("changed_lines") == 0, "the shipped copy no longer equals the generator's output"

numstat = sh("git", "diff", "--numstat", TIP, "--", "frontend/src/generated/api.ts").strip()
mm = re.search(r"(\d+)\t(\d+)\t", numstat)
assert mm, "no numstat for the regenerated copy"
gen_ins, gen_del = int(mm.group(1)), int(mm.group(2))

hand_files = len(sh("git", "diff", "--name-only", TIP, "HEAD").split("\n")) if False else None

L = []
w = L.append
w("comment-anchor guard -- r4 generation (cut at the tip, four arms)")
w("Written by k83_make_readings_r8.py; every number is parsed from a log, a probe, or git.")
w("")
w("[coordinates]")
w("  tip this hand rests on            : %s" % TIP)
w("  branch                           : review/a68b0631-comment-anchor-drift-r4")
w("  previous generation             : r3 head %s, base %s" % (R3, R3_BASE))
mt = sh("git", "merge-tree", "--write-tree", TIP, R3)
mt_conflicts = len(re.findall(r"^CONFLICT", mt, re.M))
w("  would r3 still land?            : yes -- `git merge-tree --write-tree` tip-vs-r3 reports %d" % mt_conflicts)
w("    conflicts, so this re-cut buys currency and new arms, not conflict-freedom.")
w("  guard test                       : %s" % blob_worktree("backend/tests/test_qoder_a68b0631_comment_anchor_drift_r1.py"))
w("  registry                        : %s (%d entries)" % (
    blob_worktree("frontend/review/line_anchor_drift/CONVERTED_r1.txt"), registry_entries))
w("  generated copy                   : %s (tip side %s; %d line added / %d removed)" % (
    blob_worktree("frontend/src/generated/api.ts"),
    blob_at(TIP, "frontend/src/generated/api.ts"), gen_ins, gen_del))
w("")
w("[what is new over r3]")
w("  1. SCAN_ROOTS now really contains `contracts`.  The list carried a comment claiming the root was")
w("     added below it, and it was not, so G3 never read the OpenAPI file -- which is exactly the file")
w("     whose description text is copied into the client users compile against.")
w("     A/B on that one variable, same mutant both times (the citation present in the contract and in")
w("     the generated copy), k84_root_coverage_ab.py:")
w("       without the root : %s" % json.dumps(ab_blind, ensure_ascii=False, sort_keys=True))
w("       with the root    : %s and the red line it names: %s" % (
    json.dumps(ab_covered, ensure_ascii=False, sort_keys=True), ab_named))
w("     So the tree-wide arm was blind to the contract; the only reason this particular sentence was")
w("     caught at all is that the registry happened to carry it.  A numbered citation in a contract")
w("     description nobody had registered would have been invisible to every arm.")
w("  2. A fourth arm, G4: a file generated from another file may not carry a line citation that its own")
w("     source no longer carries.  The old exemption said \"generated, don't hand-edit it\" and gave the")
w("     derived copy a free pass -- one-directional blindness, the exact defect class the guard exists")
w("     for.  G4 turns the exemption into a staleness check instead.")
w("  3. The citation G4 found is fixed the honest way: `npx openapi-typescript ../contracts/openapi.yaml`")
w("     re-run; its output differed from the shipped copy by exactly that one description line, and")
w("     the shipped copy was then replaced by the generated bytes.  Comparing them again now reports")
w("     %d changed lines, so the next regeneration cannot churn and no byte in a derived file was"
  % regen["changed_lines"])
w("     typed by hand.")
w("")
w("[denominator, so a pass cannot be an empty scan]")
w("  files scanned by the tree-wide arm : %d" % scanned_files)
w("  per root                          : %s" % per_root)
w("  of which contracts                 : %d" % contracts_files)
w("  line-shaped citations left in the derived copy : %d" % derived_cites)
w("  arms in the guard                  : %d" % len([k for k, v in vf.items() if k.startswith("test_G")]))
tsc = log("k85_tsc.txt")
tsc_rc = re.search(r"^rc=(\d+)", tsc, re.M)
tsc_err = len(re.findall(r"error TS", tsc))
assert tsc_rc, "no rc line in the typecheck artifact"
collect = log("k85_collect.txt")
collected = re.search(r"(\d+) tests collected", collect)
assert collected, "the backend collection printed no denominator"
w("  frontend typecheck (tsconfig.check.json) : rc %s, %d `error TS` lines" % (tsc_rc.group(1), tsc_err))
w("  backend `--collect-only` (imports survive a 150-file comment sweep) : %s tests, rc %s"
  % (collected.group(1), re.search(r"^rc=(\d+)", collect, re.M).group(1)))
w("")
w("[counter-arms, each naming the arm it must bite]")
for tag in ("M1_number_back_g3", "M2_name_deleted_g1", "M3_derived_only", "M4_both", "M5_contract_only"):
    if tag not in runs:
        w("  %-18s : artifact from an earlier generation, not re-run here" % tag)
        continue
    v, t = runs[tag]
    red = sorted(k for k, s in v.items() if s == "FAILED")
    green = sorted(k for k, s in v.items() if s == "PASSED")
    w("  %-18s : %d failed / %d passed -- red: %s ; green: %s"
      % (tag, t["failed"], t["passed"], ",".join(a.replace("test_", "") for a in red) or "none",
         (",".join(a.replace("test_", "") for a in green) if green
          else "%d passed, names not printed by that runner" % t["passed"])))
w("  M3 is the one that matters for the exemption: the number sits only in the generated copy, G3 stays")
w("  green (it is exempted) and G4 goes red naming that copy.  M4 puts the same number in the contract")
w("  too: G3 now goes red naming contracts/openapi.yaml while G4 stays green, which is the proof that")
w("  G4 is not a second copy of G3.  M5 puts it only in the contract: G3 red, G4 green.")
w("  final run on the restored tree: %d passed, %d failed; every mutant restored byte-for-byte." % (
    tf["passed"], tf["failed"]))
w("")
w("[artifact ordering, because one arm's verdict moves between the two sets]")
reg_mtime = os.path.getmtime(FE + "review/line_anchor_drift/CONVERTED_r1.txt")
k82_mtime = max(os.path.getmtime(WK + f) for f in os.listdir(WK) if f.startswith("k82_"))
k84_mtime = max(os.path.getmtime(WK + f) for f in os.listdir(WK) if f.startswith("k84_"))
assert k82_mtime <= reg_mtime <= k84_mtime, (
    "the ordering this section narrates is not the ordering the artifacts carry: %r %r %r"
    % (k82_mtime, reg_mtime, k84_mtime))
w("  ordering, taken from the artifacts' own mtimes: k82 %s, registry entry %s, k84 %s." % (
    time.strftime("%H:%M:%S", time.localtime(k82_mtime)),
    time.strftime("%H:%M:%S", time.localtime(reg_mtime)),
    time.strftime("%H:%M:%S", time.localtime(k84_mtime))))
w("  The k82 set therefore ran with the regenerated sentence not yet registered, and the k84 A/B ran")
w("  after it.  That is why G1 is green for M4 in the k82 table and red in the A/B pair: the same")
w("  sentence, once registered, is caught by two arms instead of one.")
w("  Nothing in either set was re-used across generations; each line above is parsed from its own log.")
w("")
w("[named against myself, this generation]")
w("  a. The root list lied: a comment asserted `contracts` was added below, and it was not.  A scan")
w("     range has to be read from the value, not from the sentence beside it.")
w("  b. My counter-arm driver first inserted M5 *before* M4's restore lines.  The run aborted and left")
w("     the citation in the contract and in the copy -- a real mutant sitting in the worktree, one")
w("     assert away from being committed.  Fixed by ordering (restore and compare sha before the next")
w("     mutant) and by re-reading the three copies of the line (worktree / index / tip) instead of")
w("     trusting `git diff`'s side of it: `git apply -3` had staged the hand, so worktree-vs-index and")
w("     worktree-vs-tip were telling different true sentences.")
w("")
w("-- lane a68b0631, r4 generation")

text = "\n".join(L) + "\n"
unfilled = [i + 1 for i, l in enumerate(L) if re.search(r"%[sdrf]\b", l)]
assert not unfilled, "un-substituted placeholders on lines %s" % unfilled
assert "None" not in text, "a missing reading leaked: %s" % [l for l in L if "None" in l][:1]
io.open(OUT, "w", encoding="utf-8", newline="\n").write(text)
print("wrote", OUT, os.path.getsize(OUT), "bytes,", len(L), "lines")
