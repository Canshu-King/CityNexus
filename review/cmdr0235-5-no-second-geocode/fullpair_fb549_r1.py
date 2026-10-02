"""Like-for-like full backend suite: clean tip tree vs my branch, both with `frontend` checked out.

`--continue-on-collection-errors` is needed at this head because
`tests/test_v18_hermes_r20_transport_reliability_probe.py` imports `citynexus_mcp`, which the
interpreter does not provide - a condition of the head, identical in both trees, and printed as
such rather than hidden.
"""
import json, os, pathlib, subprocess, sys, datetime
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
TREES = {"tip": pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt543tip"),
         "branch": pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt_fb549")}
out = {"at": datetime.datetime.now().isoformat(), "interpreter": subprocess.run([PY,"-V"],capture_output=True,text=True).stdout.strip(), "arms": {}}
for name, root in TREES.items():
    env = dict(os.environ); env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header",
                           "--continue-on-collection-errors", "tests"],
                          cwd=str(root / "backend"), capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=3000)
    (RUN / f"full_{name}_fb549.txt").write_bytes(proc.stdout.encode("utf-8"))
    lines = proc.stdout.splitlines()
    reds = sorted({l.split("::")[-1].split(" ")[0] for l in lines if l.startswith("FAILED")})
    errs = sorted({l.split("::")[-1].split(" ")[0] for l in lines if l.startswith("ERROR")})
    summary = [l for l in lines if " passed" in l and " in " in l]
    out["arms"][name] = {"head": subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),
                         "rc": proc.returncode, "summary": summary[-1] if summary else "(none)",
                         "red_count": len(reds), "reds": reds, "error_count": len(errs), "errors": errs,
                         "file": str(RUN / f"full_{name}_fb549.txt")}
    print(f"{name}: rc={proc.returncode} {out['arms'][name]['summary']} reds={len(reds)} errors={len(errs)}")
t, b = out["arms"]["tip"], out["arms"]["branch"]
only_branch = sorted(set(b["reds"]) - set(t["reds"]))
fixed = sorted(set(t["reds"]) - set(b["reds"]))
out["diff"] = {"red_only_on_branch": only_branch, "red_only_at_tip": fixed,
               "errors_only_on_branch": sorted(set(b["errors"]) - set(t["errors"]))}
(RUN / "fullpair_fb549_r1.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print("\nred ONLY on branch (must be empty):", only_branch)
print("red only at tip:", fixed)
print("errors only on branch:", out["diff"]["errors_only_on_branch"])
