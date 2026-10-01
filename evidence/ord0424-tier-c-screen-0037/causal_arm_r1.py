# -*- coding: utf-8 -*-
"""ORD-0424 causal arm r2 - change the two source strings, rebuild, and watch the screen follow.

The control pass proved the checker can say "no" (a deliberately misspelt literal is absent, and a string
that only appears inside a longer composed sentence is not counted as an own-text node). What it cannot
do alone is show that the painted text comes from *those* lines. So: edit the two literals in this lane's
private work tree, build a second bundle into its own outDir, serve it on its own port, and re-run the
same exact-node check. The old strings must be gone and the markers present; then the file is restored and
verified byte-equal to the tip's blob, because a mutation left behind would be worse than no mutation.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0424"
SRC = os.path.join(WT, "frontend", "src", "main.tsx")
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
TIP = "0c061d9eb74b21f0b0b297a068778479b08658b4"
REPO = r"D:\moodle\CityNexus"
ENV = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)
ENV["NO_PROXY"] = "*"
ENV["CNX_PW"] = "D:/moodle/_cnx_buildcheck_20260920/frontend/node_modules/playwright"
ORIG = ["Journey connection unavailable", "Retry backend connection"]
MARK = ["MUTANT-A-LEGACY-HEADLINE-0424", "MUTANT-B-LEGACY-BUTTON-0424"]
NPM = shutil.which("npm.cmd") or shutil.which("npm")


def sh(args, cwd=None, timeout=900):
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=cwd, env=ENV, timeout=timeout)
    return p.returncode, (p.stdout or "")


def tip_blob():
    _, out = sh(["git", "-C", REPO, "ls-tree", TIP, "frontend/src/main.tsx"])
    return out.split()[2] if len(out.split()) >= 3 else None


def local_blob(path):
    _, out = sh(["git", "-C", REPO, "hash-object", path.replace(os.sep, "/")])
    return out.split()[0] if out.strip() else None


def wait_port(port, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/legacy" % port, timeout=3).read()
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            time.sleep(1)
    return False


def check(label, base, literals, shot=None):
    env = dict(ENV)
    env.update({"CNX_BASE": base, "CNX_LABEL": label, "CNX_LITERALS": json.dumps(literals)})
    if shot:
        env["CNX_SHOT"] = shot
    p = subprocess.run(["node", os.path.join(HERE, "node_exact_check_r1.cjs")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, cwd=HERE, timeout=600)
    doc = json.load(io.open(os.path.join(HERE, "exact_%s_r1.json" % label), encoding="utf-8"))
    return doc, (p.stdout or "") + (p.stderr or "")


def main():
    result = {"tip": TIP, "tip_blob_main_tsx": tip_blob()}
    text = io.open(SRC, encoding="utf-8").read()
    for o, m in zip(ORIG, MARK):
        if text.count(o) != 1:
            result["aborted"] = "the literal %r does not appear exactly once, so the mutation would not be " \
                                "a single-variable change" % o
            return json.dump(result, io.open(os.path.join(HERE, "causal_arm_r1.json"), "w", encoding="utf-8"))
    before = local_blob(SRC)

    # control on the untouched build
    NEG = ["Journey connection unavaliable", "CityNexus request refused"]
    ctl, _ = check("control_full", "http://localhost:4541", ORIG + MARK + NEG, "screen_legacy_control_r1.png")
    result["control"] = {r["literal"]: {"node_exact": r["node_exact"], "substring_in_body": r["substring_in_body"]}
                         for r in ctl["results"]}

    mutated = text
    for o, m in zip(ORIG, MARK):
        mutated = mutated.replace(o, m)
    io.open(SRC, "w", encoding="utf-8", newline="\n").write(mutated)
    try:
        rc, out = sh([NPM, "run", "build", "--", "--outDir", "dist_mutant", "--emptyOutDir"], cwd=os.path.join(WT, "frontend"),
                     timeout=1200)
        result["mutant_build_rc"] = rc
        result["mutant_build_tail"] = out.strip().split("\n")[-3:]
        srv = subprocess.Popen([sys.executable, os.path.join(HERE, "static_spa_r1.py"), "4542"],
                               env=dict(ENV, CNX_DIST_ROOT=os.path.join(WT, "frontend", "dist_mutant")),
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            ok = wait_port(4542)
            result["mutant_server_up"] = ok
            mut, _ = check("mutant", "http://localhost:4542", ORIG + MARK + NEG, "screen_legacy_mutant_r1.png")
            result["mutant"] = {r["literal"]: {"node_exact": r["node_exact"],
                                               "substring_in_body": r["substring_in_body"],
                                               "tags": r["node_tags"]}
                                for r in mut["results"]}
        finally:
            srv.terminate()
    finally:
        io.open(SRC, "w", encoding="utf-8", newline="\n").write(text)
    after = local_blob(SRC)
    result["restored"] = {"local_blob_before": before, "local_blob_after": after,
                          "equal_to_tip": after == tip_blob()}
    result["verdict"] = {
        "control_shows_the_two_originals": all(result["control"][o]["node_exact"] for o in ORIG)
        and not any(result["control"][m]["node_exact"] for m in MARK),
        "mutant_shows_the_two_markers_instead": all(result["mutant"][m]["node_exact"] for m in MARK)
        and not any(result["mutant"][o]["node_exact"] for o in ORIG),
        "so_the_painted_text_is_those_source_lines": None,
    }
    result["verdict"]["so_the_painted_text_is_those_source_lines"] = (
        result["verdict"]["control_shows_the_two_originals"]
        and result["verdict"]["mutant_shows_the_two_markers_instead"])
    io.open(os.path.join(HERE, "causal_arm_r1.json"), "w", encoding="utf-8").write(
        json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps({"control": result["control"], "mutant": {k: v["node_exact"] for k, v in result["mutant"].items()},
                      "restored_equal_to_tip": result["restored"]["equal_to_tip"],
                      "verdict": result["verdict"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
