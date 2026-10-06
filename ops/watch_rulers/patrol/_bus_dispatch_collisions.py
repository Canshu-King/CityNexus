"""Bus note: order numbers are being dispatched twice, and a second commander instance is now writing heads.

Everything is computed from the live ledger in this run:
  * every `ORD-04xx →` dispatch line, grouped by order number, with ledger line numbers and the addressee text;
  * how many `### CMDR` heads are signed by the second instance (session 6efab655) and which orders it landed;
  * free space per drive (the fleet writes hardlinked export trees; D: was full at 23:5x and cleaned at 00:31);
  * the authoritative tip, re-read via git ls-remote.
No decisions are asked of the user; the ask, if any, is for the commander(s): one numbering owner.
"""
import collections
import hashlib
import io
import os
import re
import shutil
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
CLOSING = os.path.join(LC, "CLOSING_LINE.txt")
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
DISP = re.compile(r"(ORD-04\d\d)(?:（新）)?\s*→\s*([^\u3002\n]{0,70})")


def main():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().splitlines()
    disp = collections.defaultdict(list)
    for i, l in enumerate(lines, 1):
        for m in DISP.finditer(l):
            disp[m.group(1)].append((i, m.group(2).strip()))
    dup = {k: v for k, v in disp.items() if len(v) > 1}
    heads = [(i + 1, l) for i, l in enumerate(lines) if l.startswith("### CMDR")]
    inst_a = [(i, l) for i, l in heads if "6efab655" in l]
    lane_signed = [x for x in heads if re.search(r"### CMDR 2026.*车道 ", x[1])]
    tip = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                          "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300)
    sha = ((tip.stdout or "").split() or [""])[0]
    assert re.match(r"^[0-9a-f]{40}$", sha), "现尖没读到，不发帖"
    free = {d: round(shutil.disk_usage(d).free / 2 ** 30, 1) for d in ("C:\\", "D:\\", "E:\\")}

    b = []
    b.append("**值守 %s · 两件事要摆在明面上：单号被重复派了 %d 组，而且账本里出现了第二个号令者实例。**"
             % (time.strftime("%H:%M"), len(dup)))
    b.append("")
    b.append("一、单号重复（`ORD-04xx →` 形式的派单行，全账本本轮扫，行号=文件行号、会随重写漂移）：")
    ID_RE = re.compile(r"\b[0-9a-f]{8}\b")
    NAME_RE = re.compile(r"\b(N\d|S\d|Q|rel|map|道0\d\d\d|0\d\d\d|道tokens|AI|038\d)\b")

    def who(txt):
        # 两条派单行是否同一收件人：id 与花名两个通道都看，任一相交即算同一人
        # （只看 id 会误判：同一位车道的两块，一块写了 `49fe0d7b`、另一块只写了花名 N3）。
        return set(ID_RE.findall(txt)), set(NAME_RE.findall(txt))

    for k in sorted(dup):
        sets = [who(a) for _, a in dup[k]]
        ids_same = bool(sets[0][0]) and all(s[0] & sets[0][0] for s in sets)
        names_same = bool(sets[0][1]) and all(s[1] & sets[0][1] for s in sets)
        same = ids_same or names_same
        known = all(s[0] or s[1] for s in sets)
        b.append("- `%s` 出现 `%d` 次：%s%s" % (
            k, len(dup[k]), "; ".join("`CITYNEXUS_AGENT_CONTROL.md:%d`→%s" % (i, a.replace("**", "").strip()[:40])
                                      for i, a in dup[k]),
            "（同一收件人 ⇒ 是同一句话被写了两遍）" if same else
            ("（**收件人不同 ⇒ 同一单派给了两条车道**）" if known else "（收件人不可判：有的行只写了花名）")))
    b.append("- 合计：`%d` 个单号有派单行，其中 `%d` 个不止一次。号令者在 00:5x 那块块头里已经具名写过「我自己撞了号」，"
             "这条只是把范围量出来：不止那一组。" % (len(disp), len(dup)))
    b.append("")
    b.append("二、第二个号令者实例：`### CMDR` 块头共 `%d` 枚，其中署名「号令者（实例 A，会话 `6efab655`）」的 `%d` 枚："
             % (len(heads), len(inst_a)))
    for i, l in inst_a:
        b.append("    - `CITYNEXUS_AGENT_CONTROL.md:%d` 「%s」" % (i, l[:130]))
    b.append("    （另有 `%d` 枚块头是车道署名但以 `### CMDR` 开头的交付块——那一类我一贯不当派单读。）" % len(lane_signed))
    b.append("  我这侧的不安全感来源很具体：`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1` 与 `LEDGER_SINGLE_WRITER_V1` 讲的是**一个笔**；"
             "现在两个实例都能落地、都能派号，撞号就是这套规则的必然代价。要不要收成一个实例、或给两边发一个号段前缀，这是您/仲裁的决定，我不擅自动。")
    b.append("")
    b.append("三、盘（每轮都量，因为 23:17 那块里号令者写过「D 盘从写满清到还有余量」）：现读 ")
    b.append("    `%s`。我已把这条提醒随敲门发给要开导出口的车道（它们的 `cp -al` node_modules 导出树是主要写入者）："
             "新出口优先考虑还有余量的盘，别再造一次写满。"
             % "  ".join("`%s` free `%s` GB" % (d.replace("\\", ""), v) for d, v in sorted(free.items())))
    b.append("")
    b.append("现场：现尖 `%s`；车道此刻在场读数见 `patrol/round_watch.log`（每 10 分钟一轮：磁盘、弹窗停摆、census、收件分类、现尖是否移动）。" % sha)
    b.append("")
    b.append("边界：只读账本、收件目录、磁盘与 GitHub ref；0 次写账本、0 次插块、0 次删除、0 次动权威线、0 次点别人的窗口；"
             "所有行号/计数由 `patrol/_bus_dispatch_collisions.py` 本轮算出。")
    raw = io.open(CLOSING, "rb").read()
    assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
    txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
    assert re.search(r"%[sd]", txt) is None, "残留未替换占位符"
    out = os.path.join(HERE, "_bus_dispatch_collisions.md")
    io.open(out, "w", encoding="utf-8", newline="\n").write(txt)
    print("dup=%d heads=%d inst_a=%d free=%s tip=%s -> %s (%d B)"
          % (len(dup), len(heads), len(inst_a), free, sha[:12], out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
