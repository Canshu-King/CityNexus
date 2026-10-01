"""Turn the derived r3 block tool into the r4 one (text the shell cannot mangle).

Two changes: a title plus an opening section for the real conflict with ORD-0530 in the same file
family, and one emitted page this round -- ORD-0485 r5 is already in the ledger, so its landing status
travels inside this block's landing-check receipt rather than in a second block.
"""
import ast
import os

LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(LANE, "tools", "gen8_blocks_r1.py")
NL = chr(10)
TIP = "514b397f96f3b5165b24865f4a544ab6f8020084"
text = open(PATH, encoding="utf-8").read()

OLD_TITLE = "### ORD-0500 · 手机打卡门 r3：那处调用点是我开的，按 Q64 的裁语改掉，读数在 ORD-0532 之后的尖上重量（车道 phone，{t_cand}）"
NEW_TITLE = "### ORD-0500 · 手机打卡门 r4：与 ORD-0530 同族的 CSS 手工并块，曝光格两侧对照随件（车道 phone，{t_cand}）"

OLD_HEAD = "**零、这一轮改的是我自己那一格，不是尺**。"
NEW_HEAD = (
    "**〇、这次是真冲突，两族都活着**。落地序列器报的冲突在 checkin 那一族：ORD-0530（按天足迹）在现尖 "
    + TIP + " 上往 footprint.css 追加了 40 行，我那 31 行的站行可达性块也在同一枚文件尾部——两枚都是加法，"
    "合并不肯替谁排顺序，所以手工并块：它那 40 行在前（它先落在这条线上），我这 31 行在后，两枚都保留。"
    "现读计数：`cn-footprints__day` 3 处、`/* ORD-0500` 1 处（并块由 `review/ord0500-checkin/tools/land_o0500_r4.py` 做，"
    "断言是任何一枚缺席、重复或倒序就中止）。`backend/app/main.py` 与 `contracts/openapi.yaml` 在这一批里也被别人加过行，"
    "我的落点仍是 14 增 2 删那一小块——LF 之后不再整文件对撞。"
    "**调用点按 0530 的新形状重核过**：它那一族自己也是屏内格式化（`footprintCopy.ts` 里的 `zoned()`，"
    "注释明写中文 Intl 输出读作 10月1日 周四），`FootprintPanel.tsx` 里 `formatV8Date` 命中 0 枚，"
    "所以这一族没有第二条「正文→共用 helper」的路；我那枚 `formatStampedMoment` 管的是行程屏重复打卡那一刻，"
    "它那枚 `zoned()` 管的是足迹面板的日头，两家各留各的，我不擅自合并成第三家。" + NL + NL + OLD_HEAD)

OLD_PATHS = '''    paths = {
        "cand": r"D:\\moodle\\_qoder_ledger_inbox\\0afdb49b_%s.md" % now.strftime("%H%M"),
        "dic": r"D:\\moodle\\_qoder_ledger_inbox\\0afdb49b_%s.md" % later.strftime("%H%M"),
    }
    for key, text in (("cand", block_cand), ("dic", block_dict)):'''
NEW_PATHS = '''    paths = {
        "cand": r"D:\\moodle\\_qoder_ledger_inbox\\0afdb49b_%s.md" % now.strftime("%H%M"),
    }
    for key, text in (("cand", block_cand),):'''

for old, new, name in ((OLD_TITLE, NEW_TITLE, "title"), (OLD_HEAD, NEW_HEAD, "head"),
                       (OLD_PATHS, NEW_PATHS, "paths")):
    if text.count(old) != 1:
        raise SystemExit("ABORT_ANCHOR %s -> %d" % (name, text.count(old)))
    text = text.replace(old, new)

open(PATH, "w", encoding="utf-8", newline="\n").write(text)
ast.parse(text)
print("gen8 block tool is now the r4 page")
