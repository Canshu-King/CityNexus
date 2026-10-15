#!/usr/bin/env python3
r"""How often does ``tests/test_qoder_g3_xproc_http.py`` go RED when it runs alone -- on my tip and
on the fusion baseline tip?  Same command, same interpreter, one variable: which tree.

WHY THIS FILE EXISTS.  ``slice3_gates_r1.py`` reported one red name sitting in both of this tip's
full-suite samples and in neither of the previous tip's *intersection*, and its first label made that
read as "new and stable".  The membership table showed the truth: the arm was red in 1 of the
previous tip's 2 samples too, so it is a flipper, not a newcomer.  "Flipper" is a claim about a
mechanism, and the mechanism here is readable in the source: ``_wait_for_serving`` polls the child's
health route with ``_http(...)``, and ``_http`` catches only ``urllib.error.HTTPError`` (a docstring
in that file even says 4xx/5xx are readings, not exceptions to swallow).  A ``ConnectionRefusedError``
from the very first poll -- before uvicorn has bound the port -- therefore escapes the poll loop, and
neither the ``READY_DEADLINE_S = 120.0`` retry window nor the "the child exited" branch ever speaks.
Whether that fires is a race between the parent's first poll and the child's bind, so it should be
counted, not argued.

The single variable that matters for my own slice: the child imports ``app.main``, and a bigger
``app.main`` binds later, so a transplant CAN raise this arm's fire rate without breaking anything.
These numbers say by how much, on this machine, right now.  Read them against the two-sample suite
difference (slice2 1/2, slice3 2/2) before concluding anything.

Nothing here edits another lane's test.  The one-line fix -- catch ``URLError`` inside the poll --
belongs to ORD-0224's owner, and I report it instead of silently changing a gate other lanes read.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT.parent
TREES = {
    "tip": ROOT,
    "baseline": STAGING.parent / "_qoder_fusion_baseline" / "CityNexus",
}
PYTHON = STAGING.parent / "CityNexus" / ".venv" / "Scripts" / "python.exe"
TARGET = "tests/test_qoder_g3_xproc_http.py"
TAIL = re.compile(r"^\s*(\d+ (?:failed|passed|skipped|error).{0,60}?in ([\d.]+)s)\s*$", re.M)
BASELINE_TIP = "594f9a4e75"


def sha(tree: Path) -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=tree,
                          capture_output=True, text=True).stdout.strip()


def file_digest(tree: Path) -> str:
    return hashlib.sha256((tree / "backend" / TARGET).read_bytes()).hexdigest()[:16]


def untouched_by_this_slice() -> None:
    """Did the transplant touch this arm's code at all?  A diff of one file is a stronger answer
    than any timing experiment: if the file is byte-identical to the baseline's, the baseline can
    reproduce its flake without any of my code in the picture."""
    diff = subprocess.run(["git", "diff", "--stat", f"{BASELINE_TIP}..HEAD", "--",
                           "backend/" + TARGET], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    print("XPROC_ARM_DIFF_VS_BASELINE", repr(diff) if diff else "(empty: this slice did not touch it)")
    for name, tree in TREES.items():
        if (tree / "backend" / TARGET).exists():
            print(f"XPROC_ARM_SHA256_16 {name}", file_digest(tree))


def http_probe(label: str, tree: Path) -> None:
    """Call the arm's own `_http` against a port nobody is listening on, in each tree.

    This is the deterministic half of the claim.  The poll loop's first iteration cannot return a
    "not yet" reading: the connection itself raises, and `_http` only catches HTTPError, so the
    exception leaves `_wait_for_serving` and the 120 s retry window is never reached.  Which attempt
    actually hits that window is a race, so we do not gamble on reproducing it -- we show the hole."""
    script = r"""
import socket, sys, urllib.error
sys.path.insert(0, sys.argv[1])
import importlib
m = importlib.import_module("test_qoder_g3_xproc_http")
probe = socket.socket(); probe.bind(("127.0.0.1", 0)); port = probe.getsockname()[1]; probe.close()
for name in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "OPENAI_API_KEY"):
    import os; os.environ.pop(name, None)
try:
    got = m._http("GET", port, "/api/v1/health", timeout=2.0)
    print("PROBE returned a reading:", got[0])
except urllib.error.HTTPError as exc:
    print("PROBE HTTPError (caught path, still a reading):", exc.code)
except BaseException as exc:
    print(f"PROBE ESCAPED as {type(exc).__module__}.{type(exc).__name__}: "
          f"{str(exc)[:90]!r} -> the poll loop cannot survive this")
"""
    result = subprocess.run([str(PYTHON), "-c", script, str(tree / "backend" / "tests")],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = (result.stdout.strip().splitlines() or ["(no output)"])[-1]
    print(f"XPROC_HTTP_PROBE {label} {line} rc={result.returncode}")
    if result.returncode:
        print("XPROC_HTTP_PROBE_STDERR", label, (result.stderr or "")[-300:].replace("\n", " "))


def one_attempt(label: str, tree: Path, index: int) -> tuple[int, float, str, int]:
    """(rc, seconds, verdict, refusal_escaping_poll_count)

    BUG RECORDED HERE: the log name first used ``tree.name``, which is ``CityNexus`` in BOTH trees,
    so the baseline's attempt silently overwrote the tip's evidence file -- and because ``pytest -q``
    prints no rootdir, the surviving log could not say which tree produced it.  The label is passed
    in now, and each log starts with a self-describing header line instead of relying on its name.
    """
    started = time.perf_counter()
    env = dict(os.environ)
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    env.pop("OPENAI_API_KEY", None)
    env["CITYNEXUS_AI_ENABLED"] = "false"
    env["PYTHONIOENCODING"] = "utf-8"
    db = STAGING / f"_xproc_floor_{label}_{index}_{uuid.uuid4().hex[:8]}.db"
    env["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    log = STAGING / f"_xproc_floor_{label}_{index}.log"
    if db.exists():
        db.unlink()
    with log.open("wb") as handle:
        handle.write(f"# tree={label} sha={sha(tree)} target={TARGET} "
                     f"db={db.as_posix()}\n".encode("utf-8"))
        handle.flush()
        proc = subprocess.run([str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", TARGET],
                              cwd=str(tree / "backend"), env=env,
                              stdout=handle, stderr=subprocess.STDOUT)
    seconds = time.perf_counter() - started
    text = log.read_text(encoding="utf-8", errors="replace")
    tail = TAIL.search(text)
    summary = tail.group(1) if tail else "(no tail line)"
    # The leak signature AND the frame, counted from the saved log rather than from memory:
    # `:401 -> :195 -> :84` is the call site -> the poll -> the raise, which is the hole itself.
    leaks = len(re.findall(r"ConnectionRefusedError", text))
    frame = " ".join(re.findall(r"test_qoder_g3_xproc_http\.py:(\d+)", text)[:6])
    verdict = "GREEN" if proc.returncode == 0 else "RED"
    db.unlink(missing_ok=True)
    return proc.returncode, seconds, f"{verdict} ({summary}) frame[{frame}] -> {log.name}", leaks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=8)
    arguments = parser.parse_args()

    print("XPROC_FLOOR_TARGET", TARGET)
    print("XPROC_PYTHON", str(PYTHON), "EXISTS", PYTHON.exists())
    untouched_by_this_slice()
    for name, tree in TREES.items():
        if (tree / "backend" / TARGET).exists():
            http_probe(name, tree)
    totals = {}
    for name, tree in TREES.items():
        if not (tree / "backend").exists():
            print(f"XPROC_FLOOR {name} TREE_MISSING {tree}")
            continue
        if arguments.repeat <= 0:
            continue
        print(f"XPROC_FLOOR {name} sha={sha(tree)} repeat={arguments.repeat}")
        reds, leaks, seconds = 0, [], []
        for index in range(1, arguments.repeat + 1):
            rc, elapsed, line, leak_count = one_attempt(name, tree, index)
            seconds.append(elapsed)
            leaks.append(leak_count)
            reds += 1 if rc != 0 else 0
            print(f"  attempt {index:2d} rc={rc} {elapsed:5.1f}s refusal_frames={leak_count} {line}")
        totals[name] = (reds, arguments.repeat, leaks, seconds)
        print(f"XPROC_SOLO_RED {name} {reds}/{arguments.repeat}")
        print(f"XPROC_SOLO_READINESS_LEAK_REDS {name} "
              f"{sum(1 for value in leaks if value)}/{reds} "
              f"(of the reds, how many died on a ConnectionRefusedError inside the poll)")
        print(f"XPROC_SOLO_SECONDS_MEDIAN {name} {statistics.median(seconds):.1f}")
    if len(totals) == 2:
        (r1, n1, _, _), (r2, n2, _, _) = totals["tip"], totals["baseline"]
        print(f"XPROC_FLOOR_RATIO tip {r1}/{n1} baseline {r2}/{n2}")
        print("XPROC_FLOOR_READING: a quiet machine gives this arm ~0/8 on BOTH trees -- the race "
              "needs load, which is why it fires inside the full suite and not alone.  So the floor "
              "says 'nothing about my slice is needed for it to break', and the PROBE lines above "
              "say why.  Neither is a p-value.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
