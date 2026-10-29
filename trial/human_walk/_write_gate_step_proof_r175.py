"""Record the runner's own step-level result for the gate step added this shift.

A local pass is not the same claim as 'the door runs it and says success', so the receipt is written
from the workflow API's job and step objects, naming the job, the step and its conclusion verbatim.
"""

import io
import json
import subprocess
import sys

RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bx175-gate-step-proof.txt"
RUN = "40801751920"
NEW_STEP = "Typecheck every file under src, not the five named ones"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    proc = subprocess.run(
        ["gh", "run", "view", RUN, "--json", "status,conclusion,headSha,url,jobs"],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        print("ABORT gh said: %s" % proc.stderr[:300])
        return 3
    data = json.loads(proc.stdout)
    steps = []
    for job in data.get("jobs", []):
        for step in job.get("steps", []):
            steps.append((job.get("name"), step.get("name"), step.get("conclusion")))
    hits = [entry for entry in steps if entry[1] == NEW_STEP]
    lines = [
        "RELEASE GATE STEP PROOF bx175",
        "RUN_ID %s" % RUN,
        "HEAD_SHA %s" % data.get("headSha"),
        "RUN_STATUS %s RUN_CONCLUSION %s" % (data.get("status"), data.get("conclusion")),
        "URL %s" % data.get("url"),
        "JOBS %d STEPS %d" % (len(data.get("jobs", [])), len(steps)),
        "NEW_STEP_HITS %d" % len(hits),
    ]
    for job_name, step_name, conclusion in hits:
        lines.append("  JOB %s | STEP %s | CONCLUSION %s" % (job_name, step_name, conclusion))
    for job_name, step_name, conclusion in steps:
        if step_name and "Post " not in step_name:
            lines.append("  step | %s | %s" % (step_name, conclusion))
    if len(hits) != 1 or hits[0][2] != "success":
        print("ABORT the new step did not appear exactly once with a success conclusion")
        for line in lines:
            print(line)
        return 4
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
