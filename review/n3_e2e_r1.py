#!/usr/bin/env python3
"""Lane N3's e2e invocation of the commander's own runner.

Why a wrapper instead of running cmdr_e2e_r1.py directly: its port search starts at 4400 and walks 400
forwards, which is the commander's band (4400-4469) and touches B's and S2's. ORD-0357 was assigned
5470-5499 with the backend pair at +1000, so the only thing changed here is where a free pair is looked
for and where the per-arm evidence lands. The runner itself is imported untouched and stays read-only.
"""
import importlib.util
import os
import socket
import sys

RUNNER = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_e2e_r1.py"
LOW, HIGH = 5470, 5499


def _load():
    spec = importlib.util.spec_from_file_location("cmdr_e2e_r1", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bindable(p):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", p))
            return True
        except OSError:
            return False


def main():
    argv = sys.argv[1:]
    if "--wt" not in argv:
        print("USAGE: n3_e2e_r1.py --wt <worktree> --target e2e/<spec> [--tag n3]", file=sys.stderr)
        return 2
    wt = argv[argv.index("--wt") + 1]
    hit = None
    p = LOW
    while p <= HIGH:
        if _bindable(p) and _bindable(p + 1000):
            hit = p
            break
        p += 1
    if hit is None:
        print("NO_FREE_PORT in the N3 band %d-%d (each candidate also needs p+1000)" % (LOW, HIGH),
              file=sys.stderr)
        return 2
    # Evidence stays inside the lane directory the order names, and out of `reports/**`.
    os.environ["CITYNEXUS_EVIDENCE_DIR"] = os.path.join(wt, "review", "evidence").replace("\\", "/")
    mod = _load()
    mod.free_port = lambda base: hit
    sys.argv = ["cmdr_e2e_r1.py"] + argv
    print("N3_BAND_PICK frontend=%d backend=%d evidence_dir=%s"
          % (hit, hit + 1000, os.environ["CITYNEXUS_EVIDENCE_DIR"]))
    return mod.main()


if __name__ == "__main__":
    sys.exit(main())
