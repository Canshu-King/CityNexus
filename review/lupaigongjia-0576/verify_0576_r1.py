# -*- coding: utf-8 -*-
"""ORD-0576 verify: the four arms now in the dictionary must equal, byte for byte, the literals that
were deleted from the pristine tip's components.  The dictionary side is read back through the
product's own non-hook accessor (dictionaryCopy) bundled and run in node -- not by re-reading my edit."""
from __future__ import print_function

import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lupaigongjia_0576"
FRONT = os.path.join(WT, "frontend")
REPO = "D:/moodle/CityNexus"
TIP = "8a44ea61aeb81d999a17913a18828b725ea463f2"
PANEL = "frontend/src/features/discovery/DestinationPreparationPanel.tsx"
CHECK = "frontend/src/features/checklist/PretripChecklistPanel.tsx"
OUT = os.path.join(WT, "verify_0576_r1.txt")
NODE = "node"

ZH_LONG = (u'这里只列契约写明依据的两类检查：这一代方案的可行性失败、以及等待你决定的恢复方案。'
           u'完成状态由服务端事实自己消失，不需要你打勾；没跑过的检查不会被打勾，也不会出现在这里。')
EN_LONG = (u"Only the two checks whose fields the contract declares live here: feasibility failures on "
           u"this plan generation, and a recovery awaiting your decision. Items disappear when the "
           u"server's fact changes -- nothing is ticked by hand, and a check that was not run is never "
           u"shown as passed and never shown at all.")

PAIRS = [
    ("discovery.checkThisDestination", PANEL, u"看看能不能规划", u"Check this destination"),
    ("discovery.retryLater", PANEL, u"稍后重试", u"Try again later"),
    ("discovery.prepareThisDestination", PANEL, u"开始准备", u"Prepare this destination"),
    ("detail.pretripScopeNote", CHECK, ZH_LONG, EN_LONG),
]


def tip_text(rel):
    p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, rel)], capture_output=True)
    if p.returncode:
        sys.exit("ABORT git show %s rc=%d" % (rel, p.returncode))
    return p.stdout.decode("utf-8")


orig = {}
cache = {}
for key, rel, zh, en in PAIRS:
    text = cache.setdefault(rel, tip_text(rel))
    for arm, label in ((zh, "zh"), (en, "en")):
        quoted = u'"%s"' % arm
        n = text.count(quoted)
        if n != 1:
            sys.exit("ABORT tip %s %s quoted literal appears %d times in %s" % (key, label, n, rel))
    orig[key] = (zh, en)

probe_dir = os.path.join(FRONT, "src", "__verify0576")
if not os.path.isdir(probe_dir):
    os.makedirs(probe_dir)
entry = os.path.join(probe_dir, "probe.ts")
io.open(entry, "w", encoding="utf-8").write(
    u'import { dictionaryCopy } from "../i18n/LocaleContext";\n'
    u'export function read(key: string) {\n'
    u'  return { en: dictionaryCopy("en", key), zh: dictionaryCopy("zh-CN", key) };\n}\n')

runner = os.path.join(WT, "verify_0576_runner.cjs")
keys = json.dumps([k for k, _r, _z, _e in PAIRS])


def js(p):
    return json.dumps(p.replace("\\", "/"))


io.open(runner, "w", encoding="utf-8").write(
    u'const path=require("path");\n'
    u'const esbuild=require(path.join(%s,"node_modules","esbuild"));\n'
    u'(async()=>{\n'
    u'  await esbuild.build({entryPoints:[%s],bundle:true,format:"cjs",platform:"node",\n'
    u'    jsx:"automatic",external:["react","react/jsx-runtime"],\n'
    u'    outfile:%s,logLevel:"silent"});\n'
    u'  const m=require(%s);\n'
    u'  for(const k of %s){const v=m.read(k);process.stdout.write(JSON.stringify([k,v.zh,v.en])+String.fromCharCode(10));}\n'
    u'})().catch(e=>{console.error(String(e.message||e).slice(0,400));process.exit(1)});\n'
    % (js(FRONT), js(entry), js(os.path.join(probe_dir, "bundle.cjs")),
       js(os.path.join(probe_dir, "bundle.cjs")), keys))

run = subprocess.run([NODE, runner], capture_output=True)
if run.returncode:
    sys.exit("ABORT node runner rc=%d %s" % (run.returncode,
                                             run.stderr.decode("utf-8", "replace")[:400]))
got = {}
for line in run.stdout.decode("utf-8").split("\n"):
    if line.strip():
        k, zh, en = json.loads(line)
        got[k] = (zh, en)

lines = [u"ORD-0576 四臂对拍：现尖 %s 的原字面 vs 本树字典（走 dictionaryCopy 真跑）" % TIP[:10], u""]
bad = 0
for key, rel, _z, _e in PAIRS:
    oz, oe = orig[key]
    if key not in got:
        sys.exit("ABORT no reading for " + key)
    gz, ge = got[key]
    bad += (oz != gz) + (oe != ge)
    lines.append(u"%s (%s)" % (key, os.path.basename(rel)))
    lines.append(u"  zh %s  bytes_orig=%d bytes_dict=%d"
                 % (u"IDENTICAL" if oz == gz else u"DIFFERS",
                    len(oz.encode("utf-8")), len(gz.encode("utf-8"))))
    lines.append(u"  en %s  bytes_orig=%d bytes_dict=%d"
                 % (u"IDENTICAL" if oe == ge else u"DIFFERS",
                    len(oe.encode("utf-8")), len(ge.encode("utf-8"))))
lines.append(u"")
lines.append(u"合计：八臂比对，不同 %d 臂" % bad)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(u"\n".join(lines) + u"\n")
print("WROTE %s differing_arms=%d" % (OUT, bad))
