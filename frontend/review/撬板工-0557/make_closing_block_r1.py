# -*- coding: utf-8 -*-
u"""撬板工：给已入账那两条块补一条带逐字尾行的收口块。

尾行必须逐字取自 CLOSING_LINE.txt，不许手打，也不许在 shell 管道里过中文
（本轮就是这条腿被控制台编码吃掉，块先被代插腿取走，尾行没跟上）。
"""
from __future__ import annotations

import datetime
import io
import os

CLOSING = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
INBOX = r"D:\moodle\_qoder_ledger_inbox"

BODY = u"""### 撬板工 · ORD-0557 收口补件（承接块头「撬板工 · ORD-0557 交件 frontend/src/main.tsx」）：逐字尾行漏接是我的腿吃的，坐标不变，并请号令者点一句字典那半

花名「撬板工」。本块只补两件，旧块一字不改（勘误发新件不改旧件）。

一、我自己那条腿的毛病（报出来，不藏）

- 上一块入账时缺了逐字尾行。成因现读：接尾行那步我把中文路径写在 shell 的 heredoc 里，控制台编码把路径吃成乱码，脚本以 FileNotFoundError 退出；那之前代插腿已经把块取走（回执 `_qoder_ledger_inbox\\_processed\\撬板工_1003.md.inserted_101548`）。工具是我的，数与结论不受影响。
- 本块改用写成原件的脚本落盘，尾行逐字取自原件，长度与字节本机现读见脚本自报（`review/撬板工-0557/make_closing_block_r1.py:1`）。

二、交件坐标复述（与上一块逐字同值，一处没动）

- 枝 `refs/heads/review/撬板工-0557-r1`，尖 d3e4617b6b3399faea1c94285b083c3c1585f443；命令原样 `git -C D:/moodle/CityNexus ls-remote origin refs/heads/review/撬板工-0557-r1` 回读同值，出处 `review/撬板工-0557/coordinate_table_r1.txt:1`。
- 产品字节两枚文件、十九枚新键各挂两臂、九十八格静态判据全绿与七十七格红态对照，逐条在上一块第四节，读数原件 `review/撬板工-0557/arm_candidate_r1.txt:3` 与 `review/撬板工-0557/arm_control_tipbytes_r1.txt:3`。
- 让回照旧：`frontend/src/features/execution/LiveRecovery.tsx` 与 `frontend/src/main.tsx` 都已具名归人，本枝不请求并入。

三、请号令者点一句的那半件（这是本块真正要办的事）

- 主张：现尖 2039df0430c5b310fa24874f2f2e7aa8fd3b5816 上，`frontend/src/main.tsx` 调用 main 域键去重二十枚，字典两侧定义零枚；不是静态推断，屏上第 76 行实测读作 Server decision · main.notEvaluated，整屏「not evaluated」命中零枚，逐枚点名在 `review/撬板工-0557/tip_undefined_keys_r1.txt:3`，那次跑测原话在 `review/撬板工-0557/run10_tiptip_keyname.log:4`。
- 机制在字典取词的回读支：两侧都查不到就返回键名本身，现读 `frontend/src/i18n/LocaleContext.tsx:2564`。
- 补法我已备但没动：把这二十枚键按屏上现字各加两臂即可（同批串的逐字对照现成，出处 `review/撬板工-0557/coordinate_table_r1.txt:3`）。要动的是 `frontend/src/i18n/`，而最新那格写的是「字典那枚只发给一扇车道」，所以我停手等一句点头：这二十枚键由谁补、点给哪扇车道。
- 若不点头，屏上那二十处就继续画键名；这是我今晚量到的、使用者能直接看见的最重一条。
"""


def main():
    closing = io.open(CLOSING, encoding="utf-8").read().strip()
    now = datetime.datetime.now()
    name = u"撬板工_%s.md" % now.strftime("%H%M")
    path = os.path.join(INBOX, name)
    text = BODY.rstrip("\n") + u"\n\n" + closing + u"\n"
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    print(u"落 %s｜字节 %d｜尾行取自 %s（长度 %d 字）" % (
        path, len(text.encode("utf-8")), os.path.basename(CLOSING), len(closing)))
    print(u"尾行回读：本文件最后一段逐字相同 = %s" % (text.rstrip("\n").endswith(closing),))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
