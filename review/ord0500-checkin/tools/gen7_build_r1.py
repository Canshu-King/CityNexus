"""Generation 4 (tip 1e95d106) -- typecheck and build every face this round serves, in one run.

FRONTSRC_BUILD_PREREQ shape: the candidate must really typecheck and really build from its own bytes
before a screen reading on its bundle counts.  Each face gets its own outDir under faces/, so no
face can read another's bundle, and the entry asset name is taken back out of the built index.html
rather than being asserted from the file name I hoped for.

CE-2's mutant face is a throwaway tree (wt18) whose stop mark comes from the plan's activity status
instead of the footprint read -- the second state machine the order forbids.  It is built and served
so the arm can fail on it for real; it is never committed.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
FACES = [
    ("TIP_7862c6de", "wt17", "faces/tip7"),
    ("O0500_R3", "wt16", "faces/o0500_r3"),
    ("O0500_CLIENTBOOL_MUTANT", "wt18", "faces/o0500_clientbool7"),
]


def env_clean():
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "DEEPSEEK_API_KEY"):
        e.pop(k, None)
    return e


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, env=env_clean(), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def sha(path):
    b = open(path, "rb").read()
    return {"bytes": len(b), "sha256": hashlib.sha256(b).hexdigest(),
            "local_sha1": hashlib.sha1(b).hexdigest()}


def main():
    out = {"tool": "gen7_build_r1", "took_local": datetime.now().astimezone().isoformat(),
           "faces": []}
    for label, tree, rel_out in FACES:
        frontend = os.path.join(LANE, tree, "frontend")
        outdir = os.path.join(LANE, rel_out)
        entry = {"label": label, "tree": tree, "out_dir": rel_out}
        if not os.path.isdir(outdir):
            os.makedirs(outdir)
        for cfg in ("tsconfig.check.json", "tsconfig.typecheck.json"):
            rc, text = run([NODE, "node_modules/typescript/bin/tsc", "-p", cfg, "--noEmit"],
                           frontend)
            logname = "run/gen7_tsc_%s_%s.txt" % (label, cfg.replace(".json", ""))
            open(os.path.join(LANE, logname), "w", encoding="utf-8").write(text)
            entry[cfg] = {"exit": rc, "diagnostics_bytes": len(text.encode("utf-8")),
                          "head": text[:400], "log": logname}
        rc, text = run([NODE, "node_modules/vite/bin/vite.js", "build", "--outDir", outdir,
                        "--emptyOutDir"], frontend)
        logname = "run/gen7_build_%s.txt" % label
        open(os.path.join(LANE, logname), "w", encoding="utf-8").write(text)
        entry["build"] = {"exit": rc, "log": logname,
                          "built_line": [l for l in text.splitlines() if "built in" in l][:1],
                          "module_lines": len(re.findall(r"assets/[\w.\-]+\.(?:js|css)", text))}
        html_path = os.path.join(outdir, "index.html")
        if os.path.exists(html_path):
            html = open(html_path, encoding="utf-8").read()
            m = re.search(r'src="/assets/(index-[\w\-]+\.js)', html)
            css = re.search(r'href="/assets/(index-[\w\-]+\.css)', html)
            js = os.path.join(outdir, "assets", m.group(1)) if m else None
            entry["entry"] = {"index_html": sha(html_path),
                              "entry_asset": m.group(1) if m else None,
                              "css_asset": css.group(1) if css else None,
                              "bundle": sha(js) if js and os.path.exists(js) else None,
                              "sw": os.path.exists(os.path.join(outdir, "v10-sw.js")),
                              "file_count": len([f for _, _, fs in os.walk(outdir) for f in fs])}
        out["faces"].append(entry)
        print("%s tsc_check=%s tsc_all=%s build=%s entry=%s" % (
            label, entry.get("tsconfig.check.json", {}).get("exit"),
            entry.get("tsconfig.typecheck.json", {}).get("exit"), entry["build"]["exit"],
            entry.get("entry", {}).get("entry_asset")), flush=True)
    path = os.path.join(LANE, "evidence", "gen7_builds_r1.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:4000])
    print("WROTE " + path)
    return 0 if all(f["build"]["exit"] == 0 for f in out["faces"]) else 1


if __name__ == "__main__":
    sys.exit(main())
