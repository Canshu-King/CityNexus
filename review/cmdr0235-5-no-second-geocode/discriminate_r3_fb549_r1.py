"""Is `test_r3_...` crowding caused by my narrowing, or by the two extra arms I added?

Single-variable discriminator: keep the test bytes (7 arms, so the same number of journeys and
provider-attempt rows are written) but disable the gate (M1 = the pre-ruling behaviour, the second
ask always happens). If r3 still flips, the narrowing is not the cause; the arm count / shared-DB
state is. N passes per shape, and the product file is restored and re-hashed.
"""

import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt543tip")
PROD = ROOT / "backend" / "app" / "integrations" / "discovery" / "real_city.py"
BACKEND = ROOT / "backend"
STATEMENT = (
    "                anchor_grounded_by_leg = any(\n"
    "                    reading.get(\"attempted\")\n"
    "                    and reading.get(\"answered\")\n"
    "                    and str((anchor or {}).get(\"source\") or \"\").startswith(f\"{reading.get('leg')}_\")\n"
    "                    for reading in anchor_leg_readings\n"
    "                )\n"
)
M1 = "                anchor_grounded_by_leg = False  # DISCRIMINANT M1\n"
FILES = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/fb549_affected_files.txt").read_text(
    encoding="utf-8").split() + ["tests/test_qoder_ord0531_bin_ownership.py"]
WATCH = ("test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage",
         "test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match")
PASSES = int(sys.argv[1]) if len(sys.argv) > 1 else 4


def run_once():
    proc = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
                           "--no-header", "--tb=no"] + FILES, cwd=str(BACKEND),
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    reds = {line.split("::")[-1] for line in proc.stdout.splitlines() if line.startswith("FAILED")}
    return reds


def main() -> int:
    original = PROD.read_bytes()
    text = original.decode("utf-8")
    assert text.count(STATEMENT) == 1
    tally = {}
    for shape, payload in (("gate ON (my head)", None), ("gate OFF (M1)", M1)):
        PROD.write_bytes((text if payload is None else text.replace(STATEMENT, payload, 1)).encode("utf-8"))
        flips = []
        all_reds = set()
        for i in range(PASSES):
            reds = run_once()
            all_reds |= reds
            flips.append(tuple(sorted(n for n in reds if n in WATCH)))
        tally[shape] = (flips, sorted(all_reds))
        print(f"{shape}: per-pass r3/r4 reds = {flips}")
        print(f"   union of reds over {PASSES} passes = {sorted(all_reds)}")
        PROD.write_bytes(original)
        assert PROD.read_bytes() == original, shape
        print(f"   restored byte-identical: sha256[:16]={hashlib.sha256(original).hexdigest()[:16]}")
    a, b = tally["gate ON (my head)"][0], tally["gate OFF (M1)"][0]
    print("\nverdict: r3/r4 flip with the gate OFF as well ->",
          any(b) if any(a) else "no flip observed on either shape in this sample")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
