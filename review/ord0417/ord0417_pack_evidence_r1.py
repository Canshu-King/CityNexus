"""ORD-0417 lane evidence pack r1 -- assemble the readings this block cites into the branch.

Every number in the ledger block has to be retrievable: `path:line` in the repo, or a 40-hex blob the
commander can `git cat-file`.  Readings that live only under D:/moodle/_qoder_b_ord0417_20260928 are
not that, so they are copied here, trimmed to the parts that carry the number, and committed as a
second, additive commit on the review branch (the first commit's product bytes are not touched).

Nothing in this script writes to D:/moodle/CityNexus's working tree: the files land in a staging
directory, are hashed with `--no-filters`, and are grafted onto the first commit through a throwaway
index, exactly as `ord0417_commit_r1.py` did.

usage: python ord0417_pack_evidence_r1.py [--apply]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
STAGE = LANE / "evidence_pack"
BRANCH = "refs/heads/review/R-ord0417-tap-names-stop-r4"
TARGET = "review/ord0417"
CENSUS_KEEP = [
    "label", "shape", "arm", "hit_floor_px", "pins_total", "pins_individually_hittable",
    "tapped", "controls_idle", "controls_with_band", "reachable_idle", "reachable_with_band",
    "lost_reachable", "band_box_idle", "band_box_with_band", "band_growth_px",
    "newly_covered_pins", "newly_unhittable_pins", "newly_below_floor_pins",
    "name_painted_on_glass", "glass_visible", "errors", "fatal", "autoscroll_to_card_px",
]
GATE_RUNS = ["ord0417r7rebase", "ord0417r9tipreach", "ord0417r10mutantM1",
             "ord0417r11gatefinal", "ord0417r12mutantfinal", "ord0417r13gateathead", "ord0417r14tipathead", "ord0417r15rebase2", "ord0417r16tipatbase3", "ord0417r17reatfinal", "ord0417r18newbase", "ord0417r19newbasetip"]

RUNBOOK = """# ORD-0417 lane evidence -- how each number here was produced and how to produce it again

Lane: session 8ac89982 (this window's own id, from the task-output path the harness writes).
Tree under test is never D:/moodle/CityNexus itself -- that working tree is frozen and shared, so
every reading below comes from a `git archive` export of a named 40-hex rev, or from a bundle built
from one.

## The two revs everything is compared on

    authoritative line at first build          8a7665be2061a2f38aa2227f81c57003ca4caacb
authoritative line, re-read 2nd          3d28da7d221cfd2ca463991796f0a257df042972 (ORD-0419 landed
                                            `frontend/src/styles.css`, not one of my four paths)
authoritative line as delivered against  fb6131f359e85deb18a2194494dc9a96e328cdee (ORD-0420/0421/
                                            0423 landed; ORD-0423 moved `frontend/src/i18n/
                                            LocaleContext.tsx`, one of my four paths, in regions
                                            away from my anchor -- the replay is +8 lines, -0 lines)
    this lane's branch r1 head                1c642c68df93514d1254142f1f011c3a9dac65b0 (parent 8a7665be)
this lane's branches, all pushed as new refs, none force-pushed, r1/r2 left intact:
    r1 head 1c642c68df93514d1254142f1f011c3a9dac65b0  parent 8a7665be   (superseded)
    r2 head 6020871f0452cc4b1844dd8cc78b4acbeb294595  parent 3d28da7d   (superseded)
    r3 head -- DELIVER -- parent fb6131f3, code+spec commit 93a3ff5c79edf51bdb1307b219468ff632b0cb58;
         this pack is its child.  Read the head with `git rev-parse <branch>`; do not copy a
         coordinate out of prose -- this lane mis-typed one sha from memory and the push named it.
    the rev quoted in the ticket              214ab0ff9f1dc03ffbd57308797e62552b7ee24a  (superseded; ORD-0410
                                            landed `frontend/src/components/v8/MapPanel.tsx` in between)

## Private stack (this lane's own ports; :8000 never started, :4781/:4782/:8693 never rebound)

    :4831  uvicorn on the export, CITYNEXUS_DATABASE_URL = sqlite:///.../db/ord0417.db
    :4832  cmdr_static_api_proxy_r1.py over _build_ord0417tip/frontend/dist   -> api :4831
    :4833  cmdr_static_api_proxy_r1.py over _build_ord0417fix/frontend/dist   -> api :4831
    :4834/:4835  the gate's own vite + uvicorn, started by playwrightEnv via ord0417_run_gate_r1.py
    :4836/:4837  the same, pointed at the pure-tip tree (ORD0417_TREE=.../exp_tip)

    The database the bundle stack serves is a `src.backup(dst)` copy taken through
    `sqlite3.connect('file:.../_preview.db?mode=ro', uri=True)`; the shared preview database is never
    opened for write and `demo/reset` is never called against it.  The gate runs on databases created
    empty by its own run id, because `backend/app/db/session.py:41` refuses to reopen one.
    Basic-auth material is not read, printed, or stored by anything in this pack; only the path
    D:/moodle/_qoder_preview_20260920/run/preview_auth.txt is named.

## Reading-by-reading

  MAP_TAP_*_R1.json        node _map_tap_names_stop_r1.js <base> <outdir>   (the commander's own
                           instrument, D:/moodle/_qoder_cmdr_ref_20260921/live_checks/)
  REPRO_ON_214ab0ff_*.json same instrument and ord0417_probe_r1.js, run at 23:15-23:20 against the
                           build of the ticket's rev -- this is where the ticket's three `false` values
                           were re-confirmed, and where the card-outside-the-panel reading came from.
  GEOMETRY_CENSUS_*.json   node ord0417_geometry_census_r1.js <base> <outdir> <label>
                           4 shapes x 2 arms, lane N3's frozen 口径.
  GATE_ORD0417R11GATEFINAL_*  the gate green on the rebased candidate:
                           python ord0417_run_gate_r1.py ord0417r11gatefinal <spec files> --reporter=line
  GATE_ORD0417R9TIPREACH_* the same arms on the untouched tip tree, which is what attributes the reds.
  GATE_ORD0417R10MUTANTM1_TRIMMED.txt -- the first mutant run, which is also the evidence
                           that this lane's own A1/A2 assertions were reporting the wrong thing.
                           See the gate r2 commit message for the `expect(false, msg)` no-op this exposed.
GATE_ORD0417R12MUTANTFINAL_* the mutant re-run after that fix: 14 of the 17 arms red, and
                           every red names its own assertion id.  The green run on the very
                           bytes the branch head carries is GATE_ORD0417R13GATEATHEAD_*
                           (this lane's spec plus the five map neighbours).
                           The identical command against the untouched tip tree is
                           GATE_ORD0417R15REBASE2_*  the gate + neighbours on the rebased tree, at the new base; the
                           gate's own readings are GATE_R15_READINGS.json.  The instrument run
                           on the bundle built from the delivered commit is
                           MAP_TAP_R2FIX_7f7265d6_R1.json.
                           GATE_ORD0417R16TIPATBASE3_*  the same reach arms on the untouched new
                           base, which is the attribution pair for R15REBASE2.
                           GATE_ORD0417R14TIPATHEAD_* -- that is what the neighbour reds are
                           attributed with, since ord0403's reach arms are not stable between
                           runs on this machine.
  COPY_PAIR_*.json         python ord0417_bundle_copy_check_r1.py --sha <40> --base <port> --out <file>
                           the commander's r2 rule with the rev named, so a candidate can be paired too.

## Two limits of this evidence, stated rather than left to be discovered

1. `test.afterAll` in the gate writes `readings.json`, and in a run where arms fail it held only one
   row (GATE_ORD0417R9TIPREACH_TRIMMED.txt: the eight `geometry-*` console lines are in the log,
   while the json carried one).  So the logs are cited, not that json, wherever a failing run is the
   witness.  `GATE_R11_READINGS.json` is trustworthy only because that run was green (18 rows).
2. `_map_tap_names_stop_r1.js` taps the marker at whatever pixel it occupies, and the framing changed
   when ORD-0410 landed: the same instrument reports tap_centre [160, 481] at 8a7665be where the
   ticket recorded [224, 495] at 214ab0ff.  The verdict fields are still comparable because the
   instrument reads the tapped marker's own aria-label as the target name; the coordinate is not
   comparable across the two revs.

## The mutant

`exp2/frontend/src/components/v8/MapPanel.tsx` -- replace the `{selectedPoint && (<span
className="v8-map-selected-stop" ...>)}` block with `{null}`.  Nothing else changes: the dictionary
keeps both arms and `map-selection.css` keeps the rule, so the mutation is exactly "take away the
visible output".  Proof it landed is in GATE_ORD0417R12MUTANTFINAL_TRIMMED.txt: `grep -c
v8-map-selected-stop` over the component returns 0 while both dictionary arms and the CSS rule still
match 1 each.
"""


def git(*args, index=None):
    import os
    env = dict(os.environ)
    if index:
        env["GIT_INDEX_FILE"] = index
    p = subprocess.run(["git", "-C", REPO, *args], capture_output=True, env=env)
    if p.returncode:
        raise SystemExit(f"ABORT git {' '.join(args)} -> {p.stderr.decode('utf-8','replace').strip()[:300]}")
    return p.stdout.decode("utf-8", "replace").strip()


def trim_log(run_id: str) -> str:
    """Keep the lines that carry a number or a verdict; drop the uvicorn request flood."""
    src = LANE / "evidence" / "gate" / f"{run_id}.log"
    if not src.is_file():
        return f"(no log at {src})\n"
    out = []
    for line in src.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("[WebServer]"):
            continue
        if re.search(r":: |Error: |^\s+\d+\) |passed|failed|expect\(|citynexus e2e\]", line):
            out.append(line[:2000])
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    STAGE.mkdir(exist_ok=True)
    written = {}

    def put(name, text):
        p = STAGE / name
        p.write_text(text, encoding="utf-8", newline="\n")
        written[name] = len(p.read_bytes())

    for tag, src in (
        ("MAP_TAP_TIP_R1.json", LANE / "evidence/cmdr_tip/map_tap_names_stop_r1.json"),
        ("MAP_TAP_FIX_R1.json", LANE / "evidence/cmdr_fix/map_tap_names_stop_r1.json"),
        ("COPY_PAIR_TIP_R1.json", LANE / "evidence/COPY_PAIR_TIP_R1.json"),
        ("COPY_PAIR_FIX_R1.json", LANE / "evidence/COPY_PAIR_FIX_R1.json"),
        ("GATE_R11_READINGS.json", LANE / "evidence/e2e/ord0417/ord0417r11gatefinal__readings.json"),
        ("GATE_R13_READINGS.json", LANE / "evidence/e2e/ord0417/ord0417r13gateathead__readings.json"),
        ("GATE_R15_READINGS.json", LANE / "evidence/e2e/ord0417/ord0417r15rebase2__readings.json"),
        ("MAP_TAP_R2FIX_7f7265d6_R1.json", LANE / "evidence/cmdr_r2fix/map_tap_names_stop_r1.json"),
        ("MAP_TAP_BASE_FB6131F3_R1.json", LANE / "evidence/cmdr_fb3tip/map_tap_names_stop_r1.json"),
        ("MAP_TAP_DELIVERED_93A3FF5C_R1.json", LANE / "evidence/cmdr_fb3fix/map_tap_names_stop_r1.json"),
        ("COPY_PAIR_DELIVERED_R1.json", LANE / "evidence/COPY_PAIR_R3FIX_R1.json"),
        ("GATE_R17_READINGS.json", LANE / "evidence/e2e/ord0417/ord0417r17reatfinal__readings.json"),
        ("GATE_R18_READINGS.json", LANE / "evidence/e2e/ord0417/ord0417r18newbase__readings.json"),
        ("MAP_TAP_BASE_214809685_R1.json", LANE / "evidence/newtip_ab/map_tap_names_stop_r1.json"),
        ("MAP_TAP_R4FIX_32A27205_R1.json", LANE / "evidence/untranslated_r3/map_tap_names_stop_r1.json"),
        ("UNTRANSLATED_R3_MAP_BASE_R1.json", LANE / "evidence/untranslated_r3_base/untranslated_map_r3.json"),
        ("UNTRANSLATED_R3_MAP_DELIVERED_R1.json", LANE / "evidence/untranslated_r3/untranslated_map_r3.json"),
        ("COPY_PAIR_R4_DELIVERED_R1.json", LANE / "evidence/COPY_PAIR_R4_R1.json"),
        ("LSREMOTE_R2_R1.txt", LANE / "evidence/LSREMOTE_R2_R1.txt"),
        ("REPRO_ON_214ab0ff_INSTRUMENT_R1.json", LANE / "evidence/base/map_tap_names_stop_r1.json"),
        ("REPRO_ON_214ab0ff_PROBE_R1.json", LANE / "evidence/base_probe_zh_390x844/probe.json"),
    ):
        put(tag, src.read_text(encoding="utf-8", errors="replace"))

    for tag, src in (("GEOMETRY_CENSUS_TIP_R1.json", LANE / "evidence/geom_tip/TIPTREE.census.json"),
                     ("GEOMETRY_CENSUS_FIX_R1.json", LANE / "evidence/geom_fix/FIXTREE.census.json")):
        d = json.loads(src.read_text(encoding="utf-8", errors="replace"))
        d["results"] = [{k: r[k] for k in CENSUS_KEEP if k in r} for r in d["results"]]
        put(tag, json.dumps(d, ensure_ascii=False, indent=1))

    for run in GATE_RUNS:
        put(f"GATE_{run.upper()}_TRIMMED.txt", trim_log(run))

    for inst in ("ord0417_probe_r1.js", "ord0417_geometry_census_r1.js",
                 "ord0417_bundle_copy_check_r1.py", "ord0417_run_gate_r1.py",
                 "ord0417_commit_r1.py", "ord0417_pack_evidence_r1.py"):
        put(inst, (LANE / "run" / inst).read_text(encoding="utf-8"))

    put("RUNBOOK_r1.md", RUNBOOK)

    print(json.dumps(written, ensure_ascii=False, indent=1))

    # A guard the publication order has bitten me with before: refuse to ship credential *content*.
    # Naming the path where a credential lives is what the order asks for ("只写路径"); the value is
    # not.  The pattern therefore requires a value to follow the keyword -- a bare keyword is not
    # evidence of a secret, and this lane's own instruments legitimately contain the words this scan
    # looks for (they are written into the regex below).  Weakening a gate to green itself is the thing
    # I am not allowed to do, so the change here is scope, not threshold: it still fires on a real
    # Basic-auth header carrying a base64 value (calibrated against a synthetic one, in the delivery
    # block), and it says in the receipt how many files it looked at.  Note the third and fourth
    # patterns exclude a leading backslash precisely so a regex source line does not read as a value.
    value_patterns = [
        re.compile(r"Authorization\s*:\s*Basic\s+[A-Za-z0-9+/=]{8,}"),
        re.compile(r"(?i)password\s*[:=]\s*[^\s\\][^\s]{3,}"),
        re.compile(r"(?i)secret\s*[:=]\s*[^\s\\][^\s]{7,}"),
    ]
    risky = {}
    scanned = []
    for name in sorted(written):
        body = (STAGE / name).read_text(encoding="utf-8", errors="replace")
        scanned.append(name)
        for pat in value_patterns:
            for m in pat.findall(body):
                risky.setdefault(name, []).append(str(m)[:24] + "…")
    print("CREDENTIAL_SCAN_FILES", len(scanned))
    print("CREDENTIAL_SCAN_HITS", json.dumps(risky, ensure_ascii=False))
    if risky:
        raise SystemExit("ABORT: a staged file carries something shaped like a credential value")

    if not a.apply:
        print("DRY: nothing committed")
        return 0

    head = git("rev-parse", BRANCH)
    idx = str(LANE / "run" / f"ord0417.index.pack.{head[:8]}")
    import os
    if os.path.exists(idx):
        os.remove(idx)
    git("read-tree", head, index=idx)
    for name in sorted(written):
        blob = git("hash-object", "-w", "--no-filters", str(STAGE / name), index=idx)
        git("update-index", "--add", "--cacheinfo", f"100644,{blob},{TARGET}/{name}", index=idx)
        print("PUBLISH", f"{TARGET}/{name}", blob)
    tree = git("write-tree", index=idx)
    msg = ("ORD-0417 evidence: the tip-vs-candidate readings, the mutant log, and the instruments\n\n"
           "Every number the delivery block carries is here as a blob, with the instrument that\n"
           "produced it, so the claim is re-runnable rather than quotable. No product byte changes\n"
           "in this commit -- `git diff` against the parent touches review/ord0417/ only.\n")
    commit = git("commit-tree", tree, "-p", head, "-m", msg, index=idx)
    git("update-ref", BRANCH, commit)
    os.remove(idx)
    diff = git("diff", "--name-status", head, commit).splitlines()
    print("HEAD_BEFORE", head)
    print("HEAD_AFTER", commit)
    print("DIFF_LINES", len(diff), "all under review/ord0417:",
          all(l.split("\t")[-1].startswith(f"{TARGET}/") for l in diff))
    return 0


if __name__ == "__main__":
    sys.exit(main())
