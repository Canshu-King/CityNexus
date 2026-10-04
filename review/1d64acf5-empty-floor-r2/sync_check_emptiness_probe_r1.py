# -*- coding: utf-8 -*-
"""Is my own landed self-check green when BOTH sides carry no content?

Leg A (real run): the shipped `check_sync` pointed at a zero-byte local ledger while the remote holds the real
    ledger - it must not answer CURRENT.
Leg B (faithful replica): the decision block is taken out of the same file by exact line range (the `pairs`
    construction through the three-way verdict), dedented uniformly and exec'd with both sides' blobs equal to
    the blob of an empty file.  A verdict read out of a replica is a prediction about the shipped file.
Leg C (the proposed floor, same replica): with a "both sides carry no content" refuse inserted, the same input
    must now be refused.  Positive control: the untouched replica must still say CURRENT for real bytes.

Nothing here writes the real ledger, a ref, or the mirror.
"""
import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(WT, "tools", "cnx_ledger_mirror_sync_check_r1.py")
TOKEN = os.path.join(r"D:\moodle\_qoder_recovery_20260919", ".api_tok_20260920")
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
OUT = os.path.join(HERE, "sync_check_emptiness_probe_r1.json")
EMPTY_BLOB = hashlib.sha1(b"blob 0" + bytes([0])).hexdigest()


def blob_of(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + bytes([0]) + raw).hexdigest()


def extract_block():
    lines = io.open(TOOL, encoding="utf-8").read().splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.strip().startswith('pairs = [("local_0 vs remote_1"'))
    i1 = next(i for i, l in enumerate(lines) if i > i0 and "verdict = DIVERGED" in l)
    block = lines[i0:i1 + 1]
    start, end = i0 + 1, i1 + 1
    if len(block) > 30:
        raise SystemExit("ABORT: extracted %d lines, that is not the decision block" % len(block))
    text = "\n".join(block)
    for must in ("verdict = CURRENT", "verdict = LAGGING", "verdict = DIVERGED", "matched = ["):
        if must not in text:
            raise SystemExit("ABORT: extracted block lost %r" % must)
    ded = textwrap.dedent(text)
    ast.parse(ded)
    return {"start": start, "end": end, "lines": len(block), "parse": "ok",
            "digest": hashlib.sha1(ded.encode("utf-8")).hexdigest()[:16], "ded": ded}


def run_replica(ded, local_blobs, remote_blobs, snaps, floor=""):
    """`snaps` is only used through len() inside the extracted block, so a list of the right length is
    a faithful stand-in; the blobs are the real inputs."""
    ns = {"verdict": None, "CURRENT": "CURRENT", "LAGGING": "LAGGING", "DIVERGED": "DIVERGED",
          "EMPTY_BLOB": EMPTY_BLOB}
    src = ("local_blobs = %r\nremote_blobs = %r\nsnaps = %r\n" % (local_blobs, remote_blobs, snaps)) \
        + floor + ded
    exec(compile(src, "verdict_replica", "exec"), ns)
    return ns["verdict"]


def leg_a_real():
    tmp = tempfile.mkdtemp(prefix="s4_empty_ledger_")
    empty = os.path.join(tmp, "empty_ledger.md")
    io.open(empty, "w", encoding="utf-8", newline="\n").write("")
    size = os.path.getsize(empty)
    env = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    p = subprocess.run([sys.executable, TOOL, "--local", empty, "--reads", "1", "--token-file", TOKEN],
                       capture_output=True, env=env, timeout=900)
    out = p.stdout.decode("utf-8", "replace").strip()
    os.remove(empty)
    os.rmdir(tmp)
    return {"local_file_bytes": size, "rc": p.returncode, "stdout_tail": out[-260:],
            "stderr_tail": p.stderr.decode("utf-8", "replace")[-200:],
            "answered_current": '"verdict": "CURRENT"' in out}


def main():
    b = extract_block()
    ded = b["ded"]
    three, two = [EMPTY_BLOB] * 3, [EMPTY_BLOB] * 2
    verdict_b = run_replica(ded, three, two, [0, 0, 0])
    floor = ("if all(x == EMPTY_BLOB for x in local_blobs + remote_blobs):\n"
             "    raise SystemExit('ABORT: both sides carry no content, that is not CURRENT')\n")
    try:
        verdict_c = run_replica(ded, three, two, [0, 0, 0], floor=floor)
        refused_c, detail_c = False, "no refusal, verdict=%s" % verdict_c
    except SystemExit as e:
        refused_c, detail_c = True, str(e)[:150]
    rb = blob_of(io.open(LEDGER, "rb").read())
    verdict_pos = run_replica(ded, [rb] * 3, [rb] * 2, [0, 0, 0])
    a = leg_a_real()
    R = {"tool": "tools/cnx_ledger_mirror_sync_check_r1.py",
         "tool_blob": blob_of(io.open(TOOL, "rb").read()), "empty_blob": EMPTY_BLOB,
         "real_ledger_blob": rb,
         "extract": {k: v for k, v in b.items() if k != "ded"},
         "leg_a_real_one_sided_empty": a,
         "leg_b_replica_both_empty": {"fed_local_len": len(three), "fed_remote_len": len(two),
                                      "verdict": verdict_b},
         "leg_c_replica_with_floor": {"refused": refused_c, "detail": detail_c},
         "positive_control_real_bytes": {"verdict": verdict_pos}}
    R["summary"] = {
        "real_run_did_not_answer_current": not a["answered_current"],
        "replica_answers_current_on_both_empty": verdict_b == "CURRENT",
        "proposed_floor_refuses_both_empty": refused_c,
        "positive_control_still_current": verdict_pos == "CURRENT"}
    json.dump(R, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(R, ensure_ascii=False, indent=1))
    ok = (R["summary"]["real_run_did_not_answer_current"] and R["summary"]["proposed_floor_refuses_both_empty"]
          and R["summary"]["positive_control_still_current"])
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
