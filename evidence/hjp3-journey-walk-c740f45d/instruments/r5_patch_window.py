"""Put every claimed number inside the gate's coordinate window, and move the headline counts where they can pay.

r4d still counts a non-zero quantity, and a `0` in front of a product noun, unless a strong receipt (a full
40-hex, an issuecomment id, a refs/heads name or a run id) sits within 200 characters. So: each fate line carries
its own screenshot blob, the signature line carries the probe file's blob, the self-test lines carry the fixture
and raw-file blobs, and the headline stops asserting two counts it cannot anchor - they move into the body beside
the reading file's blob. No figure is deleted and no claim is softened.

Every replacement asserts it matched exactly once, so a silent no-op cannot pass as a fix.
"""
import ast
import pathlib

p = pathlib.Path('D:/moodle/HJ-P3_evidence/r5_block.py')
s = p.read_text(encoding='utf-8')


def sub(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:80])
    s = s.replace(old, new)


sub("INSTR_BLOB = BLK(WALK + '/instruments/r5_walk3.cjs')",
    "INSTR_BLOB = BLK(WALK + '/instruments/r5_walk3.cjs')\n"
    "SHOT_CANARY = BLK(WALK + '/shots/W3_6_fate_canary200.png')\n"
    "SHOT_SHOT7 = BLK(WALK + '/shots/W3_7_natural.png')\n"
    "SHOT_FIXTURE = BLK(WALK + '/shots/W3_8_collapse_fixture.png')\n"
    "SHOT_STEP2 = BLK(WALK + '/shots/W3_3_next2.png')\n"
    "WHO_BLOB = BLK(WALK + '/who_answered_the_500s.json')\n"
    "RAW3 = BLK(WALK + '/raw_walk3_findings.json')\n"
    "RAWFIN = BLK(WALK + '/raw_finish_findings.json')")

sub("""L.append(f'### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **真人行程复验已在手机新代次上走完：{len(RS["cells"])} 格读数 + '
         f'{len(EXC)} 次我自己的仪器错都记账；结论只到读数，不写 PASS；用户现在做不到的事按步骤具名** '
         f'@{time.strftime("%H:%M")}+08')""",
    """L.append('### 📱 aad2d1f2 (SESSION=aad2d1f2) P3 · **真人行程复验已在手机新代次上走完：读数、我自己的仪器错、'
         '用户做不到的事都按步骤具名；只交读数，不写 PASS** @' + time.strftime('%H:%M') + '+08')""")

sub("""L.append(f'**读数总账（件 blob {Q}{READING_BLOB}{Q}；判据逐条 = '
         f'{sum(1 for v in J.values() if v is True)} / {len(J)} 条由件内字段算出，不是我打的勾）**')""",
    """L.append(f'**读数总账（件 blob {Q}{READING_BLOB}{Q}）：走到的格 {len(RS["cells"])} 格、被我排除的仪器跑 '
         f'{len(EXC)} 次、由件内字段算出的判据 {sum(1 for v in J.values() if v is True)} 条为真 / 共 {len(J)} 条；'
         f'逐条都不是我打的勾**')""")

sub("""    L.append(f'    {Q}{k}{Q} 屏上尾部三行 {Q}{" ▏ ".join(v["the_lines_it_shows"])}{Q}；开块后异常字面 文本 '
             f'{v["exception_in_text_after_opening_details"]} 处、属性 {v["exception_in_attributes_after_opening_details"]} 处、'
             f'堆栈 {v["stack_frame"]}、长机器串 {v["long_machine_text"]}、canary 是否到了 DOM = '
             f'{v["canary_reached_the_dom"]}')""",
    """    _sb = {'refused': SHOT_REFUSED, 'empty500': SHOT_EMPTY500, 'canary200': SHOT_CANARY}[k]
    L.append(f'    {Q}{k}{Q} 开块后：异常字面 文本 {v["exception_in_text_after_opening_details"]} 处、属性 '
             f'{v["exception_in_attributes_after_opening_details"]} 处、堆栈 {v["stack_frame"]}、长机器串 '
             f'{v["long_machine_text"]}、canary 到 DOM = {v["canary_reached_the_dom"]}'
             f'（截图 blob {Q}{_sb}{Q}；尾部三行 {Q}{" ▏ ".join(v["the_lines_it_shows"])}{Q}）')""")

sub("""L.append(f'· 而「谁答的」是量出来的：{WA["verdict"]["the_made_up_path_answers_identically_to_the_real_api_paths"]} —— '""",
    """L.append(f'· 而「谁答的」是量出来的（件 blob {Q}{WHO_BLOB}{Q}）：'
         f'{WA["verdict"]["the_made_up_path_answers_identically_to_the_real_api_paths"]} —— '""")

sub("""L.append(f'· 还有两件小的：链上不当我动手时也是这个态（自然态屏上尾部三行 {Q}{" ▏ ".join(NAT["what_the_shell_says_without_me_breaking_anything"])}{Q}，'""",
    """L.append(f'· 还有两件小的（截图 blob {Q}{SHOT_SHOT7}{Q}）：链上不当我动手时也是这个态（自然态屏上尾部三行 '
         f'{Q}{" ▏ ".join(NAT["what_the_shell_says_without_me_breaking_anything"])}{Q}，'""")

sub("""L.append(f'· 暴露判据：我自建一张真会漏的页（异常字面进文本 + 进 data-* 属性）跑同一条判据 = 文本 '""",
    """L.append(f'· 暴露判据：我自建一张真会漏的页（异常字面进文本 + 进 data-* 属性；夹具截图 blob '
         f'{Q}{SHOT_FIXTURE}{Q}，原始读数 blob {Q}{RAW3}{Q}）跑同一条判据 = 文本 '""")

sub("""L.append(f'· 折叠敏感度我改了测法：元素级 innerText 在折叠时确实读不到（'""",
    """L.append(f'· 折叠敏感度我改了测法（原始读数 blob {Q}{RAWFIN}{Q}）：元素级 innerText 在折叠时确实读不到（'""")

sub("""L.append(f'· 记账的仪器错 {len(EXC)} 次，每次都有机械信号（不是我事后认）：')""",
    """L.append(f'· 记账的仪器错 {len(EXC)} 次，每次都有机械信号（不是我事后认；三次的原始读数在 blob '
         f'{Q}{RAW3}{Q} 与 {Q}{RAWFIN}{Q}）：')""")

sub("""L.append(f'· 第三步复核页上写着「{C1["values_the_product_filled_for_me"][0]}」这类话（{len(C1["values_the_product_filled_for_me"])} 处）：'""",
    """L.append(f'· 第三步复核页（截图 blob {Q}{SHOT_STEP2}{Q}）上写着「{C1["values_the_product_filled_for_me"][0]}」'
         f'这类话（{len(C1["values_the_product_filled_for_me"])} 处）：'""")

p.write_text(s, encoding='utf-8')
ast.parse(s)
print('PATCHED + PARSES')
