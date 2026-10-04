"""Two single-variable counter-arms proving the reachability ruler can actually be flipped.

A verdict table nobody can change is a photo, not a ruler.  Each mutation edits ONE line of
`backend/app/main.py`, keeps the rest of the file byte-identical, runs the shipped ruler against it, and
restores it; the ruler's own verdict for exactly one row must move, and every other row must not.

  M1 plant a hard-delete   add `session.delete(journey)` to the bin route -- the sentence
                           `errJourneyNotFound` waits on a row that stops existing, so the ruler must
                           flip that row from UNREACHABLE_BY_A_TRAVELLER_STEP to
                           REACHABLE_BY_A_TRAVELLER_STEP, and flip it back when the line is removed.
  M2 hide the null pointer replace the create door's `active_plan_version_id=None` with a non-null
                           default -- `errNoActivePlan` is reachable precisely because a made-but-never-
                           planned trip is a real state, so that row must flip to
                           UNREACHABLE_BY_A_TRAVELLER_STEP and back.

Both mutants are instrument-only: the file is restored from the bytes read at the start and re-hashed, and
mutant generations of the ruler's JSON are named with the run stamp and then deleted, so nothing published
is reachable by a re-run.  A receipt with every rc, verdict and hash is written next to the ruler's output.

    D:/moodle/CityNexus/.venv/Scripts/python.exe -X utf8 review/ord0545/refusal_reachability_ruler_counterarm_r1.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAIN = ROOT / "backend/app/main.py"
RULER = os.environ.get("CITYNEXUS_ORD0545S5_RULER", "review/ord0545/refusal_reachability_ruler_r1.py")
RD = ROOT / "review/ord0545/readouts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
RECEIPT = RD / f"refusal_reachability_ruler_counterarms_{STAMP}.json"
LOCK = DATA / "refusal_reachability_ruler_counterarm.lock"
PY = sys.executable
BASE_TIP = os.environ.get("CITYNEXUS_ORD0545_BASE_TIP", "")

MUTATIONS = [
    {"name": "M1_plant_a_hard_delete_branch",
     "row": "errJourneyNotFound",
     "needle": '    journey.deleted_at = datetime.now(timezone.utc).isoformat()\n',
     "replace": '    journey.deleted_at = datetime.now(timezone.utc).isoformat()\n'
                '    session.delete(journey)\n',
     "expect_after": "REACHABLE_BY_A_TRAVELLER_STEP"},
    {"name": "M2_hide_the_null_plan_pointer",
     "row": "errNoActivePlan",
     "needle": "        active_plan_version_id=None,",
     "replace": "        active_plan_version_id=str(uuid4()),",
     "expect_after": "UNREACHABLE_BY_A_TRAVELLER_STEP"},
]


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


TMP_TAGS: list[str] = []


def run_ruler(tag: str) -> dict:
    TMP_TAGS.append(tag)
    env = dict(os.environ)
    env.update({"CITYNEXUS_ORD0545S5_RULER_NAME": f"tmp_{tag}.json",
                "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP})
    proc = subprocess.run([PY, "-X", "utf8", RULER], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300, env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    (DATA / f"ruler_{tag}.txt").write_text(out, encoding="utf-8", newline="\n")
    doc_path = RD / f"tmp_{tag}.json"
    doc = json.loads(doc_path.read_text(encoding="utf-8")) if doc_path.exists() else {}
    verdicts = {r["table_key"]: r["verdict"] for r in doc.get("rows", [])}
    return {"rc": proc.returncode, "verdicts": verdicts,
            "n_rows": len(verdicts), "tally": doc.get("tally")}


def main() -> int:
    if LOCK.exists():
        holder = "".join(c for c in LOCK.read_text(encoding="utf-8") if c.isdigit())
        alive = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                                f"Get-Process -Id {holder} -ErrorAction SilentlyContinue | "
                                "ForEach-Object { $_.Id }"], capture_output=True, text=True).stdout.strip()
        if alive:
            raise SystemExit("ABORT: another instance holds the lock (live pid " + alive + ")")
        print("lock left by a dead pid; taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    original = MAIN.read_bytes()
    pristine = sha(MAIN)
    rows: dict[str, object] = {"generation": {"base_tip": BASE_TIP, "recorded_at": STAMP,
                                              "main_sha_before": pristine}, "rows": []}
    bits: list[bool] = []

    def emit() -> None:
        RECEIPT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    try:
        base = run_ruler("base")
        rows["rows"].append({"row": "baseline_shipped_source", **base})
        bits.append(base["rc"] == 0 and base["n_rows"] == 7)
        emit()
        for mut in MUTATIONS:
            text = original.decode("utf-8")
            count = text.count(mut["needle"])
            if count != 1:
                rows["rows"].append({"row": mut["name"], "skipped": f"anchor appears {count} times"})
                bits.append(False)
                emit()
                continue
            MAIN.write_text(text.replace(mut["needle"], mut["replace"], 1), encoding="utf-8", newline="\n")
            landed = sha(MAIN) != pristine
            during = run_ruler(mut["name"][:10] + "on")
            MAIN.write_bytes(original)
            restored = sha(MAIN) == pristine
            after = run_ruler(mut["name"][:10] + "off")
            MAIN.write_bytes(original)
            restored = restored and sha(MAIN) == pristine
            flipped = during["verdicts"].get(mut["row"]) == mut["expect_after"]
            others_unchanged = all(during["verdicts"].get(k) == base["verdicts"].get(k)
                                   for k in base["verdicts"] if k != mut["row"])
            flipped_back = after["verdicts"].get(mut["row"]) == base["verdicts"].get(mut["row"])
            ok = landed and flipped and others_unchanged and flipped_back and restored
            bits.append(ok)
            rows["rows"].append({
                "row": mut["name"], "watched_row": mut["row"], "expect_after": mut["expect_after"],
                "baseline_verdict": base["verdicts"].get(mut["row"]),
                "mutant_verdict": during["verdicts"].get(mut["row"]),
                "restored_verdict": after["verdicts"].get(mut["row"]),
                "mutation_landed": landed, "flips_as_expected": flipped,
                "other_six_rows_unchanged": others_unchanged, "flips_back_after_restore": flipped_back,
                "main_restored_byte_identical": restored, "bites": ok,
                "rows_seen_during": during["n_rows"], "rows_seen_after": after["n_rows"],
            })
            emit()
            print(mut["name"], "baseline", str(base["verdicts"].get(mut["row"]))[:14], "-> mutant",
                  str(during["verdicts"].get(mut["row"]))[:14], "-> restored",
                  str(after["verdicts"].get(mut["row"]))[:14], "| others unchanged", others_unchanged,
                  "| restored bytes", restored, flush=True)
    finally:
        MAIN.write_bytes(original)
        rows["main_sha_after"] = sha(MAIN)
        rows["main_untouched"] = sha(MAIN) == pristine
        # delete exactly the temporary files this run wrote -- never a glob that could reach someone
        # else's tmp_* artifact in the same directory
        for junk in list(RD.glob("tmp_*.json")):
            if junk.name.startswith(tuple(f"tmp_{t}." for t in TMP_TAGS)):
                junk.unlink()
        LOCK.unlink(missing_ok=True)
        emit()

    rows["verdict"] = ("KILL_OK two single-variable mutations flip exactly their own row and flip back, "
                       "source byte-identical after every step"
                       if all(bits) and rows["main_untouched"] else "NOT_OK -- see the rows above")
    emit()
    print(rows["verdict"], "->", RECEIPT.name, RECEIPT.stat().st_size, "B")
    return 0 if rows["verdict"].startswith("KILL_OK") else 1


if __name__ == "__main__":
    sys.exit(main())
