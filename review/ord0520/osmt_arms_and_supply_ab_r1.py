"""One run, both states: the osm_type arms and the door's real-supply buckets, before and after.

Nothing here is typed in.  Each number is read out of a command this script actually runs, and both
states are measured in the same minute against the same HEAD, so a "before" cannot be a stale file
from an earlier generation (which is how I got caught out once already this lane).

Three measurements per state:
  1. the five door-level arms of tests/test_qoder_ord0520_osm_type_bare_kind_r1.py,
  2. what the capability door answers for the replay supply this build actually serves (the same
     reading my published g10 shape probe makes, re-run rather than re-quoted),
  3. the eight-file neighbour set, for the new-red question.

State changes are done with `git apply` / `git apply -R` on the committed product diff, so the two
sides differ by exactly that patch and nothing else.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import re
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_lane_ord0520_20260930/wt2")
BACKEND = TREE / "backend"
DBDIR = TREE.parent / "db"
PROBE = TREE / "tmp/g10_shape_probe_reread_r1.py"
PYTHON = pathlib.Path(r"D:/moodle/CityNexus/.venv/Scripts/python.exe")
OUT = TREE / "review/ord0520/OSMT_ARMS_AND_SUPPLY_ab_r1.json"

ARMS = "tests/test_qoder_ord0520_osm_type_bare_kind_r1.py"
NEIGHBOURS = [
    "tests/test_qoder_anywhere_capability_from_store.py",
    "tests/test_qoder_anywhere_discovery_truth.py",
    "tests/test_qoder_anywhere_contract_parity.py",
    "tests/test_qoder_anywhere_gates.py",
    "tests/test_ord0544_anchor_leg_shape_r1.py",
    "tests/test_qoder_anywhere_provider_truth.py",
    "tests/test_qoder_catalog_hydration.py",
    "tests/test_qoder_pending_destination_identity.py",
]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


def pytest(target, tag: str) -> dict:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S%f")
    db = DBDIR / ("_osmt-%s-%s.db" % (tag, stamp))
    env = dict(subprocess.os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([str(PYTHON), "-X", "utf8", "-m", "pytest", "-q", "-p", "no:randomly",
                           "--no-header", *target], cwd=str(BACKEND), env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = proc.stdout or ""
    # pytest prints "5 passed" with no failed clause at all when nothing failed, and "3 failed, 71
    # passed" otherwise -- one regex for both shapes, or the green run reads as an unparsed tail.
    failed = re.search(r"(\d+) failed", out)
    passed = re.search(r"(\d+) passed", out)
    for suffix in ("", "-wal", "-shm"):
        path = pathlib.Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    return {"rc": proc.returncode, "db": db.name,
            "failed": int(failed.group(1)) if failed else 0,
            "passed": int(passed.group(1)) if passed else None,
            "red_names": sorted(re.findall(r"FAILED \S+::(\S+)", out)),
            "line": ", ".join(part.group(0) for part in (failed, passed) if part)
            or out.strip()[-160:]}


def supply(tag: str) -> dict:
    """The door's buckets on the replay rows, read by the published probe rather than by me."""

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%H%M%S%f")
    db = DBDIR / ("_osmt-%s-%s.db" % (tag, stamp))
    env = dict(subprocess.os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env["CITYNEXUS_E2E_RUN_ID"] = db.stem.lstrip("_")
    env["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + db.as_posix()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run([str(PYTHON), "-X", "utf8", str(PROBE), str(BACKEND), "天津市"],
                          cwd=str(TREE.parent), env=env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    text = proc.stdout or ""
    hit = re.search(r"kinds_as_the_arm_reads_them (\{.*?\})", text)
    rows = re.search(r"places_rows (\d+)", text)
    miss = re.search(r"rows_missing_coordinates (\d+)", text)
    verdict = re.search(r"VERDICT (\S+)", text)
    for suffix in ("", "-wal", "-shm"):
        path = pathlib.Path(str(db) + suffix)
        if path.exists():
            path.unlink()
    return {"rc": proc.returncode, "db": db.name,
            "places_rows": int(rows.group(1)) if rows else None,
            "buckets_as_g10_reads_them": hit.group(1) if hit else None,
            "rows_missing_coordinates": int(miss.group(1)) if miss else None,
            "probe_verdict": verdict.group(1) if verdict else None}


def git_bytes(*args: str) -> bytes:
    """Raw bytes for anything that is a patch: text mode plus write_text() would flip CRLF and a
    stripped diff is a corrupt diff (both have bitten this lane before)."""

    return subprocess.run(["git", "-C", str(TREE), *args], capture_output=True).stdout


def main() -> int:
    head = git("rev-parse", "HEAD")
    base = git("rev-parse", "HEAD^")
    product_blob_patched = git("rev-parse", "HEAD:backend/app/anywhere_capability.py")
    product_blob_base = git("rev-parse", "%s:backend/app/anywhere_capability.py" % base)
    arms_blob = git("rev-parse", "HEAD:backend/tests/test_qoder_ord0520_osm_type_bare_kind_r1.py")
    # The supply reading reuses MY OWN published probe, extracted from the g10 refutation branch
    # rather than re-typed -- so the "before" buckets are the same measurement my g10 block shipped.
    PROBE.write_bytes(git_bytes("show",
                                "13e2b6610c25a3c97a8dbca1c58377c66ceec649:review/inflight-wait-r1/g10_shape_probe_r1.py"))
    probe_blob = git("hash-object", str(PROBE))
    assert probe_blob == git("rev-parse",
                             "13e2b6610c25a3c97a8dbca1c58377c66ceec649:review/inflight-wait-r1/g10_shape_probe_r1.py")
    patch_file = TREE.parent / "tmp/osmt_product.patch"
    patch_file.write_bytes(git_bytes("diff", "HEAD^", "HEAD", "--", "backend/app/anywhere_capability.py"))
    assert subprocess.run(["git", "-C", str(TREE), "apply", "--check", "-R", str(patch_file)],
                          capture_output=True).returncode == 0, "patch not reversible as read"

    states: dict[str, dict] = {}
    for state in ("tip_bytes", "patched"):
        if state == "tip_bytes":
            rc = subprocess.run(["git", "-C", str(TREE), "apply", "-R", str(patch_file)],
                                 capture_output=True).returncode
            assert rc == 0, "reverse apply failed"
        states[state] = {
            "product_blob_now": git("hash-object", "backend/app/anywhere_capability.py"),
            "colon_split_still_in_the_file": 'split(":", 1)' in
                (BACKEND / "app/anywhere_capability.py").read_text(encoding="utf-8"),
            "arms": pytest([ARMS], state + "-arms"),
            "real_supply": supply("supply-" + state),
            "neighbours": pytest(NEIGHBOURS, state + "-nbr"),
        }
        if state == "tip_bytes":
            assert subprocess.run(["git", "-C", str(TREE), "apply", str(patch_file)],
                                  capture_output=True).returncode == 0
            assert git("hash-object", "backend/app/anywhere_capability.py") == product_blob_patched

    before, after = states["tip_bytes"], states["patched"]
    report = {
        "measured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "measured_against_head": head,
        "parent_tip": base,
        "product_blob_patched": product_blob_patched,
        "product_blob_parent": product_blob_base,
        "arms_file_blob": arms_blob,
        "interpreter": str(PYTHON),
        "each_state": states,
        "arms_before": before["arms"]["line"],
        "arms_after": after["arms"]["line"],
        "arms_restored_to_green": after["arms"]["failed"] == 0,
        "arms_discriminate": before["arms"]["failed"] > 0,
        "supply_before": before["real_supply"]["buckets_as_g10_reads_them"],
        "supply_after": after["real_supply"]["buckets_as_g10_reads_them"],
        "supply_changed": before["real_supply"]["buckets_as_g10_reads_them"]
        != after["real_supply"]["buckets_as_g10_reads_them"],
        "neighbour_reds_before": before["neighbours"]["red_names"],
        "neighbour_reds_after": after["neighbours"]["red_names"],
        "new_red_names_from_this_patch": sorted(
            set(after["neighbours"]["red_names"]) - set(before["neighbours"]["red_names"])
        ),
    }
    report["verdict"] = (
        "DEFECT_MEASURED_AND_CLOSED_ON_REAL_SUPPLY"
        if report["arms_discriminate"] and report["arms_restored_to_green"] and report["supply_changed"]
        and not report["new_red_names_from_this_patch"]
        else "READ_THE_FIELDS"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "each_state"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
