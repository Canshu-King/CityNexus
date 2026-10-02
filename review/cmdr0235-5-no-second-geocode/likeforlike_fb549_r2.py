"""Like-for-like affected-set run: clean tip tree vs my branch tree, identical sparse scope.

Both trees now check out `backend contracts data frontend review scripts tools`, so the earlier
sparse-denominator mistake cannot repeat. `test_v18_hermes_*` was the file that aborted a whole
directory collection once; it is not in this list, and the list is passed explicitly to both.
"""

import pathlib
import subprocess
import sys

RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
FILES = [
    "tests/test_foundation_registry.py",
    "tests/test_ord0544_anchor_leg_shape_r1.py",
    "tests/test_qoder_anywhere_discovery_truth.py",
    "tests/test_qoder_anywhere_gates.py",
    "tests/test_qoder_catalog_hydration.py",
    "tests/test_qoder_city_failure_reasons.py",
    "tests/test_qoder_ord197_four_class_receipt.py",
    "tests/test_qoder_provider_identity_leg.py",
    "tests/test_v14_trial_readiness.py",
    "tests/test_v6_predictive_real_city.py",
]
TREES = {
    "branch": pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt_fb549"),
    "tip": pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt543tip"),
}
PYTHON = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"

print("interpreter:", subprocess.run([PYTHON, "-V"], capture_output=True, text=True).stdout.strip())
for name, root in TREES.items():
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--", "backend"],
                           capture_output=True, text=True).stdout.strip()
    print(f"{name}: head={head} backend-dirt={len(dirty.splitlines())} file(s)")
    if dirty:
        print("   " + dirty.replace("\n", "\n   "))

for name, root in TREES.items():
    proc = subprocess.run(
        [PYTHON, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header"] + FILES,
        cwd=str(root / "backend"), capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    out = RUN / f"aff_{name}_r2.txt"
    out.write_bytes(proc.stdout.encode("utf-8") + f"\nrc={proc.returncode}\n".encode())
    reds = [line for line in proc.stdout.splitlines() if line.startswith(("FAILED", "ERROR"))]
    summary = [line for line in proc.stdout.splitlines() if " passed" in line or " failed" in line or "error" in line]
    print(f"\n=== {name} ===  rc={proc.returncode}  -> {out.name}")
    print("  " + (summary[-1] if summary else "(no summary)"))
    for line in reds:
        print("  " + line)
    (RUN / f"aff_{name}_r2.reds.txt").write_text("\n".join(sorted(reds)) + "\n", encoding="utf-8")

branch_reds = {l.split("::")[-1] for l in (RUN / "aff_branch_r2.reds.txt").read_text(encoding="utf-8").splitlines()}
tip_reds = {l.split("::")[-1] for l in (RUN / "aff_tip_r2.reds.txt").read_text(encoding="utf-8").splitlines()}
print("\n=== red-set diff (arm names) ===")
print(f"  tip reds            : {sorted(tip_reds)}")
print(f"  branch reds         : {sorted(branch_reds)}")
print(f"  red ONLY on branch  : {sorted(branch_reds - tip_reds)}   <- must be empty")
print(f"  red only at tip     : {sorted(tip_reds - branch_reds)}")
