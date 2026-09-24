"""Wire the ORD-0278 continuation copy into both dictionaries, and stop the `en` dictionary
speaking Chinese for the ORD-0269 keys.

Written as a script because the two dictionaries hold byte-identical lines for these keys, so an
editor anchor cannot tell them apart -- the same reason the leak exists: the first cut pasted the
Chinese sentence into both blocks (the mirror of ORD-0240's defect).

Every replacement is asserted: the en block ends up with 0 CJK values other than `nav.language`,
which legitimately names a language in its own script.
"""

import re
import sys

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PATH = "D:/moodle/_qoder_d_lane_20260923/frontend/src/i18n/LocaleContext.tsx"
CJK = re.compile(r"[\u3400-\u9fff]")
ALLOWED_EN_CJK = {"nav.language"}

EN_CONTINUATION = """  /* ORD-0269 cells 1 and 3, and ORD-0278's outcomes.  These are the `en` copies: the Chinese
     sentences live in `zhCN` below and neither dictionary may hold the other's language -- an
     English screen answering a traveller in Chinese is ORD-0240's defect in the other coat.
     `nav.language` stays 「中文」 on purpose: a language switcher names each language in its own
     script, which is a value, not a leaked sentence. */
  "hub.continuationPending":
    "A plan started on this device did not finish: the first step completed, but no plan came out of it.",
  "hub.continuationResume": "Continue this plan",
  /* ORD-0278: pressing this re-issues the SECOND leg carrying the recorded mission.  Each outcome
     says what actually happened.  A refusal never dresses an HTTP status up as the server's reason:
     that label is only ever filled with text the server itself sent. */
  "hub.continuationResuming": "Continuing…",
  "hub.continuationResumed": "The second step went through, and the new plans are below.",
  "hub.continuationResumedEmpty":
    "The second step went through, but this round produced no new plan.",
  "hub.continuationResumeRefused":
    "The server refused this attempt. Nothing was created, and the record is still here so you can try again.",
  "hub.continuationResumeDeadline":
    "This wait reached the limit this screen allows. The request may or may not have arrived -- refresh to check before pressing again.",
  "hub.continuationResumeTransport":
    "This device could not send the request at all (connection failure). The record is still here.",
  "hub.continuationUnconfirmable":
    "There is a record of the last plan, but its progress cannot be read now, so how far it got is unconfirmed.",
"""

ZH_CONTINUATION = """  // ORD-0269 cells 1 and 3: continuation reveal. On-this-device is the named coverage boundary.
  // ORD-0278: 按下这一键是把第二步带着那枚 mission 再发一次；每种结果各说各的话，
  // 「服务器给出的原因」这一标签只填服务器真发来的文字，服务器没给就明说是本机说的。
  "hub.continuationPending": "上次有一次规划在这台设备上没跑完：前半段已完成，但还没有产出方案。",
  "hub.continuationResume": "继续这次规划",
  "hub.continuationResuming": "正在续发…",
  "hub.continuationResumed": "已接着上次把第二步发出去，新方案在下面。",
  "hub.continuationResumedEmpty": "已接着上次把第二步发出去，但这一轮没有产出新方案。",
  "hub.continuationResumeRefused": "服务器拒绝了这一次尝试。没有产生新东西，上次的记录还在，你可以再试一次。",
  "hub.continuationResumeDeadline": "这一次等待到了本屏幕允许的时限。请求可能已经到达、也可能没有——请先刷新确认，不要连着再点。",
  "hub.continuationResumeTransport": "这一发在本机就没送出去（连接失败）。上次的记录还在。",
  "hub.continuationUnconfirmable": "上次规划有记录，但现在读不到它的进度，无法确认进行到哪一步。",
"""


def main() -> int:
    src = open(PATH, encoding="utf-8", newline="").read()
    original = src

    en_start = src.index("const en: Dict = {")
    zh_start = src.index("const zhCN: Dict = {")
    dict_start = src.index("const dictionaries: Record<TripLocale, Dict>")
    en_block, zh_block = src[en_start:zh_start], src[zh_start:dict_start]

    old_en_keys = [
        '"hub.continuationPending": "上次有一次规划在这台设备上没跑完：前半段已完成，但还没有产出方案。",',
        '"hub.continuationResume": "继续这次规划",',
        '"hub.continuationUnconfirmable": "上次规划有记录，但现在读不到它的进度，无法确认进行到哪一步。",',
    ]
    old_stanza = "  " + "\n  ".join(old_en_keys)
    if en_block.count(old_stanza) != 1 or zh_block.count(old_stanza) != 1:
        print("ABORT: the three continuation lines are not the single shared stanza I expected")
        return 2

    new_en = en_block.replace(old_stanza, EN_CONTINUATION)
    new_zh = zh_block.replace(old_stanza, ZH_CONTINUATION)
    src = src[:en_start] + new_en + new_zh + src[dict_start:]

    # Assertions on the result, not on the intent.
    en_end = src.index("const zhCN: Dict = {")
    en_again = src[src.index("const en: Dict = {") : en_end]
    pairs = re.findall(r'"([a-zA-Z0-9.]+)":\s*(?:\n\s*)?"([^"]+)"', en_again)
    leaks = {key for key, value in pairs if CJK.search(value)} - ALLOWED_EN_CJK
    if leaks:
        print(f"ABORT: the `en` dictionary still carries Chinese values: {sorted(leaks)}")
        return 3
    for key in (
        "hub.continuationResuming",
        "hub.continuationResumed",
        "hub.continuationResumedEmpty",
        "hub.continuationResumeRefused",
        "hub.continuationResumeDeadline",
        "hub.continuationResumeTransport",
    ):
        if src.count(f'"{key}":') != 2:
            print(f"ABORT: {key} should exist in both dictionaries, found {src.count(chr(34) + key + chr(34) + chr(58))}")
            return 4
    print(f"rewrote {len(original)} -> {len(src)} bytes; en CJK leaks = {len(leaks)} (allow-list: {sorted(ALLOWED_EN_CJK)})")
    open(PATH, "w", encoding="utf-8", newline="").write(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
