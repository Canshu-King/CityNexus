"""Probe whether the Q43 door ever checks that a cited path exists, and record what it actually did.

Block #375 passed this door green while carrying six coordinates whose directory was written twice, so the
path it named was not on disk.  Before saying anything about whose gate does what, run the shape: the same
claim sentence, four different coordinate targets, and the door's own verdict for each.

  real path            trial/results/20261026_gozero/bw301-…txt:148   exists, line exists
  doubled directory    …gozero/trial/results/…gozero/bw301-…txt:148   does not exist (the #375 shape)
  no such file         trial/results/no-such-file-here.txt:148        does not exist at all
  line out of range    bw301-…txt:99999                               file exists, that line does not

The receipt is the artifact: each arm prints os.path.exists as measured here, the door's verbatim verdict
line and its exit code, so the claim "the shape gate does not look at existence" is something a reader can
re-run rather than something I asserted.
"""

import hashlib
import io
import os
import re
import subprocess
import sys
import tempfile

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REF = r"D:/moodle/_qoder_cmdr_ref_20260921"
RULER = os.path.join(REF, "live_checks", "claim_coordinate_check_r7.py")
GOZERO = "trial/results/20261026_gozero"
RECEIPT = os.path.join(ROOT, GOZERO, "bw341-what-the-q43-door-accepts-as-a-coordinate.txt")
REAL = GOZERO + "/bw301-this-sessions-blocks-landed.txt"
DOUBLED = GOZERO + "/" + REAL
GHOST = "trial/results/no-such-file-here.txt"

ARMS = (
    ("real_path", REAL, 148, True, True),
    ("doubled_directory", DOUBLED, 148, False, None),
    ("no_such_file", GHOST, 148, False, None),
    ("line_out_of_range", REAL, 99999, True, False),
)
VERDICT = re.compile(r"(Q43_GATE_GREEN|Q43_GATE_RED|NO_CLAIM_FOUND)")
CLAIMS = re.compile(r"claims checked (\d+)")


def read(rel):
    return io.open(os.path.join(ROOT, rel.replace("/", os.sep)), encoding="utf-8",
                   errors="replace").read()


def run_arm(box, name, path, line):
    text = ("### 探针 %s\n\n"
            "- 读数：共 46 条记录，逐条坐标见 %s:%d，另有 12 条待点单\n" % (name, path, line))
    probe = os.path.join(box, "probe_%s.md" % name)
    io.open(probe, "w", encoding="utf-8", newline="\n").write(text)
    done = subprocess.run([sys.executable, RULER, "--text", probe], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    verdict = VERDICT.search(done.stdout)
    claims = CLAIMS.search(done.stdout)
    if not verdict or not claims:
        raise SystemExit("ABORT the door printed no verdict for arm %s: %r"
                         % (name, (done.stdout or done.stderr)[-200:]))
    exists = os.path.exists(os.path.join(ROOT, path.replace("/", os.sep)))
    in_range = None
    if exists:
        in_range = line <= len(read(path).split("\n"))
    return {"text": text, "verdict": verdict.group(1), "claims": int(claims.group(1)),
            "rc": done.returncode, "exists": exists, "in_range": in_range}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not os.path.exists(RULER):
        raise SystemExit("ABORT the ruler under probe is not on disk: %s" % RULER)
    box = tempfile.mkdtemp()
    results = [(name, path, line, run_arm(box, name, path, line)) for name, path, line, _e, _r in ARMS]

    for (name, path, line, got), (_n, _p, _l, expect_exists, expect_range) in zip(results, ARMS):
        if got["exists"] != expect_exists:
            raise SystemExit("ABORT arm %s exists=%s, which is not the shape this probe was written to "
                             "test (%s)" % (name, got["exists"], expect_exists))
        if expect_range is not None and got["in_range"] != expect_range:
            raise SystemExit("ABORT arm %s line-in-range=%s but the file was expected to read %s"
                             % (name, got["in_range"], expect_range))
    greens = [name for name, _p, _l, got in results if got["verdict"] == "Q43_GATE_GREEN"]
    reds = [name for name, _p, _l, got in results if got["verdict"] != "Q43_GATE_GREEN"]
    if len(greens) != len(results):
        raise SystemExit("ABORT not every arm passed - the door does discriminate after all: red %s" % reds)

    sha = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    ruler_bytes = io.open(RULER, "rb").read()
    out = ["Q43 COORDINATE DOOR - WHAT A GREEN VERDICT DOES AND DOES NOT CHECK  bw341",
           "door %s (bytes=%d, sha1 of these local bytes %s)"
           % (RULER, len(ruler_bytes), hashlib.sha1(ruler_bytes).hexdigest()),
           "generation of the tree holding these artifacts: git object %s" % sha,
           "",
           "one claim sentence, four coordinate targets; the sentence is identical in every arm:"]
    for name, path, line, got in results:
        out += ["", "ARM %s" % name,
                "  cited as            %s:%d" % (path, line),
                "  path on disk here   %s" % got["exists"],
                "  that line in file   %s" % ("n/a (no file)" if got["in_range"] is None
                                              else got["in_range"]),
                "  door verdict        %s  claims=%d rc=%d" % (got["verdict"], got["claims"], got["rc"]),
                "  claim sentence      %s" % got["text"].split("\n")[2].strip()]
    out += ["",
            "READ: all %d arms came back Q43_GATE_GREEN, including the arm whose file does not exist and "
            "the arm whose line number is beyond the end of a real file. So this door's coordinate arm "
            "judges shape only: it asks whether a number is written next to something that looks like a "
            "file name, not whether that path is on disk or how long the file is."
            % len(results),
            "WHAT THAT EXPLAINS: block #375 carried coordinates whose directory was written twice and still "
            "passed this door green - the doubled_directory arm above is that exact shape. The per-coordinate "
            "list is in the erratum block that followed it.",
            "NOT A JUDGEMENT ABOUT THE DOOR'S SCOPE: it is a shape gate by design elsewhere (it pins "
            "retrievable git objects and anchors per claim); whether it should grow a path-exists arm is "
            "the commander's call, not mine, and nothing here was changed in the door itself.",
            "WHERE MY SIDE NOW CHECKS IT: the block generator for this shift refuses to post a block whose "
            "cited path is missing or whose cited line is past the end of the file.",
            "",
            "TALLY arms=%d green=%d red=0",
            ""]
    out[-2] = out[-2] % (len(results), len(greens))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out))
    back = io.open(RECEIPT, encoding="utf-8").read()
    if "Q43_GATE_GREEN" not in back or sha not in back:
        raise SystemExit("ABORT the receipt does not carry its own verdicts or its generation")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
