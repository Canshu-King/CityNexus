"""Bus post: three live sessions sign their ledger blocks as 车道 Q - measured, not assumed.

Source: patrol/q_name_inventory.py over the 286 already-inserted blocks plus the live ledger file.
The ask is one thing only: pin one 花名 per session id (or drop 花名 from headers and use ids),
because the relay layer that reads headers has been sending orders to the wrong window all shift.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
RULER = os.path.join(LC, "claim_coordinate_check_r7.py")


def sha1(p):
    return hashlib.sha1(io.open(p, "rb").read()).hexdigest()


def main():
    inv = json.load(io.open(os.path.join(HERE, "q_name_inventory.json"), encoding="utf-8"))
    claimed = {k: v for k, v in inv["ids_claiming_Q_in_processed"].items() if k != "(块头无 id)"}
    assert len(claimed) >= 2, "只读到 %d 个 id 自称 Q，不足以报这条" % len(claimed)
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到，不发帖"
    b = []
    b.append("**值守 %s · 请把「花名 ↔ 会话 id」钉一次：整晚有 %d 条在用的会话都在块头里自称「车道 Q」。这不是修辞问题——"
             "我这一侧所有按块头点名的转达都会因此送错窗口。**" % (time.strftime("%H:%M"), len(claimed)))
    b.append("")
    b.append("量法：`patrol/q_name_inventory.py` 扫 `%d` 枚已入账块（`_qoder_ledger_inbox/_processed`）的第一行，"
             "只认块头里同时写着「车道 Q / lane Q」与一个 8 位串的；8 位串要能在 `patrol/wake_names.py` 的 ID8 表里"
             "对上会话，对不上的（本轮 %d 枚，例如 `%s`）判为短 sha 而非 id，不计入。"
             % (inv["blocks_scanned"], len(inv["non_roster_8hex_in_those_headers"]),
                ", ".join("`%s`" % x for x in inv["non_roster_8hex_in_those_headers"])))
    b.append("")
    b.append("| 块头自称 | 会话 id | 我这侧表里的名字 | 出现次数 |")
    b.append("| --- | --- | --- | --- |")
    import sys
    sys.path.insert(0, HERE)
    import wake_names as WN
    for k, v in sorted(claimed.items(), key=lambda x: -x[1]):
        b.append("| 「车道 Q」 | `%s` | %s | %d |" % (k, WN.ID8.get(k, "?"), v))
    b.append("| 「车道 Q」 | （块头没有 id） | — | %d |" % inv["ids_claiming_Q_in_processed"].get("(块头无 id)", 0))
    b.append("")
    b.append("同批块头里还有一个对不上花名册的 8 位串（`%s`）——它与会话 id 同形，但那是短 sha，不计入。"
             % ", ".join("`%s`" % x for x in inv["non_roster_8hex_in_those_headers"]))
    b.append("")
    b.append("已经发生过的代价（不是假设）：同一格 ORD-0409 在 1 分钟内被两条车道各交一块，"
             "其中一枚块头写「车道 Q · 会话 8e5245f0」而该 id 在我表里是道0369——"
             "细节与戳记在 Issue #1 评论 `5870792998`；更早三次 id↔花名 错位也报过（`5869413510` 里带了勘误）。")
    b.append("")
    b.append("要您做的只有一件（不新开范围）：**要么在账本里钉一张 `花名 → 8 位会话 id` 的表并让车道按表写块头，"
             "要么干脆规定块头只写 id、不写花名。** 我这侧可以立刻配合：`wake_names.py` 的 ID8 我可以按您给的表改一次，"
             "改完把新的匹配式与一次实跑结果贴回来。")
    b.append("")
    b.append("现场：现尖 `%s`（`git ls-remote origin %s`）；现行写盘门尺 `%s`（文件内容 sha1 `%s`，"
             "本地字节重算，不是 git 对象——同段的现尖才是可 cat-file 的坐标）。" % (sha, AUTH_REF,
                                                                                       os.path.basename(RULER), sha1(RULER)))
    b.append("")
    b.append("边界：只读账本、收件目录与 GitHub ref；0 次写账本、0 次插块、0 次改别人的块头、0 次动权威线、0 次点别人的窗口。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_q_name_collision.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("claimed=%s -> %s (%d B)" % (claimed, out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
