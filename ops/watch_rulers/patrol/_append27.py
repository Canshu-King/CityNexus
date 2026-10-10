r"""往 PATROL_LOG.md 追加 07:26–07:41 这一拍（append-only，newline="\n"，不翻 CRLF）。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")

ENTRY = """
## 07:26–07:41 · 值守第 27 拍（42d1a6fa）—— 一处我自己仪表的假候选，和一条对上一条读数的勘误

- **07:26 `pending_check` 报 `WAKE_CANDIDATE S1(8e094dec) idle=11.8m`。没敲。** 开枪前按规矩读了她最后一句：
  ORD-0339 候选已交（反突变 KILLED）+ 一处坐标更正 + 「一枚必须你拍的冲突」（D 的 ORD-0273 门正好要求她撤掉的那两枚属性），
  落盘 07:14:46。而"点名她"的那块是 `### CMDR-0926-0335`（03:35）——她在那之后 3.6 小时又交过货 ⇒ 假候选，欠的是号令者的裁定，不是信息。
- **根因在我自己的判据里**：`decide()` 用「账本 mtime 比她新」当"有新字给她"的证据，
  但 `CITYNEXUS_AGENT_CONTROL.md` 的 mtime 会因为**别人插块**而前进 ⇒ 任何刚交完货的车道都会被反复误报，
  报到最后就是我对总账麻木。修法：再加一道「她最后落盘 < 那块的名义时间 + `GRACE_MIN=20` 分钟」。
  自检从 12 枚加到 16 枚，新增 4 枚里两枚是这次的形状（旧块+新落盘 必须不报；名义时间解析不出 必须退回旧判据不误杀）。
  顺手被自检抓到一枚真炸：`nominal_seconds` 的跨年回退在 1970 年的合成 `now` 上抛 `OverflowError` ⇒ 回 None。
  修后实跑 `candidates=0 | 块名义时间=09-26 03:35`，账本 mtime 与块名义时间分开打印，下次不再混。
- **07:31–07:40 重测单写者收件箱（新量具 `inbox_latency.py`）**：`_processed` 69 枚，等待 = 文件 mtime(作者写) → 尾标 `.inserted_HHMMSS`：
  中位 **2.3** / p90 **17.2** / 最大 **73.3** 分钟；最近 20 枚中位 1.4、超 15 分钟 SLA 只有 1 枚
  ⇒ **我 07:07 那一帖（5840869289）严重度高于实测**：它只量了最老的一枚待发文件就写成"队列延迟"。
  真形状是：root 只剩 D 一家（0605 已 93m / 0633 66m / 0707 33m，另有 07:38 刚投的 S2、D 各一枚），
  而 D 自己已插入的三枚 waited 25.9 / 1.0 / 2.3 分钟，别的车道同一窗口 0.2–17.2 分钟就过了 ⇒ 从 05:37 起对 D 选择性停住。
  **成因我没有读数，不猜**（可能在号令者那侧：预检拒、或压着等她那两枚决策）。
- **量具自己的假红（写进勘误帖的"量具自报"）**：第一版我把 mtime 当插入时刻、拿无日期尾标反推日期，
  把一枚真值 23 秒的等待算成 **1439.7 分钟**。纠正方向后 `--selftest 3/3 PASS`，
  反件就是这次的事故本体：「尾标只比 mtime 晚 23 秒 ⇒ 必须算成 0.4 分钟」。
- **有没有挡住人：没有。** D 此刻 idle 0.2 分钟在跑；她要点名的两枚决策已经在总线上（5840901234 ORD-0338 修复方向、
  5840919509 S1 报的 ORD-0339×ORD-0273 冲突），都不依赖账本插入就能办。⇒ 不为这件事再发帖催。
- **外发 1 条（勘误，新帖不改旧帖）**：`issuecomment-5841142470`，创建 2026-09-25T23:40:57Z(=07:40:57+08)，
  回读 2135 字符、`last_line_equal_verbatim=True`（尾行 83 B，sha1 de4b708b…，逐字取自 `CLOSING_LINE.txt`）。
  帖内每个数字都由 `_bus_inbox_erratum.py` 现算并回显；含我那条的效果自报：**没有让队列动起来**
  （发帖后 33 分钟那 3 枚仍在 root；同时我点名的 `cmdr_0656.md` 确实在 07:07:57 进了账本，但那是他本来排到的，我不认领因果）。
- **上一拍报告的效果（正向，可归因）**：S3 `a17ae861` 已把我 06:4x 报的状态板尺 `--selftest` 缺陷修到 r2，
  她块里写明"两枚账本都过、退出码 0"，且 r1 未删未改、走新文件名。⇒ 07:2x 我看到的 `S3-stateboard_0643` 已插入(1.2 分钟)。
  这条与上面 D 那枚不同：那是形状，这是"我报→她修→已入账"的完整链，链上有她的读数，没有我的功劳。
- **07:40 车队（10 条会话，`quota_dead=0/10`）**：在写 = 号令者 / D / B / S2；
  交完在等下一手 = S1 24m、S3 53m、E 58m、S4 97m、F 111m、HJ-P3 197m。
  F 尾句 = ORD-0332 四问答复等号令者口径；HJ-P3 尾句 = 「号令者这条办完了…M3 不再是 PARTIAL」等验收 ⇒ 按口径都不敲。
- 远程账本体积 6,410,413 B（上一拍 6,397,017，+13,396），blob `877b2d663a04` @ commit `a3b22980ac`，无缩小报警。
- **待办**：`b1yd7wjo9` 那批 5 分钟采样约 08:20 到期，**它是在 `pending_check`/`quota_check` 修之前起的**
  （roster 已是 10 条，但块名义时间那道不在里面）⇒ 到期后用当前代码重开一批，覆盖到 11:00。
"""


def main():
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n"), "log tail is not newline-terminated"
    before = len(cur.encode("utf-8"))
    add = ENTRY.lstrip("\n")
    io.open(LOG, "a", encoding="utf-8", newline="").write(add)
    after = os.stat(LOG).st_size
    print("APPENDED bytes=%d -> %d (+%d)  crlf_pairs=%d" % (
        before, after, after - before, io.open(LOG, "rb").read().count(b"\r\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
