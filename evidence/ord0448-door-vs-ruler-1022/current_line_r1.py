"""Does the lost cell still matter on the line as it stands now?

Every reading in this delivery was taken at `0fee131d...`, which was the authoritative line when the order
arrived; the publish step read the line at a different sha, so the claim has to be re-taken there or stated
as pinned to the older one. Two rulers over one export of the CURRENT line: the door's pinned r7b and my
newest published r7b4.
"""
import glob
import io
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
REF = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
LINE = "mirror/integration-frontend-apple-pass1"
EXPORT = os.path.join(WORK, "_line_export")
PAIRS = [("r7b", "ui_exposure_taint_ast_r7b.cjs"), ("r7b4", "ui_exposure_taint_ast_r7b4.cjs")]
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*", PYTHONIOENCODING="utf-8")


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return (r.stdout or "").strip()


def main():
    sha = git("-c", "http.proxy=", "-c", "https.proxy=", "ls-remote",
              "git@github.com:Canshu-King/CityNexus.git", "refs/heads/" + LINE).split()[0]
    if os.path.isdir(EXPORT):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", EXPORT], timeout=600)
    os.makedirs(EXPORT, exist_ok=True)
    t = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, sha, EXPORT),
                       shell=True, capture_output=True, timeout=900, env=ENV)
    assert t.returncode == 0, t.stderr[:200]
    out = {"line_ref": LINE, "line_sha_readback": sha,
           "tsx_files": len(glob.glob(os.path.join(EXPORT, "frontend", "src", "**", "*.ts*"),
                                       recursive=True)),
           "rulers": {}}
    base = os.path.join(EXPORT, "frontend", "src")
    for tag, name in PAIRS:
        js = os.path.join(WORK, "line_%s.json" % tag)
        r = subprocess.run(["node", os.path.join(REF, name), "--tree", base, "--out", js],
                           capture_output=True, timeout=1800,
                           env=dict(ENV, PYTHONIOENCODING="utf-8"))
        assert os.path.isfile(js), "ruler %s failed rc=%s" % (tag, r.returncode)
        d = json.load(io.open(js, encoding="utf-8"))
        keys = sorted({"%s:%s|%s" % (str(h["file"]).replace("\\", "/").split("/")[-1], h["line"],
                                     h.get("rule")) for h in d.get("hits", [])})
        out["rulers"][tag] = {"file": name, "cells_total": d.get("cells_total"), "hits": len(keys),
                              "keys": keys,
                              "recovery_cells": [k for k in keys if k.startswith("RecoveryRequiredPanel")]}
    a = set(out["rulers"]["r7b"]["keys"])
    b = set(out["rulers"]["r7b4"]["keys"])
    out["lost_on_the_current_line"] = sorted(a - b)
    out["gained_on_the_current_line"] = sorted(b - a)
    io.open(os.path.join(WORK, "current_line_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "rulers"}, ensure_ascii=False, indent=1))
    for tag, _ in PAIRS:
        print(tag, "cells", out["rulers"][tag]["cells_total"], "recovery",
              out["rulers"][tag]["recovery_cells"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
