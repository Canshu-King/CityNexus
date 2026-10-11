# -*- coding: utf-8 -*-
"""Compare the two generations' own readings of the stage-busy failure line.

Reads only what the probes printed (the product's own describeFailure / dictionaryCopy / dictionaryText
output), never a hand-written expectation.  Every count below is computed from those two JSON files.
"""
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CJK = re.compile(u"[㐀-鿿]")
base = json.loads(io.open("D:/moodle/_jz_0585/probe_base_out.json", encoding="utf-8").read())
cand = json.loads(io.open("D:/moodle/_jz_0585/probe_wt_out.json", encoding="utf-8").read())

bc, cc = base["cases"], cand["cases"]
print("CASES base=%d cand=%d same_keys=%s" % (len(bc), len(cc), sorted(bc) == sorted(cc)))

zh_same = [k for k in bc if bc[k]["zh"] == cc[k]["zh"]]
zh_diff = [k for k in bc if bc[k]["zh"] != cc[k]["zh"]]
en_same = [k for k in bc if bc[k]["en"] == cc[k]["en"]]
en_diff = [k for k in bc if bc[k]["en"] != cc[k]["en"]]
print("ZH arm: identical %d / different %d" % (len(zh_same), len(zh_diff)))
print("EN arm: identical %d / different %d" % (len(en_same), len(en_diff)))
for k in zh_diff:
    print("  ZH_DIFF %s" % k)

base_en_with_cjk = [k for k in bc if CJK.search(bc[k]["en"])]
cand_en_with_cjk = [k for k in cc if CJK.search(cc[k]["en"])]
print("EN arm carrying Chinese before the move: %d of %d cases" % (len(base_en_with_cjk), len(bc)))
print("EN arm carrying Chinese after  the move: %d of %d cases" % (len(cand_en_with_cjk), len(cc)))
print("ZH arm carrying no Chinese after the move: %d" % len([k for k in cc if not CJK.search(cc[k]["zh"])]))

print("\n-- one line per case, both arms, both generations --")
for k in sorted(bc):
    print("CASE %s" % k)
    print("   zh base %s" % bc[k]["zh"])
    print("   zh cand %s" % cc[k]["zh"])
    print("   en base %s" % bc[k]["en"])
    print("   en cand %s" % cc[k]["en"])

print("\n-- the three keys read straight off the candidate dictionary --")
for k in sorted(cand["keys"]):
    v = cand["keys"][k]
    print("KEY %s | en %r | zh %r | en_filled %r | zh_filled %r | missing_en=%s missing_zh=%s"
          % (k, v["en"], v["zh"], v["enFilled"], v["zhFilled"], v["missingOnEn"], v["missingOnZh"]))

print("\n-- control: a key neither side carries --")
print("CONTROL %r" % cand["control"]["absentKeyReadsBackAsName"])

print("\n-- base generation had no such keys, so it must read them back as their own name --")
for k in sorted(base["keys"]):
    v = base["keys"][k]
    print("BASE_KEY %s | missing_en=%s missing_zh=%s | reads %r" % (k, v["missingOnEn"], v["missingOnZh"], v["zh"]))
