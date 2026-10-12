# -*- coding: utf-8 -*-
"""真取词探针驱动：两侧语言各渲染一次，读的是货架上那枚 useT()，不是我把字典抄一遍。
  甲臂 = 本车道树上的字典（应念出搬前的两串原文）
  乙臂 = 钉在现尖那一代字典上的反控（键还没上尖，应逐枚念出键名本身）
每一臂重新打包一次。任一臂断言不过就非零退出。"""
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = json.load(open(sys.argv[1], encoding="utf-8"))
TREE = "D:/moodle/_qoder_pinggong_0576"
SCRATCH = "D:/moodle/_pinggong_scratch"
REPO = "D:/moodle/_qoder_integration_20260919"
TIP = SPEC["tip"]
NEG = SCRATCH + "/negctl_r1"
OUT = SCRATCH + "/probe_out_r1"
KEYS = []
for row in SPEC["rows"]:
    if row["key"] not in KEYS:
        KEYS.append(row["key"])


def sh(args, cwd, use_env=None):
    proc = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=use_env)
    if proc.returncode != 0:
        raise SystemExit("ABORT %s :: %s" % (" ".join(args)[:120],
                                             (proc.stdout + proc.stderr)[-500:]))
    return proc.stdout


os.makedirs(NEG + "/src/i18n", exist_ok=True)
os.makedirs(NEG + "/src/lib", exist_ok=True)
with open(NEG + "/src/i18n/LocaleContext.tsx", "w", encoding="utf-8", newline="") as h:
    h.write(sh(["git", "show", "%s:frontend/src/i18n/LocaleContext.tsx" % TIP], REPO))
with open(NEG + "/src/lib/plural.ts", "w", encoding="utf-8", newline="") as h:
    h.write(sh(["git", "show", "%s:frontend/src/lib/plural.ts" % TIP], REPO))

os.makedirs(OUT, exist_ok=True)
with open(OUT + "/package.json", "w", encoding="utf-8") as h:
    h.write('{"type":"commonjs"}\n')

runner = r"""
const esbuild = require(require.resolve("esbuild", { paths: [process.cwd()] }));
const [entry, outfile] = process.argv.slice(2);
esbuild.build({
  entryPoints: [entry],
  outfile: outfile,
  bundle: true,
  platform: "node",
  format: "cjs",
  jsx: "automatic",
  absWorkingDir: process.cwd(),
  nodePaths: [process.cwd() + "/node_modules"],
  logLevel: "error",
}).then(() => console.log("BUNDLED " + outfile)).catch(() => process.exit(1));
"""
with open(SCRATCH + "/esbuild_probe_r1.cjs", "w", encoding="utf-8") as h:
    h.write(runner)

env = dict(os.environ)
env["PROBE_KEYS"] = json.dumps(KEYS)
arms = [("candidate", TREE + "/review/pinggong-0576/probe_candidate_r1.ts", OUT + "/cand.cjs"),
        ("negtip", TREE + "/review/pinggong-0576/probe_neg_r1.ts", OUT + "/neg.cjs")]
readings = {}
for tag, entry, outfile in arms:
    sh(["node", SCRATCH + "/esbuild_probe_r1.cjs", entry, outfile], cwd=TREE + "/frontend", use_env=env)
    env["PROBE_ARM"] = tag
    readings[tag] = [l for l in sh(["node", outfile], cwd=TREE, use_env=env).splitlines() if l.strip()]
    want_cells = 2 * len(KEYS)
    if len(readings[tag]) != want_cells:
        raise SystemExit("ABORT arm %s printed %d cells, expected %d —— 空读数不算绿"
                         % (tag, len(readings[tag]), want_cells))

expected = {row["key"]: (row["zh"], row["en"]) for row in SPEC["rows"]}
fails = []
for line in readings["candidate"]:
    arm, locale, key, value = [p.strip() for p in line.split("|", 3)]
    want = expected[key][0] if locale == "zh-CN" else expected[key][1]
    if value != want:
        fails.append("candidate %s %s got %r want %r" % (locale, key, value, want))
neg_missing = 0
for line in readings["negtip"]:
    arm, locale, key, value = [p.strip() for p in line.split("|", 3)]
    if value != key:
        fails.append("negtip %s %s resolved to %r (expected the bare key)" % (locale, key, value))
    else:
        neg_missing += 1

for line in readings["candidate"] + readings["negtip"]:
    print(line)
print("CANDIDATE_CELLS %d NEG_CELLS %d NEG_BARE_KEY %d FAILS %d"
      % (len(readings["candidate"]), len(readings["negtip"]), neg_missing, len(fails)))
for failure in fails:
    print("FAIL " + failure)
if fails or not readings["candidate"] or not readings["negtip"]:
    raise SystemExit(1)
print("VERDICT probe_green keys=%d cells=%d" % (len(KEYS), len(readings["candidate"])))
