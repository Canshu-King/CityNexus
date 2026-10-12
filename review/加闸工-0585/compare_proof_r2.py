# -*- coding: utf-8 -*-
"""Compare two generations' own readings of the stage-busy failure line (ORD-0585 r2).

Usage: python compare_proof_r2.py <base.json> <cand.json> <out.txt>
Reads only what the probe printed -- the product's own describeFailure / dictionaryCopy / dictionaryText
output.  Every count is computed from those two files; nothing below is a hand-written expectation.
"""
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CJK = re.compile(u"[㐀-鿿]")
base = json.loads(io.open(sys.argv[1], encoding="utf-8").read())
cand = json.loads(io.open(sys.argv[2], encoding="utf-8").read())
bc, cc = base["cases"], cand["cases"]

o = []
o.append("加闸工 ORD-0585 r2 两代逐字节对拍 —— tag=%s 对 tag=%s，两边都是真产品码打包真跑出来的读数"
         % (base["tag"], cand["tag"]))
o.append("用例数 base=%d cand=%d 同一批用例名=%s" % (len(bc), len(cc), sorted(bc) == sorted(cc)))
o.append("中文臂：同文 %d 条 / 异文 %d 条"
         % (len([k for k in bc if bc[k]["zh"] == cc[k]["zh"]]),
            len([k for k in bc if bc[k]["zh"] != cc[k]["zh"]]))
         )
o.append("英文臂：同文 %d 条 / 异文 %d 条"
         % (len([k for k in bc if bc[k]["en"] == cc[k]["en"]]),
            len([k for k in bc if bc[k]["en"] != cc[k]["en"]]))
         )
o.append("改前英文臂含汉字 %d 条 / 共 %d 条；改后含汉字 %d 条"
         % (len([k for k in bc if CJK.search(bc[k]["en"])]), len(bc),
            len([k for k in cc if CJK.search(cc[k]["en"])])))
o.append("改后中文臂不含汉字 %d 条（若为正数就是搬丢了）"
         % len([k for k in cc if not CJK.search(cc[k]["zh"])]))
o.append("")
o.append("-- 逐枚用例，两臂两代 --")
for k in sorted(bc):
    o.append("CASE %s" % k)
    o.append("   zh 改前 %s" % bc[k]["zh"])
    o.append("   zh 改后 %s" % cc[k]["zh"])
    o.append("   en 改前 %s" % bc[k]["en"])
    o.append("   en 改后 %s" % cc[k]["en"])
o.append("")
o.append("-- 三枚键在两代的读法（改前那代应读不回，改后那代应两侧都读得回）--")
for k in sorted(cand["keys"]):
    v, w = cand["keys"][k], base["keys"][k]
    o.append("KEY %s | 改后 en=%r zh=%r 填洞后 en=%r zh=%r | 改前 missing_en=%s missing_zh=%s 读回=%r"
             % (k, v["en"], v["zh"], v["enFilled"], v["zhFilled"], w["missingOnEn"], w["missingOnZh"], w["zh"]))
o.append("对照：dictionaryCopy 对字典没有的键返回键名本身，所以 missing_* 那两枚布尔是真测的（本例 control=%r）"
         % cand["control"]["absentKeyReadsBackAsName"])

io.open(sys.argv[3], "w", encoding="utf-8", newline="\n").write("\n".join(o) + "\n")
print("WROTE %s  行数=%d" % (sys.argv[3], len(o)))
print(o[2]); print(o[4]); print(o[5])
