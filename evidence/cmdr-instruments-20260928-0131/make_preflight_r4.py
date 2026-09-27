#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_preflight_r4.py -- derive preflight_and_land_r4.py from r3 by adding a build arm.

Why a new file and not an edit in place: r3's identity is bolted into receipts that already shipped
(its blob is cited), so the instrument moves by publishing a successor, never by rewriting the one
that was judged.

The defect being closed: at 01:19 on 2026-09-28 this door returned READY_TO_LAND for a candidate
whose `frontend/src/features/planning/PlanWithAiSheet.tsx` contained an unescaped ASCII double quote
inside a double-quoted Chinese string.  `vite build` rejects that file, so the door had certified a
frontend that cannot compile.  The phone was swapped onto the *previous* generation only by luck of
ordering, and the fix-forward patch became tip `53a00d5e6552006ebfb7cc03d109cf4b675450dc`.

The arm deliberately shells out to `cmdr_build_bundle_r1.py` -- the same builder the swap uses --
rather than re-implementing a build, because two definitions of "it builds" is how this door just
got out-certified.
"""
from pathlib import Path

SRC = Path(__file__).with_name("preflight_and_land_r3.py")
DST = Path(__file__).with_name("preflight_and_land_r4.py")

ARG_ANCHOR = '''    ap.add_argument("--land", action="store_true", help="actually move the authoritative line (default: dry run)")'''

ARG_NEW = '''    ap.add_argument("--frontend-build", default="on", choices=["on", "off"],
                    help="compile arm (default on).  When the candidate introduces any "
                         "frontend/src file, run the SAME builder the phone swap uses "
                         "(cmdr_build_bundle_r1.py) against the candidate tip and refuse unless "
                         "vite exits 0 and produces dist + index.html.  r3 shipped a candidate the "
                         "bundler rejects; that is the hole this closes.  'off' is recorded as an "
                         "untested face, never as a pass.")
''' + ARG_ANCHOR

ARM_ANCHOR = '''        run["exposure"] = {"skipped": ("no frontend/src file changed" if fe_cand == [] else "arm off")}
'''

ARM_NEW = ARM_ANCHOR + '''
    # ---- compile arm: a frontend the bundler rejects is not shipped software -------------------
    # Added because r3 certified tip c215342802 as READY_TO_LAND while `vite build` failed on
    # PlanWithAiSheet.tsx (1025:72 "Expected \\":\\" but found ..."), i.e. the door had greenlit a
    # phone generation that would render nothing.
    if fe_cand:
        if a.frontend_build == "on":
            import json as _json
            here = os.path.dirname(os.path.abspath(__file__))
            info_path = os.path.join(here, "_build_%s_info.json" % cand[:7])
            rb = subprocess.run([sys.executable, os.path.join(here, "cmdr_build_bundle_r1.py"),
                                 "--sha", cand], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=1500, cwd=here)
            rec = {}
            if os.path.exists(info_path):
                try:
                    with open(info_path, encoding="utf-8") as fh:
                        rec = _json.load(fh)
                except Exception as exc:  # noqa: BLE001
                    rec = {"read_error": "%s: %s" % (type(exc).__name__, str(exc)[:200])}
            else:
                rec = {"read_error": "builder wrote no info file at %s" % info_path}
            binfo = rec.get("build") or {}
            steps = rec.get("steps") or []
            vite_step = next((s for s in steps if s.get("step") == "vite_build"), {})
            run["frontend_build"] = {
                "builder_rc": rb.returncode,
                "vite_build_rc": vite_step.get("rc"),
                "dist_exists": bool(binfo.get("dist_exists")),
                "index_exists": bool(binfo.get("index_exists")),
                "asset_refs": binfo.get("asset_refs"),
                "live_tree": rec.get("live_tree"),
                "info_file": info_path,
                "build_tail": [str(t)[-200:] for t in (vite_step.get("tail") or [])][-8:],
            }
            if (vite_step.get("rc") != 0 or not binfo.get("dist_exists")
                    or not binfo.get("index_exists")):
                problems.append(
                    "candidate does not COMPILE: vite_build rc=%s dist=%s index=%s -- refusing to land "
                    "a frontend the bundler rejects.  tail=%s"
                    % (vite_step.get("rc"), binfo.get("dist_exists"), binfo.get("index_exists"),
                       " | ".join(run["frontend_build"]["build_tail"])[-600:]))
        else:
            run["frontend_build"] = {
                "skipped": "arm off -- %d frontend/src file(s) shipped WITHOUT a compile check"
                           % len(fe_cand)}
            problems.append("compile arm requested off while %d frontend/src file(s) changed; "
                            "the door will not certify an uncompiled frontend -- pass nothing to "
                            "keep it on, or land with --frontend-build off only if you also accept "
                            "the receipt saying NOT COMPILED" % len(fe_cand))
    else:
        run["frontend_build"] = {"skipped": "no frontend/src file in this candidate"}
'''


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    for anchor, name in ((ARG_ANCHOR, "argparse"), (ARM_ANCHOR, "arm")):
        if text.count(anchor) != 1:
            raise SystemExit("ABORT: anchor %s matched %d times, expected exactly 1" % (name, text.count(anchor)))
    text = text.replace(ARG_ANCHOR, ARG_NEW, 1)
    text = text.replace(ARM_ANCHOR, ARM_NEW, 1)
    header_old = "preflight_and_land_r3"
    text = text.replace(header_old, "preflight_and_land_r4")
    DST.write_text(text, encoding="utf-8", newline="")
    import ast
    ast.parse(text)
    print("wrote %s (%d B, %d lines) and it parses" % (DST.name, DST.stat().st_size, len(text.split(chr(10)))))


if __name__ == "__main__":
    main()
