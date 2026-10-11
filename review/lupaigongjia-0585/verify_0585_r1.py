# -*- coding: utf-8 -*-
"""ORD-0585 verify: the arm now in the dictionary must equal, byte for byte, the literal deleted from
the pristine tip's component.  Read back through the product's own dictionaryCopy, bundled + run."""
from __future__ import print_function

import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lupaigongjia_0576"
FRONT = os.path.join(WT, "frontend")
REPO = "D:/moodle/CityNexus"
TIP = "a368e12313b505d444c871cb79375339f72a6c5c"
REL = "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx"
OUT = os.path.join(WT, "verify_0585_r1.txt")
KEY = u"recovery.acceptanceUnanswered"
ZH = u"这步接受没有得到可确认的答复，结果未知。"
EN = u"This acceptance got no confirmable answer; the result is unknown."

p = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (TIP, REL)], capture_output=True)
if p.returncode:
    sys.exit("ABORT git show rc=%d" % p.returncode)
tip = p.stdout.decode("utf-8")
for arm, label in ((ZH, "zh"), (EN, "en")):
    n = tip.count(u'"%s"' % arm)
    if n != 1:
        sys.exit("ABORT tip %s literal hits %d, expected 1" % (label, n))

probe_dir = os.path.join(FRONT, "src", "__verify0585")
if not os.path.isdir(probe_dir):
    os.makedirs(probe_dir)
entry = os.path.join(probe_dir, "probe.ts")
io.open(entry, "w", encoding="utf-8").write(
    u'import { dictionaryCopy } from "../i18n/LocaleContext";\n'
    u'export function read(key: string) {\n'
    u'  return { en: dictionaryCopy("en", key), zh: dictionaryCopy("zh-CN", key) };\n}\n')


def js(x):
    return json.dumps(x.replace("\\", "/"))


runner = os.path.join(WT, "verify_0585_runner.cjs")
io.open(runner, "w", encoding="utf-8").write(
    u'const path=require("path");\n'
    u'const esbuild=require(path.join(%s,"node_modules","esbuild"));\n'
    u'(async()=>{\n'
    u'  await esbuild.build({entryPoints:[%s],bundle:true,format:"cjs",platform:"node",\n'
    u'    jsx:"automatic",external:["react","react/jsx-runtime"],outfile:%s,logLevel:"silent"});\n'
    u'  const v=require(%s).read(%s);\n'
    u'  process.stdout.write(JSON.stringify(v));\n'
    u'})().catch(e=>{console.error(String(e.message||e).slice(0,400));process.exit(1)});\n'
    % (js(FRONT), js(entry), js(os.path.join(probe_dir, "bundle.cjs")),
       js(os.path.join(probe_dir, "bundle.cjs")), js(KEY)))

run = subprocess.run(["node", runner], capture_output=True)
if run.returncode:
    sys.exit("ABORT node rc=%d %s" % (run.returncode, run.stderr.decode("utf-8", "replace")[:400]))
got = json.loads(run.stdout.decode("utf-8"))

lines = [u"ORD-0585 单键两臂对拍：现尖 %s 原字面 vs 本树字典（dictionaryCopy 真跑）" % TIP[:10], u"",
         u"zh %s  bytes_orig=%d bytes_dict=%d" % (u"IDENTICAL" if got["zh"] == ZH else u"DIFFERS",
                                                  len(ZH.encode("utf-8")), len(got["zh"].encode("utf-8"))),
         u"en %s  bytes_orig=%d bytes_dict=%d" % (u"IDENTICAL" if got["en"] == EN else u"DIFFERS",
                                                  len(EN.encode("utf-8")), len(got["en"].encode("utf-8"))),
         u"",
         u"字典取回值逐字：",
         u"  zh=%s" % got["zh"],
         u"  en=%s" % got["en"],
         u""]
lines.append(u"合计：两臂比对，不同 %d 臂" % ((got["zh"] != ZH) + (got["en"] != EN)))
io.open(OUT, "w", encoding="utf-8", newline="\n").write(u"\n".join(lines) + u"\n")
print("WROTE %s differing=%d" % (OUT, (got["zh"] != ZH) + (got["en"] != EN)))
