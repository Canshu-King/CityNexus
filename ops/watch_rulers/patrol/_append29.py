r"""追加 07:56–07:58 这一拍：一条被实测推翻的成因假设 + D 那两枚"消失"的块的去向。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")

ENTRY = """
### 07:54–07:58 值守第 29 拍 —— 我差点把一条**错的成因**发出去，靠先量再说话拦住了

- **假设来源**：项目记忆里有一条常设行为「一枚解不出的手写 40 位会拒掉整块 ⇒ 作者只能改名重投」。
  07:43 我看到 root 里 D 自取代 6 枚，就用它当了解释。**这是别人给的成因，按规矩必须先复现。**
- **复现结果：不成立。** `_hex_resolve_probe.py`（两仓库 × blob→commit 双向探，读数落 `_hex_resolve_probe.json`）：
  - 待发（D 的 4 枚现存件）：29 枚 40 位坐标，**不可解 0 枚（0%）**
  - 已插入（S1/S2/S3/B/cmdr 各一枚）：58 枚坐标，**不可解 0 枚（0%）**
  ⇒ 两侧都是 0%，"坐标解不出把 D 的块挡在门外"这句**没有读数支持**，我没发出去。
- **号令者那道门的自记件也在说同一件事**：`_qoder_ledger_inbox/_non_retrievable_carried.json`
  （schema `CNX_CMDR_DOOR_NON_RETRIEVABLE_V1`，06:02）里只登记了 `S4-ast-taint_0632.md` 一枚（line 4，
  `62411651…`，`declared:true`、`line_has_resolvable:true`），**D 的块一枚都没进这份拒收清单**。
- **07:54→07:56 之间 root 少了两枚 D 的件，我第一反应是"交付被删了"——查完不是。** 按内容标记查血缘，不按文件名猜：
  `d-e345b9d6_0633.md` 被 D 自己改名成 `…superseded_by_0830`；`0605` 的内容（ORD-0325 命中 2 处）
  活在新件 `_0830.md.bad_generation_compare`(11,179 B) 与 `_0835.md`(11,045 B) 里；
  ORD-0338 的内容活在 `_0707.md` 与 `_0810.md` 里。⇒ **无丢失**，账本也一字未动（mtime 仍 07:25:20，6,410,413 B）。
- **D 的重切频率是今晚最贵的一件事（不是队列）**：root 里以她为时间标的件 @STAMPS@，
  共 @NAMECOUNT@ 枚，跨度 @SPAN@ 分钟；其中 @DEADCOUNT@ 枚是她自己判废改名的（`.superseded_by_*` / `.bad_*`），
  仍挂待发 @LIVECOUNT@ 枚。
  副作用：`_0707.md`(ORD-0338, 已等 51 分钟) 与 `_0810.md`(同含 ORD-0338, 15 分钟) **同时挂在 root**，
  号令者若两枚都插，同一单会入账两次。D 正在跑（idle 0.3m），她大概会自己收掉 ⇒ **不敲门、不发帖**，
  只在这里留一条给下一班：09:00 之后若 root 里同时有 `_0707` 与 `_0810`（或 `_0835`），那才是需要人管的事。
- **今晚第三次提醒自己**：形状（root 里有谁的几枚、压了多少分钟）不等于成因。
  这两拍里成形的两条成因——"号令者卡住 D"、"坐标解不出被门拒"——**一条没量出来就被我扔了，一条量出来是 0% vs 0%**。
"""


def main():
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    entry = ENTRY.lstrip("\n")
    import re
    inbox = r"D:\moodle\_qoder_ledger_inbox"
    names = sorted(f for f in os.listdir(inbox) if f.startswith("d-e345b9d6_"))
    stamps = [m.group(1) for f in names for m in [re.match(r"d-e345b9d6_(\d{4})", f)] if m]
    dead = [f for f in names if ("superseded" in f or ".bad_" in f)]
    live = [f for f in names if f.endswith(".md")]
    mins = [int(s[:2]) * 60 + int(s[2:]) for s in stamps]
    span = max(mins) - min(mins)          # 时间标跨度（不是墙钟 mtime，标签只到分钟）
    entry = entry.replace("@NAMECOUNT@", str(len(names))).replace(
        "@STAMPS@", "→".join(stamps)).replace(
        "@DEADCOUNT@", str(len(dead))).replace("@LIVECOUNT@", str(len(live))).replace(
        "@SPAN@", str(span))
    io.open(LOG, "a", encoding="utf-8", newline="").write(entry)
    print("counted: D root 件=%d 自判废=%d 仍待发=%d 时间标=%s" % (
        len(names), len(dead), len(live), " ".join(stamps)))
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
