"""Why did that run stall: a matrix, not a story (CMDR 02:45 line 7 for this lane).

At 02:3x I reported a walkthrough run that sat for minutes and finally died on its own external cap.
My first explanations were narrations, and one of them (a leftover vite squatting the port) was real
but was NOT the cause of that particular stall.  This tool measures the candidates apart, one variable
per row, on this lane's own private stack:

  R1  control -- the shipped gate on a fresh store copy: green, and its wall seconds are the yardstick.
  R2  mechanism, capped -- put back the one line that read a cell which only exists on the fresh-write
      branch (this is today's helper, which caps a single read at five seconds) and run it at two
      different per-test ceilings.  Both fail in seconds at either ceiling: that is the repair working.
  R6/R7/R8  mechanism, uncapped -- the same absent cell read the way the instrument did at 02:3x, before the
      cap existed, at a 20 second, a 100 second and then the ceiling that actually shipped (300 s).  Same
      locator named at all three, wall tracking the ceiling.  That triple is the stall's shape, measured
      instead of narrated: R8 is the cost of one such cell in the run that died on its external cap.
  R3  branch control -- the same mutated line on a store that does NOT yet carry the place (so the cell
      exists): green at the short ceiling.  Together with R2 this pins "cell absent on the taken branch",
      not "this gate is slow".
  R4  environment control -- the shipped gate with HTTP(S)_PROXY pointed at a dead local port, then with
      the proxy variables stripped: comparable wall seconds and both green => proxy environment refuted.
  R5  the other stall, on purpose -- leave a vite bound to the gate's own frontend port and run the
      shipped gate.  Its config now declares `port:` and starts vite with `--strictPort`, so this dies in
      well under a second on a sentence naming the port; before that change the same collision sat for
      minutes, because vite moved ports on its own while the readiness probe kept polling a port that a
      foreign process owned.  Reaped and re-run green afterwards.

NAMED INSTRUMENT DEFECT, MEASURED, NOT NARRATED:  two of these runs were live at once at 05:3x while the
fixed ports (4916 / 4911) and the fixed store tags (r18 / r19) were shared.  That generation is kept in
`readouts/hang_cause_matrix_r1_overlap_contaminated_r1.json`: every row there, control included, fails at
rc 1 waiting for `getByTestId('poi-import')` -- the screen's own entry -- and none of them names the
mutated locator.  A row that reds on the entry cell is measuring my stack, not the product, so this tool
now picks a free frontend port, a free backend port and its own store tag per invocation and refuses to
start if it cannot bind them.

A SECOND DEFECT, SAME DISCIPLINE:  at 05:5x a hard-killed instance left its mutation sitting in the spec,
and the next instance inserted a copy on top of it.  That generation is kept in
`readouts/hang_cause_matrix_r1_leftover_mutation_contaminated_r1.json` -- three rows there collected zero
tests (a duplicate `const` is a SyntaxError), and its `capped_read_is_ceiling_independent` still reported
true off two rows that never ran anything, which is a vacuous predicate, not a measurement.  Both are
bolted: the run now refuses to start unless the spec on disk matches the published blob byte for byte, the
mutation is restored in a `finally`, and every cause-deciding predicate demands `tests_collected == 1` and
`failed == 1` alongside the locator it names.

Rows write one JSON matrix plus a console tail per row; nothing here ships a product byte.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0545/hang_cause_matrix_r1.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
SPEC = FRONTEND / "e2e/qoder-ord0545s4-poi-screen-walkthrough-r1.spec.ts"
READOUTS = ROOT / "review/ord0545/readouts"
DATA = pathlib.Path("D:/moodle/_qoder_newlane_ord0545_data")
# two of these runs on one machine collide on the gate's own vite port and quietly corrupt EACH OTHER's
# readings -- the rows then look like measurements of the product when they are measurements of a race
LOCK = DATA / "hang_cause_matrix.lock"
BASE_TIP = "06ad00b0267c2bef08d4cdcbae2e5a206ded8666"
CONFIG = "playwright.ord0545s4-walkthrough.config.ts"
# chosen per invocation by run_matrix(); 4916/4911 are only the lowest candidates.  Hardcoding them is
# what made a second live instance read the first one's stack instead of its own.
FRONTEND_PORT = 4916
BACKEND_PORT = 4911
STORE_TAG_A = "r18"
STORE_TAG_B = "r19"
STACK = "review/ord0533/lane_stack_r1.py"
PY = sys.executable

# the one line that caused it: an unconditional reach for a cell that exists only on the fresh-write leg
ANCHOR = "      // ---------- G the same tap again: a replay may not mint a second success sentence"
MUTANT = (
    '      const legacyUnconditional = await text(page.getByTestId("poi-import-added-source"));\n'
    '      wire.legacy_probe_length = legacyUnconditional.length;\n'
)
# the same reach WITHOUT the five second cap, i.e. the instrument shape that actually stalled at 02:3x:
# there the wait could only end when the configured per-test ceiling ended it
MUTANT_UNCAPPED = (
    '      const legacyUncapped = await page.getByTestId("poi-import-added-source").innerText();\n'
    '      wire.legacy_uncapped_length = legacyUncapped.length;\n'
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git(*args):
    proc = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, errors="replace")
    return proc.returncode, proc.stdout.strip()


def blob_bytes(rev: str, path: str) -> bytes:
    proc = subprocess.run(["git", "-C", str(ROOT), "show", rev + ":" + path], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("ABORT: cannot read " + rev + ":" + path + " -- " + proc.stderr.decode("utf-8", "replace")[:120])
    return proc.stdout


def listening_pids(port: int) -> list[str]:
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace").stdout
    pids = []
    for line in out.splitlines():
        cols = line.split()
        if len(cols) >= 5 and cols[0].upper() == "TCP" and cols[3].upper() == "LISTENING" \
                and cols[1].endswith(":" + str(port)):
            pids.append(cols[4])
    return sorted(set(pids))


def command_line(pid: str) -> str:
    probe = ("Get-CimInstance Win32_Process -Filter 'ProcessId=" + pid + "' | ForEach-Object { $_.CommandLine }")
    proc = subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                          capture_output=True, text=True, errors="replace")
    return " ".join((proc.stdout or "").split())[:160]


def pick_port(low: int) -> int:
    """Lowest port at or above `low` that nothing listens on and that this process can bind right now."""
    import socket
    for candidate in range(low, low + 60):
        if listening_pids(candidate):
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", candidate))
            except OSError:
                continue
        return candidate
    raise SystemExit("ABORT: no bindable port at or above " + str(low) + " -- named holders: "
                     + ", ".join(str(p) + "=" + ";".join(listening_pids(p)) for p in range(low, low + 60)))


def stack(mode: str, tag: str) -> dict:
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.update({"CITYNEXUS_ORD0533_TAG": tag, "CITYNEXUS_ORD0533_BASE_TIP": BASE_TIP,
                "CITYNEXUS_ORD0533_BACKEND_PORT": str(BACKEND_PORT)})
    proc = subprocess.run([PY, STACK, mode], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=300, env=env)
    out = proc.stdout + proc.stderr
    if mode == "--start":
        marker = re.search(r'"database_url": "sqlite:///(.+?)"', out)
        return {"rc": proc.returncode, "db": marker.group(1) if marker else None}
    killed = re.search(r'"killed": \[([^\]]*)\]', out)
    still = re.search(r'"still_listening": \[([^\]]*)\]', out)
    return {"rc": proc.returncode, "killed": killed.group(1) if killed else "", "still_listening": still.group(1) if still else ""}


def plan_places(db_path: str) -> list[str]:
    import sqlite3
    with sqlite3.connect(f"file:{pathlib.Path(db_path).as_posix()}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            "select p.name from activities a join places p on p.id = a.place_id where a.plan_version_id = "
            "(select active_plan_version_id from journeys where id='22222222-2222-4222-8222-222222222222')"
        ).fetchall()
    return sorted(r[0] for r in rows)


def gate(tag: str, test_timeout_ms: int | None, proxy_dead: bool, grep: str | None) -> dict:
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_ORD0545_TAG": tag,
        "CITYNEXUS_ORD0545_BASE_TIP": BASE_TIP,
        "CITYNEXUS_ORD0545S4_PORT": str(FRONTEND_PORT),
        "CITYNEXUS_ORD0545_BACKEND_PORT": str(BACKEND_PORT),
        "DEEPSEEK_API_KEY": "",
    })
    if proxy_dead:
        env["HTTP_PROXY"] = "http://127.0.0.1:1"
        env["HTTPS_PROXY"] = "http://127.0.0.1:1"
        env["NO_PROXY"] = ""
    cmd = ["node", "node_modules/@playwright/test/cli.js", "test", "-c", CONFIG]
    if test_timeout_ms:
        cmd += ["--timeout", str(test_timeout_ms)]
    if grep:
        cmd += ["-g", grep]
    started = time.time()
    try:
        done = subprocess.run(cmd, cwd=FRONTEND, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=(test_timeout_ms or 300000) / 1000 + 240, env=env)
        out = (done.stdout or "") + (done.stderr or "")
        code = done.returncode
    except subprocess.TimeoutExpired as exp:
        out = "".join(x.decode("utf-8", "replace") if isinstance(x, bytes) else (x or "")
                      for x in (exp.stdout, exp.stderr))
        code = "TIMEOUT"
    wall = round(time.time() - started, 1)
    (DATA / f"hang_{tag}.txt").write_text(out, encoding="utf-8", newline="\n")
    return {
        "tag": tag,
        "measured_at": now(),
        "command": " ".join(cmd),
        "test_timeout_ms": test_timeout_ms,
        "wall_seconds": wall,
        "rc": code,
        # `-g Wzh` leaves ONE test, and playwright prints "Running 1 test" for that -- a regex demanding
        # the plural read a real two-digit collection as 0, which is how a clean row can look vacuous
        "tests_collected": int(re.search(r"Running (\d+) tests?", out).group(1)) if re.search(r"Running (\d+) tests?", out) else 0,
        "passed": int(re.search(r"(\d+) passed", out).group(1)) if re.search(r"(\d+) passed", out) else 0,
        "failed": int(re.search(r"(\d+) failed", out).group(1)) if re.search(r"(\d+) failed", out) else 0,
        "waiting_for": sorted(set(re.findall(r"waiting for (getByTestId\('[a-z0-9-]+'\))", out))),
        "server_port_complaint": sorted(set(re.findall(r"(https?://\S+ is already used[^\n]{0,90})", out)))[:2],
        "tail": out.strip().splitlines()[-3:] if out.strip() else [],
    }


def pid_alive(pid: str) -> bool:
    probe = "Get-Process -Id " + pid + " -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }"
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", probe],
                         capture_output=True, text=True, errors="replace").stdout
    return bool(out.strip())


def main() -> int:
    if LOCK.exists():
        holder = "".join(ch for ch in LOCK.read_text(encoding="utf-8") if ch.isdigit())
        if holder and pid_alive(holder):
            raise SystemExit("ABORT: another instance holds " + str(LOCK) + " (live pid " + holder + ")")
        # a hard-killed instance leaves the lock behind; refusing to start forever is a worse failure than
        # taking it over, as long as the dead pid is named in the output
        print("lock held by dead pid " + holder + ": taking it over", flush=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8", newline="\n")
    try:
        return run_matrix()
    finally:
        if LOCK.exists():
            LOCK.unlink()


def run_matrix() -> int:
    global FRONTEND_PORT, BACKEND_PORT, STORE_TAG_A, STORE_TAG_B
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    FRONTEND_PORT, BACKEND_PORT = pick_port(4916), pick_port(4911)
    STORE_TAG_A, STORE_TAG_B = "x" + stamp + "a", "x" + stamp + "b"
    spec_before = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    published_sha = hashlib.sha256(blob_bytes(BASE_TIP, SPEC.relative_to(ROOT).as_posix())).hexdigest()
    # a hard-killed instance leaves its mutation sitting in the file; inserting on top of that declares the
    # same const twice, and every later row then measures my own wreckage instead of the product
    if spec_before != published_sha:
        raise SystemExit("ABORT: the walkthrough spec on disk is not the published bytes (disk "
                         + spec_before[:16] + " vs " + BASE_TIP + " as " + published_sha[:16]
                         + "); restore it from that blob and re-run")
    rows: dict[str, object] = {"base_tip": BASE_TIP, "started_at": now(), "spec_sha_before": spec_before,
                               "spec_sha_published": published_sha,
                               "pre_flight": {
                                   "frontend_port": FRONTEND_PORT,
                                   "backend_port": BACKEND_PORT,
                                   "store_tags": [STORE_TAG_A, STORE_TAG_B],
                                   "holders_at_entry": {str(p): [command_line(x) for x in listening_pids(p)]
                                                        for p in (4916, 4911)},
                                   "matrix_pid": os.getpid(),
                               },
                               "runs": []}
    text = SPEC.read_text(encoding="utf-8")
    assert ANCHOR in text, "the anchor moved; this tool must not invent a mutation point"

    def run_row(label: str, mutated: bool, timeout_ms, proxy_dead: bool, grep, mutant=MUTANT):
        original = None
        if mutated:
            original = SPEC.read_bytes()
            SPEC.write_text(text.replace(ANCHOR, mutant + ANCHOR, 1), encoding="utf-8", newline="\n")
        try:
            reading = gate(label, timeout_ms, proxy_dead, grep)
        finally:
            # restore even when the row throws: an aborted row used to leave the mutation in the file, and
            # the next row then inserted a second copy of the same const
            if mutated and original is not None:
                SPEC.write_bytes(original)
        reading["label"] = label
        reading["mutated"] = mutated
        if mutated:
            reading["restored"] = hashlib.sha256(SPEC.read_bytes()).hexdigest() == spec_before
        rows["runs"].append(reading)
        (READOUTS / "hang_cause_matrix_r1.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        print(label, "rc", reading["rc"], "wall", reading["wall_seconds"], "failed", reading["failed"],
              "waiting_for", reading["waiting_for"], flush=True)

    # R1 control: fresh copy of the canary, shipped gate, both locales
    up = stack("--start", STORE_TAG_A)
    rows["stack_" + STORE_TAG_A] = up
    run_row("R1_shiped_fresh_store", mutated=False, timeout_ms=None, proxy_dead=False, grep=None)
    db_after_r1 = plan_places(up["db"]) if up["db"] else []
    rows["plan_places_after_R1"] = db_after_r1

    # R3 branch control first, while the store is still clean: mutate and expect GREEN (cell exists)
    stack("--stop", STORE_TAG_A)
    up3 = stack("--start", STORE_TAG_B)
    rows["stack_" + STORE_TAG_B] = up3
    run_row("R3_mutated_cell_present_short_ceiling", mutated=True, timeout_ms=45000, proxy_dead=False, grep="Wzh")
    # one green shipped pass to reach the already-carried state
    run_row("R1b_shiped_second_write_leg", mutated=False, timeout_ms=None, proxy_dead=False, grep="Wzh")

    # R2 mechanism: same store state, same mutation, two different ceilings
    run_row("R2a_mutated_cell_absent_ceiling_20s", mutated=True, timeout_ms=20000, proxy_dead=False, grep="Wzh")
    run_row("R2b_mutated_cell_absent_ceiling_100s", mutated=True, timeout_ms=100000, proxy_dead=False, grep="Wzh")

    # R6/R7: the same missing cell read the way the instrument did it BEFORE the five second cap existed.
    # These two rows are the ceiling test: if the wait is Playwright auto-waiting on an absent locator, the
    # wall tracks the configured per-test ceiling.  R2a/R2b show the capped helper refuses to do that.
    run_row("R6_uncapped_missing_cell_ceiling_20s", mutated=True, timeout_ms=20000, proxy_dead=False,
            grep="Wzh", mutant=MUTANT_UNCAPPED)
    run_row("R7_uncapped_missing_cell_ceiling_100s", mutated=True, timeout_ms=100000, proxy_dead=False,
            grep="Wzh", mutant=MUTANT_UNCAPPED)
    # R8 is the third point, at the ceiling the shipped config actually carries, so the cost of the run
    # that died is a reading rather than something I multiply out in a sentence
    run_row("R8_uncapped_missing_cell_shipped_ceiling_300s", mutated=True, timeout_ms=300000, proxy_dead=False,
            grep="Wzh", mutant=MUTANT_UNCAPPED)

    # R4 environment control
    run_row("R4a_shiped_with_dead_proxy_env", mutated=False, timeout_ms=None, proxy_dead=True, grep="Wzh")
    run_row("R4b_shiped_without_proxy_env", mutated=False, timeout_ms=None, proxy_dead=False, grep="Wzh")

    # R5 the other stall, produced deliberately
    orphan = subprocess.Popen(
        ["node", "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(6)
    rows["orphan_vite_pid"] = orphan.pid
    run_row("R5_shiped_with_orphan_vite_on_port", mutated=False, timeout_ms=None, proxy_dead=False, grep="Wzh")
    orphan.kill()
    time.sleep(1)
    run_row("R5b_shiped_after_reaping_orphan", mutated=False, timeout_ms=None, proxy_dead=False, grep="Wzh")

    stack("--stop", STORE_TAG_B)
    rows["ended_at"] = now()
    rows["spec_sha_after"] = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    rows["spec_untouched"] = rows["spec_sha_after"] == spec_before
    (READOUTS / "hang_cause_matrix_r1.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    by = {r["label"]: r for r in rows["runs"]}
    capped_a = by.get("R2a_mutated_cell_absent_ceiling_20s", {})
    capped_b = by.get("R2b_mutated_cell_absent_ceiling_100s", {})
    unc_a = by.get("R6_uncapped_missing_cell_ceiling_20s", {})
    unc_b = by.get("R7_uncapped_missing_cell_ceiling_100s", {})
    unc_c = by.get("R8_uncapped_missing_cell_shipped_ceiling_300s", {})
    orphan = by.get("R5_shiped_with_orphan_vite_on_port", {})
    same_locator = bool(unc_a.get("waiting_for")) and unc_a.get("waiting_for") == unc_b.get("waiting_for") == unc_c.get("waiting_for")
    ran = all(r.get("tests_collected") == 1 and r.get("failed") == 1 for r in (unc_a, unc_b, unc_c))
    scales = unc_b.get("wall_seconds", 0) > unc_a.get("wall_seconds", 0) * 2
    conclusions = {
        # the stall's shape: one locator, waited on until whatever ceiling the run was given
        "uncapped_wait_tracks_the_ceiling": bool(same_locator and ran and scales),
        "the_two_rows_name_the_same_locator": bool(same_locator and ran),
        # three measured points on the same straight line: the wait IS the ceiling, and the shipped ceiling
        # is measured rather than multiplied out
        "ceiling_300s_point_measured": bool(
            unc_c.get("waiting_for") == unc_a.get("waiting_for") and unc_c.get("failed") == 1
            and unc_c.get("tests_collected") == 1
            and unc_a.get("wall_seconds", 0) < unc_b.get("wall_seconds", 0) < unc_c.get("wall_seconds", 0)
            and 295 <= unc_c.get("wall_seconds", 0) <= 340
            and unc_c.get("test_timeout_ms") == 300000),
        # the fix's shape: with a per-read cap the same absent cell fails in seconds at either ceiling --
        # and both rows must have ACTUALLY run one test and named the locator, because the contaminated
        # generation at 05:5x satisfied "waiting_for ==" with two rows that collected no test at all
        "capped_read_is_ceiling_independent": bool(
            capped_a.get("waiting_for") == ["getByTestId('poi-import-added-source')"]
            and capped_b.get("waiting_for") == ["getByTestId('poi-import-added-source')"]
            and capped_a.get("tests_collected") == capped_b.get("tests_collected") == 1
            and capped_a.get("failed") == capped_b.get("failed") == 1
            and capped_a.get("wall_seconds", 99) < 20 and capped_b.get("wall_seconds", 99) < 20
            and capped_b.get("test_timeout_ms") == 100000),
        # the other stall, which is what I first blamed: an occupied port, now a sub-second named failure
        "occupied_port_fails_fast_and_named": bool(orphan.get("rc") not in (0, None)
                                                   and orphan.get("wall_seconds", 99) < 5
                                                   and orphan.get("server_port_complaint")),
        "cell_present_means_no_stall": by.get("R3_mutated_cell_present_short_ceiling", {}).get("rc") == 0,
        "proxy_env_refuted": by.get("R4a_shiped_with_dead_proxy_env", {}).get("rc") == 0,
        # a row may only ever name the cell it was pushed at; the screen's own ENTRY testid showing up in
        # any row is the 05:3x signature -- that run was reading someone else's stack, not the product
        "no_row_names_the_screen_entry": not any("getByTestId('poi-import')" in r.get("waiting_for", [])
                                              for r in rows["runs"]),
        "shipped_gate_green_throughout": all(by[k]["rc"] == 0 for k in
                                             ("R1_shiped_fresh_store", "R1b_shiped_second_write_leg",
                                              "R4b_shiped_without_proxy_env", "R5b_shiped_after_reaping_orphan")
                                             if k in by),
    }
    rows["conclusions"] = conclusions
    (READOUTS / "hang_cause_matrix_r1.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps(conclusions, ensure_ascii=False), "spec_untouched", rows["spec_untouched"], flush=True)
    # the exit code is gated only on the rows that decide the stall's cause; R4/R5 are reported as
    # measured facts, because a dead proxy in the environment can legitimately break browser navigation
    # and an occupied port is a different failure than the one being explained
    needed = ("uncapped_wait_tracks_the_ceiling", "the_two_rows_name_the_same_locator",
              "ceiling_300s_point_measured",
              "capped_read_is_ceiling_independent", "cell_present_means_no_stall",
              "shipped_gate_green_throughout", "no_row_names_the_screen_entry")
    return 0 if all(conclusions[k] for k in needed) and rows["spec_untouched"] else 1


if __name__ == "__main__":
    sys.exit(main())
