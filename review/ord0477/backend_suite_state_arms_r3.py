"""ORD-0477 r3 -- the two arms the set difference flagged, run on their own, three times, both sides.

The suite's set difference said one arm is red on the candidate in one pass and absent from both tip
passes, and one arm is red on the tip in both passes and absent from the candidate. Neither reading can
be attributed to this order by looking at it once: both arms are state-sensitive (they measure a
generation job's shape and a second uvicorn worker over HTTP, so what they see depends on what ran
before them in the same process pool and which ports were free at that minute). The suite's own two
passes already disagree about both of them.

So the question is asked the only way that answers it: run each arm alone, three times, in each tree,
with the same interpreter and env, and report pass/pass/pass or the failure. `three isolated passes green
on both sides` means the difference is the suite's ordering, not this order's code -- and the block says
exactly that, with the runs attached, rather than writing "no new reds" over a reading that showed one.

usage: python ord0477_flaky_check_r3.py
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO_PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
REPORT = LANE / "run/ord0477_flaky_check_r3.txt"
TREES = {
    "tip": LANE / "tipcut_7862c6de",
    "candidate": LANE / "ord0477cut_7862c6de",
}
ARMS = [
    "tests/test_qoder_ord224_g3_generation_measurement.py::test_shape_a_terminal_job_then_five_requests_is_two_generations_not_one",
    "tests/test_qoder_g3_xproc_http.py::test_g3_xproc_two_uvicorn_workers_over_http_share_one_operation",
]
PASSES = 3


def main() -> int:
    lines = ["passes=%d interpreter=%s" % (PASSES, REPO_PY), ""]
    verdicts = {}
    for side, tree in TREES.items():
        for arm in ARMS:
            results = []
            for index in range(1, PASSES + 1):
                done = subprocess.run(
                    [REPO_PY, "-m", "pytest", arm, "-q", "--no-header", "-p", "no:cacheprovider"],
                    cwd=str(tree / "backend"), capture_output=True, text=True,
                    encoding="utf-8", errors="replace",
                    env=dict(
                        {k: v for k, v in os.environ.items() if k not in
                         ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy",
                          "DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY")},
                        PYTHONPATH=str(tree / "backend"),
                        CITYNEXUS_AI_ENABLED="false",
                    ),
                )
                tail = [line for line in (done.stdout or "").splitlines() if " passed" in line or " failed" in line or " error" in line]
                state = "GREEN" if done.returncode == 0 else "RED"
                results.append(state)
                lines.append("%s pass%d %s -> %s | %s" % (side, index, arm.split("::")[-1][:52], state, (tail[-1] if tail else "")[:110]))
            verdicts[(side, arm)] = results
    lines.append("")
    for (side, arm), results in verdicts.items():
        lines.append("verdict %s %s = %s" % (side, arm.split("::")[-1][:52], "/".join(results)))
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.buffer.write(text.encode("utf-8", "replace"))
    return 0


import os  # noqa: E402  (imported after the docstring so the header stays the explanation)

if __name__ == "__main__":
    raise SystemExit(main())
