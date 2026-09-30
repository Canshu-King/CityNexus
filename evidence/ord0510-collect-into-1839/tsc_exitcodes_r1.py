"""Record the two `tsc` runs as exit codes and byte sizes, not as a citation to an empty file.

Both configs answer with no output when they are clean, so the receipts beside them are 0-byte files and
their git blob is the empty blob -- naming that blob as if it were evidence would be a coordinate that
proves nothing.  This runs both configs, records the exit code, the byte size and the blob together, so
the claim in the block is "exit 0 and 0 bytes of output", which is what was actually observed.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0510"
FRONT = r"D:\moodle\_qoder_lane_S4_0926\wt0510\frontend"
NUL = chr(0).encode()
CONFIGS = [("tsconfig.check.json", "npm run typecheck"),
           ("tsconfig.typecheck.json", "npm run typecheck:all")]


def main():
    out = {"tree": FRONT, "tree_head": subprocess.run(
        ["git", "-C", FRONT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "runs": []}
    for cfg, npm in CONFIGS:
        dest = os.path.join(WORK, "tsc_out_%s.txt" % cfg.replace(".json", "").replace("tsconfig.", ""))
        r = subprocess.run(["node", os.path.join(FRONT, "node_modules", "typescript", "bin", "tsc"),
                            "-p", cfg, "--noEmit"], capture_output=True, timeout=1800, cwd=FRONT)
        body = r.stdout + r.stderr
        io.open(dest, "wb").write(body)
        blob = hashlib.sha1(b"blob %d" % len(body) + NUL + body).hexdigest()
        out["runs"].append({"config": cfg, "npm_script": npm, "exit_code": r.returncode,
                            "output_bytes": len(body), "output_blob": blob,
                            "empty_blob": blob == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
                            "receipt": os.path.basename(dest)})
    io.open(os.path.join(WORK, "tsc_exitcodes_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if all(x["exit_code"] == 0 and x["output_bytes"] == 0 for x in out["runs"]) else 1


if __name__ == "__main__":
    sys.exit(main())
