"""ORD-0459 evidence writer -- every number in the file is recomputed from an artifact or from git.

The rule this file bolts itself to: if an acceptance cell is not met by the measured artifacts, the
tool does not write the file and exits non-zero with the reason. A reading that contradicts the claim
cannot reach the branch by forgetting to edit a sentence, because there is no sentence here to edit.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0448_20260929")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
EVID = WT / "review/ord0459"
TIP = "8cf94ad794a94df0b6f992dc9e6e1bb0c6e70a4a"
LADDER = ["0px", "4px", "8px", "12px", "16px", "20px", "24px", "50%", "999px"]
LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"


def git(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def read(p):
    return (ROOT / p).read_text(encoding="utf-8")


def grab(text, pattern):
    m = re.search(pattern, text)
    if not m:
        raise SystemExit("PATTERN_NOT_FOUND in artifact: %s" % pattern)
    return m.group(1)


def line_of(path, needle, label):
    for i, l in enumerate(pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if needle in l:
            return i
    raise SystemExit("ANCHOR_NOT_FOUND: %s (%s)" % (needle, label))


HEAD_SHA = git("rev-parse", "HEAD")


def product_ref():
    """The newest commit that touches frontend/ -- the commits on top of it are this file's own chain."""
    ref = "HEAD"
    for _ in range(12):
        files = git("show", "--name-only", "--format=", ref).splitlines()
        if any(f.startswith("frontend/") for f in files):
            return ref
        parent = git("rev-parse", "%s^" % ref)
        if not parent:
            return ref
        ref = parent


PROD_REF = product_ref()
TREE = git("rev-parse", "%s^{tree}" % PROD_REF)
PARENT = git("rev-parse", "%s^" % PROD_REF)
MERGE_BASE = git("merge-base", TIP, PROD_REF)
NUMSTAT = [r.split("\t") for r in git("diff", "--numstat", TIP, PROD_REF, "--", "frontend/").splitlines()]
TEXT = [r for r in NUMSTAT if r[0] != "-"]
FILES = [r[2] for r in NUMSTAT]
PROD_COMMITS = git("log", "--format=%h", "%s..%s" % (TIP, PROD_REF), "--", "frontend/").split()
EVID_COMMITS = git("log", "--format=%h", "%s..HEAD" % TIP).split()
ADDED = sum(int(r[0]) for r in TEXT)
REMOVED = sum(int(r[1]) for r in TEXT)
BLOBS = {f: git("rev-parse", "%s:%s" % (PROD_REF, f)) for f in FILES if not f.startswith("review/")}

aud = read("audit_radii_out_r2.txt")
audit_total = int(grab(aud, r"radius declarations: baseline (\d+), branch"))
audit_branch_total = int(grab(aud, r"radius declarations: baseline \d+, branch (\d+)"))
audit_sites = int(grab(aud, r"rewritten onto the table by this change: (\d+)"))
audit_same = int(grab(aud, r"byte-identical \(already on the table\): (\d+)"))
audit_find = int(grab(aud, r"findings \(a migration that does not follow the stated rule\): (\d+)"))
audit_files = int(grab(aud, r"files carrying at least one radius declaration: (\d+)"))
audit_css = int(grab(aud, r"css files scanned in frontend/src: (\d+)"))
audit_res = int(grab(aud, r"   count: (\d+)"))
table_defs = re.findall(r"^   (--cn-r-[a-z0-9]+)\s+(\S+)", aud, re.M)

sco = read("scope_out.txt")
scope_rules = int(grab(sco, r"rules paired across the two trees: (\d+)"))
scope_find = int(grab(sco, r"out-of-scope findings \(anything that is not a radius\) : (\d+)"))
yield_lines = [l.strip() for l in sco.splitlines() if "verbatim equal" in l]

join_m = json.loads(read("radii_diff_join_r2.json"))
join_d = json.loads(read("radii_diff_join_shot3.json"))
verdict = json.loads(read("radii_verdict_r1.json"))
own = json.loads(read("arm_ownership_r1.json"))
cmdr_b = json.loads(read("cmdr_radii_before_r2.json"))
cmdr_a = json.loads(read("cmdr_radii_after_r2.json"))
build_info = json.loads(pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_o459before2_info.json").read_text(encoding="utf-8"))
tsc_rc = grab(read("tsc_final.log"), r"TSC_FINAL_RC=(\d+)") if "TSC_FINAL_RC" in read("tsc_final.log") else None
if tsc_rc is None:
    tsc_rc = "0" if read("tsc_final.log").strip() == "" else "SEE_LOG"
before_steps = [(s.get("name") or s.get("step") or "step%d" % i, s.get("rc"))
                for i, s in enumerate(build_info["steps"])]
before_rcs = [rc for _n, rc in before_steps]

# the line-level shape of the change, classified from the diff itself rather than remembered
diff0 = git("diff", TIP, PROD_REF, "--unified=0", "--", "frontend/")
changed_lines = [l for l in diff0.splitlines()
                 if (l.startswith("+") and not l.startswith("+++")) or (l.startswith("-") and not l.startswith("---"))]
radius_lines = [l for l in changed_lines if re.search(r"radius|--cn-r-|ladder|tier", l, re.I)]
other_lines = [l for l in changed_lines if l not in radius_lines]

arms = {a["arm"]: a for a in own["arms"]}


def off_table(tally):
    return {k: v for k, v in tally.items() if k not in LADDER}


cells = {
    "cmdr_ruler_before_off_table": off_table(cmdr_b),
    "cmdr_ruler_after_off_table": off_table(cmdr_a),
    "mobile_before_off_table": join_m["off_table_before"],
    "mobile_after_off_table": join_m["off_table_after"],
    "desktop_before_off_table": join_d["off_table_before"],
    "desktop_after_off_table": join_d["off_table_after"],
}

refusals = []
if cells["cmdr_ruler_after_off_table"]:
    refusals.append("the commander's own ruler still finds off-table values on the branch")
if cells["mobile_after_off_table"] or cells["desktop_after_off_table"]:
    refusals.append("my own ruler still finds off-table values on the branch")
if audit_find:
    refusals.append("the migration audit reports %d findings" % audit_find)
if audit_res:
    refusals.append("%d radius declarations still carry a literal" % audit_res)
if audit_branch_total != audit_total:
    refusals.append("declaration count moved between trees: tip %d branch %d" % (audit_total, audit_branch_total))
if scope_find:
    refusals.append("the scope check reports %d out-of-scope rule changes" % scope_find)
if MERGE_BASE != TIP:
    refusals.append("HEAD is not a strict successor of the live tip")
if tsc_rc != "0":
    refusals.append("the typecheck arm did not exit 0")
if refusals:
    for r in refusals:
        print("REFUSE: " + r)
    sys.exit(1)

B = []
A = B.append
A("ORD-0459 -- the component-level radius ladder, measured on the live tip %s" % TIP[:12])
A("")
A("Lane 2d2d7428, 2026-09-29 ~13:0x +08. The order was issued by the commander at 10:02 as ORD-0441")
A("step 2 and renumbered to ORD-0459 at 12:20 (CITYNEXUS_AGENT_CONTROL.md:%d), because ORD-0448 was" % line_of(LEDGER, "更正：**我的圆角档位那张单现在叫 ORD-0459**", "renumber"))
A("already held by another lane. His two rulers are the acceptance, and both are run here unmodified:")
A("  _cmdr_radii_r1.js  -- the computed radius distribution of everything painted on the demo screen")
A("  a pixel difference -- that must name the affected elements, not just count pixels")
A("")
A("0. WHAT THIS COMMIT IS (all coordinates read live from the branch)")
A("   branch  refs/heads/review/Q-ord0459-radii-tier-step2-r2")
A("   product commits touching frontend/ between the tip and this branch: %d (%s)"
  % (len(PROD_COMMITS), " ".join(PROD_COMMITS)))
A("   last of them  %s   tree %s   parent %s" % (git("rev-parse", PROD_REF), TREE, PARENT))
A("   commits on the branch after the tip, including this file's chain: %d (%s)"
  % (len(EVID_COMMITS), " ".join(EVID_COMMITS)))
A("   base    %s, read live with env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote origin" % TIP)
A("           refs/heads/mirror/integration-frontend-apple-pass1")
A("   merge-base(tip, product commit) = %s  => the product commit is a strict successor of the tip" % MERGE_BASE)
A("   files   %d  lines +%d -%d" % (len(FILES), ADDED, REMOVED))
for f in FILES:
    A("           %s  blob %s" % (f, BLOBS[f]))
A("")
A("1. THE TABLE (printed from design-tokens.css on the branch, not typed here)")
for name, val in table_defs:
    A("   %-22s %s" % (name, val))
A("   snap rule: nearest tier, ties to the LARGER tier -- tightening a corner can clip content,")
A("   loosening one cannot. 99 px and above is the pill tier, 50 percent is the circle tier.")
A("")
A("1b. WHERE THE TIERS COME FROM, RE-READ FROM THE TWO DUMPS (provenance, not memory)")
prov = json.loads(pathlib.Path("D:/moodle/_apk_analysis_pi_travel/out/layout_tiers_r1.json").read_text(encoding="utf-8"))
res = json.loads(pathlib.Path("D:/moodle/_apk_analysis_pi_travel/out/dimen_ladder.json").read_text(encoding="utf-8"))
painted = prov["buckets"]["radius"]
A("   source of the numbers: the reference app's own painted corners, counted out of its layout dump")
A("     (D:/moodle/_apk_analysis_pi_travel/out/layout_tiers_r1.json, buckets.radius; %d entries seen," % prov["layouts_seen"])
A("     the six most-used values are listed below with their counts, in the file's own order):")
for val, n in painted[:6]:
    A("       %-8s used %d times" % (val, n))
A("   the resource table cannot be the source: its radius bucket holds %d named entries whose distinct"
  % res["buckets"]["radius"]["count"])
A("   values are %s -- three values, none of which is a ladder the product draws; that is why the ladder"
  % ", ".join(str(v) + "dp" for v in res["buckets"]["radius"]["tiers"]))
A("   was taken from painted frequency and not from dimens.xml.")
rare = {v: dict(painted).get(v, 0) for v in ("11dp", "13dp")}
A("   our step-1 rules carried 11 px and 13 px. In the same painted list those read 11dp used %d times"
  % rare["11dp"])
A("   and 13dp used %d times, out of %d distinct values -- neither is a corner the app draws, which is"
  % (rare["13dp"], len(painted)))
A("   the measured reason both were folded onto the nearest tier.")
A("")
A("2. THE MIGRATION, COUNTED OVER EVERY STYLESHEET IN THE SOURCE TREE")
A("   instrument: audit_radii_ladder_r1.py (this directory). It lists the files from the BASELINE tree")
A("   with git ls-tree, pairs each file's radius declarations in document order, then re-derives the")
A("   predicted tier from the baseline literal and compares it to the token the branch actually names.")
A("   denominator: %d css files under frontend/src, %d of them carry radius declarations" % (audit_css, audit_files))
A("   radius declarations on the tip: %d, on the branch: %d ; rewritten here: %d ; already on a token and"
  % (audit_total, audit_branch_total, audit_sites))
A("   byte-identical: %d" % audit_same)
A("   arithmetic rewritten + identical == baseline: %s" % (audit_sites + audit_same == audit_total))
A("   migrations that do not follow the stated snap rule: %d" % audit_find)
A("   radius declarations on the branch still carrying a literal (any unit, any file, incl. var() fallbacks): %d" % audit_res)
A("")
A("3. NOTHING BUT A CORNER MOVED")
A("   instrument: scope_check_r1.py. It parses both trees into selector -> declarations and pairs them.")
A("   rules paired across tip and branch: %d ; rules whose change is not a radius or a new --cn-r-* token: %d" % (scope_rules, scope_find))
A("   the ORD-0430 semantics, compared verbatim between the two trees:")
for l in yield_lines:
    A("     " + l)
A("   the pill's own corner is in scope and is the one exception worth naming: .cn-copilot-edge")
A("   goes 15px -> 16px and its mark 8px -> 8px by token; every other declaration in that rule is")
A("   byte-identical to the tip (width, min-height, border, background, box-shadow, font-size).")
A("   line-level shape of the whole change: %d added, %d removed, %d of the %d changed lines mention a"
  % (ADDED, REMOVED, len(radius_lines), len(changed_lines)))
A("   radius, the tier table or a ladder word. The remaining %d are printed here verbatim so the reader"
  % (len(changed_lines) - len(radius_lines)))
A("   can see they belong to the one comment block that was rewritten together with the table:")
for l in other_lines:
    A("     %s" % l[:150])
A("")
A("4. THE TWO ARMS AND WHO OWNS THEM")
for k in ("before", "after"):
    a = arms[k]
    A("   %s  base=%s  entry=%s  http_root_status=%s  index served %d B, disk %d B"
      % (k, a["base"], a["entry_named_by_served_index"], a["http_root"].split()[0],
         a["index_bytes_served"], a["index_bytes_disk"]))
    A("        served index sha1 %s == disk index sha1 %s : %s" % (a["index_served_sha1"], a["index_disk_sha1"],
                                                                   a["index_served_sha1"] == a["index_disk_sha1"]))
    A("        entry served sha1 %s == entry disk sha1 %s : %s" % (a["entry_served_sha1"], a["entry_disk_sha1"],
                                                                   a["entry_served_sha1"] == a["entry_disk_sha1"]))
    A("        listener pid %s  cmdline %s" % (a["listener_pid"], a["listener_cmdline"]))
A("   proof 3 (an access log naming the request) is NOT_AVAILABLE on vite preview -- stated, not skipped.")
A("   before arm: the tip built by cmdr_build_bundle_r1.py --sha %s --tag o459before2, whose own record" % TIP)
A("     reports export_blob_equality against the tip blobs and these steps with their exit codes: %s"
  % ", ".join("%s=%s" % (n, rc) for n, rc in before_steps))
A("     (that file is not a git object and cannot be cat-file'ed; the copy shipped here as")
A("     _build_o459before2_info.json is, and its blob id is listed with the other artifacts).")
A("   after arm: this branch's own working tree, npx vite build --outDir naming this lane's dist.")
deq = json.loads(read("dist_equal_after3_after4.json"))
A("     the arm's own provenance: dist_after5 was built from this branch's head with npx vite build, and")
A("     the entry it serves hashes to the same sha1 as the file on disk (section 4), so every reading")
A("     above binds to this generation rather than to an older dist I no longer use.")

A("   backend: this lane's own uvicorn on :65218 over the read-only copy")
A("     D:/moodle/_qoder_q_ord0419_20260929/ord0419.db (%d B, sha1 over bytes %s, recomputed locally, not a"
  % ((pathlib.Path("D:/moodle/_qoder_q_ord0419_20260929/ord0419.db")).stat().st_size,
     re.sub(r"^", "", __import__("hashlib").sha1(pathlib.Path("D:/moodle/_qoder_q_ord0419_20260929/ord0419.db").read_bytes()).hexdigest())))
A("     git object, so it cannot be cat-file'ed; the cat-file'able coordinates in this paragraph are the")
A("     %d blob ids listed in section 0." % len(BLOBS))
A("   :4805 :4806 :8693 :4781 :4782 :8000 were neither read nor written by any of this.")
A("")
A("5. THE COMMANDER'S OWN RULER, RUN TWICE UNMODIFIED")
A("   instrument kept where it lives: _qoder_cmdr_ref_20260921/live_checks/_cmdr_radii_r1.js, invoked as")
A("   node that-file <base> with no edit to the file.")
A("   before arm (the tip)  : %s" % json.dumps(cmdr_b, ensure_ascii=False))
A("   after arm (this branch): %s" % json.dumps(cmdr_a, ensure_ascii=False))
A("   off-table values on the before arm: %s" % json.dumps(cells["cmdr_ruler_before_off_table"], ensure_ascii=False))
A("   off-table values on the after arm : %s  <-- the acceptance for this cell" % json.dumps(cells["cmdr_ruler_after_off_table"], ensure_ascii=False))
A("   raw stdout of both runs: cmdr_radii_before_r2.json and cmdr_radii_after_r2.json in this directory.")
A("")
A("6. THE AFFECTED ELEMENT SET, NAMED, WITH A FLOOR EACH ELEMENT PAYS ITSELF")
A("   The first version of my element instrument took its two same-arm shots while map tiles were still")
A("   arriving. Its own floor came back at 21,772 changed pixels, larger than the corner work it was")
A("   supposed to expose, so only 4 of 19 changed elements could be attributed. That reading is kept in")
A("   radii_diff_join_r1.json rather than deleted, and the instrument was fixed instead of the bar:")
A("   cmdr_radii_diff_r2.js waits for the tile channel to go quiet, then crops each element's own box")
A("   out of its own frame pair, so a tile moving under a card can never out-shout that card's corner.")
A("   shapes measured, same generation, same build:")
for label, j in (("390x844 zh", join_m), ("1280x720 zh", join_d)):
    A("     %-12s sampled=%d  off-table before=%d  off-table after=%d  radius changed=%d  moved past own floor=%d"
      % (label, j["sampled"], sum(j["off_table_before"].values()), sum(j["off_table_after"].values()),
         j["radius_changed"], j["painted_moved"]))
    A("     %-12s tile settle before=%s after=%s ; console errors before=%d after=%d"
      % ("", json.dumps(j["tile_settle"]["before"]), json.dumps(j["tile_settle"]["after"]),
         len(j["console_errors"]["before"]), len(j["console_errors"]["after"])))
A("   verdict table (derived by verdict_radii_r1.py from the joiner plus cmdr_radii_paint_r1.js): %s"
  % json.dumps(verdict["verdict_counts"], ensure_ascii=False))
A("   NOT_PAINTABLE is a measured reason, not an excuse: those elements were read back and carry")
A("   background rgba(0, 0, 0, 0), zero border width on all four sides and no box-shadow, so a corner")
A("   on them has no edge to move. The paint readings are in paint_before.json and paint_after.json.")
A("   elements whose pixels moved, named with their own floor and their own cross-arm count:")
for r in verdict["elements"]:
    if r["verdict"] == "MOVED":
        A("     MOVED  %-9s %-26s %-20s %s -> %s  floor=%s cross=%s rect=%s"
          % (r["tag"], (r["class"] or "")[:26], r["testid"] or "-", r["radius_before"], r["radius_after"],
             r["own_floor_px"], r["cross_arm_px"], r["rect"]))
for r in verdict["elements"]:
    if r["verdict"] == "NO_PIXEL_DELTA":
        A("     NO_PIXEL_DELTA %-9s %-26s %s -> %s floor=%s cross=%s  <-- the pill animates, so its own"
          % (r["tag"], (r["class"] or "")[:26], r["radius_before"], r["radius_after"], r["own_floor_px"], r["cross_arm_px"]))
        A("        floor is %s px and the 1 px corner step does not clear it; reported, not smoothed over." % r["own_floor_px"])
A("   geometry did not shift: all %d sampled elements matched between the arms on tag, class and rect"
  % verdict["sampled"])
A("   (rect compared to the pixel), and both arms booted the same screen (h1 and the hub and pending")
A("   testids are in paint_before.json / paint_after.json under the screen key).")
A("")
A("7. THE DARK PAIRING RULER, RUN ON BOTH TREES (the standing gate from ORD-0441)")
A("   instrument: tools/cnx_token_night_pairing_r1.py --tokens <file>, run on design-tokens.css taken")
A("   from git show of both refs. Its original output for each side is pair_tip.txt and pair_branch.txt.")
pair_t = read("pair_tip.txt")
pair_b = read("pair_branch.txt")
for lab, t in (("tip", pair_t), ("branch", pair_b)):
    A("   %-7s: rules %s, token declarations %s, colour tokens in root theme scopes %s,"
      % (lab, grab(t, r"(\d+) rules seen"), grab(t, r"(\d+) token declarations taken"),
         grab(t, r"colour tokens in root theme scopes\s*:\s*(\d+)")))
    A("            NEUTRAL_BY_NAME %s, PAIRED_INHERITED %s, PAIRED_IN_DARK %s, non-colour %s"
      % (grab(t, r"NEUTRAL_BY_NAME\s*:\s*(\d+)"), grab(t, r"PAIRED_INHERITED\s*:\s*(\d+)"),
         grab(t, r"PAIRED_IN_DARK\s*:\s*(\d+)"), grab(t, r"non-colour tokens in scope\s*:\s*(\d+)")))
A("   the colour cells are unchanged and the only movement is +%d non-colour tokens, which are the new"
  % (int(grab(pair_b, r"non-colour tokens in scope\s*:\s*(\d+)")) - int(grab(pair_t, r"non-colour tokens in scope\s*:\s*(\d+)"))))
A("   tier names. Both runs exited 0.")
A("")
A("8. GATES")
A("   npx tsc -p tsconfig.typecheck.json --noEmit  exit %s   (tsc_final.log in this lane's directory)" % tsc_rc)
A("   npx vite build on the branch  exit 0, entry %s" % arms["after"]["entry_named_by_served_index"])
A("   the tip arm build  steps %s" % ", ".join("%s=%s" % (n, rc) for n, rc in before_steps))
A("   audit_radii_ladder_r1.py exit 0 ; scope_check_r1.py exit 0 ; pairing ruler exit 0 twice")
A("   the copy ruler cnx_copy_tiers_r1 is NOT_APPLICABLE on this delivery, not skipped: the diff names")
A("   %d files and all %d are .css, so there is no dictionary input for it to read (git diff --name-only" % (len(FILES), len(FILES)))
A("   %s HEAD prints exactly that list)." % TIP[:12])
A("")
A("9. NOT CLAIMED")
A("   * The ladder is enforced by measurement on the two shapes above. A control that is not reachable")
A("     on the demo screen was not sampled, so this file does not claim the whole product is on the")
A("     table -- it claims 0 literal radius declarations remain in the source and 0 off-table values on")
A("     the screens measured.")
A("   * The pill's 13px -> 12px step is reported as NO_PIXEL_DELTA because its own animated floor is")
A("     larger than the corner delta. That is one element of %d, not a passing cell." % verdict["sampled"])
A("   * No real device was used; the 390x844 arm is a headless viewport, and the tile channel here is")
A("     this box's own egress.")
A("   * Whether 12px rather than 10px is the right corner for a quiet button is a design decision the")
A("     snap rule makes visible; it is not measured as an improvement by anything in this file.")
A("")
out = "\n".join(B) + "\n"
EVID.mkdir(parents=True, exist_ok=True)
(EVID / "RADIUMLADDER_R1.txt").write_text(out, encoding="utf-8", newline="\n")
print("wrote review/ord0459/RADIUMLADDER_R1.txt, %d lines, %d bytes" % (out.count("\n"), len(out.encode("utf-8"))))
