# ORD-0417 lane evidence -- how each number here was produced and how to produce it again

Lane: session 8ac89982 (this window's own id, from the task-output path the harness writes).
Tree under test is never D:/moodle/CityNexus itself -- that working tree is frozen and shared, so
every reading below comes from a `git archive` export of a named 40-hex rev, or from a bundle built
from one.

## The two revs everything is compared on

    authoritative line as read at build time  8a7665be2061a2f38aa2227f81c57003ca4caacb
    this lane's commit                        38b6ae7a9b68f014e606bdda5b1f6dd8ce50d273  (parent = the above)
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
