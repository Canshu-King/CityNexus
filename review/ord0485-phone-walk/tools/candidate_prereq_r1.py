"""ORD-0485: re-measure the dictionary gap on the candidate source, and typecheck the candidate.

FRONTSRC_BUILD_PREREQ shape: tsc --noEmit and vite build must both really run against the
candidate bytes.  The build ran in the lane runner (bundle index-CFK705TS.js); this writes the
typecheck receipt and the post-fix key gap in one place.
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
EXPORT = LANE + "/export"
FRONTEND = EXPORT + "/frontend"
NODE = os.environ.get("CNX_PHONE_NODE", r"C:/Program Files/nodejs/node.exe")
out = {"tool": "candidate_prereq_r1", "took_local": datetime.now().astimezone().isoformat()}

ts_src = os.path.join(LANE, "wt/frontend/src/i18n/LocaleContext.tsx")
ts_exp = os.path.join(FRONTEND, "src/i18n/LocaleContext.tsx")
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
out["dictionary_file"] = {"wt_sha256": h(ts_src), "export_sha256": h(ts_exp),
                          "identical": h(ts_src) == h(ts_exp),
                          "cr_bytes_in_file": open(ts_src, "rb").read().count(b"\r")}

env = dict(os.environ)
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    env.pop(k, None)

log = os.path.join(LANE, "run", "tsc_candidate_r1.txt")
p = subprocess.run([NODE, "node_modules/typescript/bin/tsc", "-p", "tsconfig.check.json",
                    "--noEmit"], cwd=FRONTEND, env=env,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
text = p.stdout.decode("utf-8", "replace")
open(log, "w", encoding="utf-8").write(text)
out["tsc"] = {"command": "node node_modules/typescript/bin/tsc -p tsconfig.check.json --noEmit",
              "cwd": "export/frontend", "exit": p.returncode,
              "diagnostics_bytes": len(text), "diagnostics_head": text[:800]}

p2 = subprocess.run([NODE, "node_modules/typescript/bin/tsc", "-p", "tsconfig.typecheck.json",
                     "--noEmit"], cwd=FRONTEND, env=env,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
text2 = p2.stdout.decode("utf-8", "replace")
open(os.path.join(LANE, "run", "tsc_all_candidate_r1.txt"), "w",
     encoding="utf-8").write(text2)
out["tsc_all"] = {"command": "node node_modules/typescript/bin/tsc -p tsconfig.typecheck.json --noEmit",
                  "exit": p2.returncode, "diagnostics_bytes": len(text2),
                  "diagnostics_head": text2[:1200]}

gap = subprocess.run([r"D:/moodle/CityNexus/.venv/Scripts/python.exe", "-X", "utf8",
                      os.path.join(LANE, "tools/i18n_key_gap_r1.py")],
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
try:
    parsed = json.loads(gap.stdout.decode("utf-8", "replace"))
except Exception:
    parsed = {"unparsed": gap.stdout.decode("utf-8", "replace")[:600]}
out["i18n_gap_after_fix"] = {k: parsed.get(k) for k in
                             ("keys_in_en", "keys_in_zhCN", "referenced_key_count",
                              "referenced_keys_missing_from_en",
                              "referenced_keys_missing_from_zhCN",
                              "referenced_keys_missing_from_both", "missing_from_both")}
out["i18n_gap_exit"] = gap.returncode

path = os.path.join(LANE, "evidence", "candidate_prereq_r1.json")
json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(json.dumps(out, indent=2, ensure_ascii=False)[:3000])
print("WROTE " + path)
