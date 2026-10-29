"""Bolt the whole-tree frontend typecheck onto the release gate.

The gate has only ever run tsconfig.check.json, which names five files, so every other source file
could reach a release with an untypechecked tree while the job still printed green.  The broad config
already exists and passes here, so the door can carry it without weakening anything: the narrow step
stays, and a refusal in the broad pass now blocks the release.
"""

import io
import sys

WORKFLOW = r"D:\moodle\_cmdr_rescue_v3_1022\.github\workflows\v3-rescue-release-gate.yml"

ANCHOR = "      - name: Vite production build\n"
STEP = (
    "      - name: Typecheck every file under src, not the five named ones\n"
    "        # tsconfig.check.json lists five files, so the rest of src/ could reach a release while\n"
    "        # this job still reported green. The broad config was measured clean at the same tip as\n"
    "        # this step was added (receipt trial/results/20261026_gozero/bx172-broad-typecheck.txt),\n"
    "        # so carrying it here adds a refusal, not a new red.\n"
    "        run: npx tsc -p tsconfig.typecheck.json --noEmit\n"
)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(WORKFLOW, encoding="utf-8", newline="").read()
    if "tsconfig.typecheck.json" in text:
        print("ABORT the broad typecheck step is already in the gate")
        return 4
    if "\r\n" in text:
        print("ABORT the workflow is not LF-only")
        return 6
    if text.count(ANCHOR) != 1:
        print("ABORT anchor hits=%d" % text.count(ANCHOR))
        return 5
    updated = text.replace(ANCHOR, STEP + ANCHOR, 1)
    io.open(WORKFLOW, "w", encoding="utf-8", newline="").write(updated)
    read_back = io.open(WORKFLOW, encoding="utf-8", newline="").read()
    if read_back.replace(STEP, "", 1) != text:
        print("ABORT taking the inserted step back does not give the original bytes")
        return 7
    print("INSERTED size=%d->%d step_hits=%d" % (
        len(text),
        len(read_back),
        read_back.count("npx tsc -p tsconfig.typecheck.json --noEmit"),
    ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
