"""The generation-7 sheet covers ORD-0500 only; ORD-0485's readings live on its own page.

Section seven is replaced by a pointer, because the dictionary order was measured on the generation
its ref was cut on (`0989713a...`) and that sheet is committed in
`review/newlane-ord0485-phone-walkthrough-r5`.  Claiming its numbers under this order's generation
header would be exactly the cross-generation reading the standing rule forbids.
"""
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "tools", "gen7_sheets_r1.py")
NL = chr(10)
text = open(PATH, encoding="utf-8").read()

start = text.index('    a("## 七、词汇闸')
end = text.index('    a("## 八、打卡真理载体')
replacement = (
    '    a("## 七、词汇闸（ORD-0485）不在这一页上。" )' + NL +
    '    a("")' + NL +
    '    a("那一单量在它自己那一代（基座 0989713aa687b97f4cd40bae009a6ce493425a4b），读数单是'
  '`review/ord0485-phone-walk/GEN6_READINGS.md`，随枝 `review/newlane-ord0485-phone-walkthrough-r5` '
  '交付；把它的数写在本单页眉下就是跨代折算，Q24 不许。")' + NL +
    '    a("")' + NL
)
text = text[:start] + replacement + text[end:]
text = text.replace('for dest in (os.path.join(LANE, "wt11/review/ord0485-phone-walk/GEN5_READINGS.md"),\n'
                    '                 os.path.join(LANE, "wt16/review/ord0500-checkin/GEN5_READINGS.md")):',
                    'for dest in (os.path.join(LANE, "wt16/review/ord0500-checkin/GEN7_READINGS.md"),):')
open(PATH, "w", encoding="utf-8", newline=NL).write(text)
import ast
ast.parse(text)
print("gen7 sheet trimmed; destinations:", [l.strip()[:80] for l in text.split(NL) if "READINGS" in l])
