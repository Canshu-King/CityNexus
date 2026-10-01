"""Give the r4 block its reachability sentence, and make the coordinate list cover it.

The census answers five of six stop controls reachable by centre hit at 390x844 on this tip -- on the
base bundle and on my candidate alike, and six of six at 1280x800.  A number like that invites the
reading "your change cost one", so the block has to say what was measured and what was tried: a
`scroll-margin-bottom` on the stop row was built into its own face and re-measured (still five of six),
then reverted rather than shipped.  The remedy sits with the scroll container and the mobile nav.
"""
import ast
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COORD = os.path.join(LANE, "tools", "gen8_coordinates_r1.py")
BLOCKS = os.path.join(LANE, "tools", "gen8_blocks_r1.py")

text = open(COORD, encoding="utf-8").read()
old = '          (cand, "review/ord0500-checkin/receipts/checkin_PRE_SLICE2_dcb90ccc_phone_390x844_r2.json"),'
new = ('          (cand, "review/ord0500-checkin/receipts/'
       'checkin_PRE_SLICE2_dcb90ccc_phone_390x844_r2.json"),\n'
       '          (cand, "review/ord0500-checkin/receipts/'
       'checkin_SCROLLTEST_phone_390x844_r2.json"),')
assert text.count(old) == 1, "coord anchor"
open(COORD, "w", encoding="utf-8", newline="\n").write(text.replace(old, new))

b = open(BLOCKS, encoding="utf-8").read()
slot_old = '        "b_walk6": blobs["review/ord0485-phone-walk/receipts/gen6_walk_r1.json"],'
slot_new = (slot_old + '\n        "b_scroll": blobs["review/ord0500-checkin/receipts/'
            'checkin_SCROLLTEST_phone_390x844_r2.json"],')
assert b.count(slot_old) == 1, "slot anchor"
b = b.replace(slot_old, slot_new)

prose_old = "（件 `{b_sweep}`）。"
prose_new = ("（件 `{b_sweep}`）。④ 里那句「可按 {press_tip} 枚」不是我这笔造成的：同一普查在基座面上也是 "
             "{press_tip} 枚、桌面 1280x800 两代都 6 枚——不可按的是第 1 站 Riverside Museum，它的元素中心落在固定"
             "底栏「地图」那枚按钮上（`overlaps_nav=true`）。我按上代的教训先量再改：给站行加 "
             "`scroll-margin-bottom: 92px` 单独造了一面重跑，仍是 {press_tip} 枚，于是把这条规则撤了不留装饰"
             "（重跑件 `{b_scroll}`）；真正要动的是滚动容器与手机底栏那两家，不在本单写集里，具名报出。")
assert b.count(prose_old) == 1, "prose anchor count %d" % b.count(prose_old)
b = b.replace(prose_old, prose_new, 1)
open(BLOCKS, "w", encoding="utf-8", newline="\n").write(b)
ast.parse(b)
print("block carries the reachability finding")
