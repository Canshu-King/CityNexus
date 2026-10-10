# -*- coding: utf-8 -*-
"""relay.py — 把「号令者写进账本、点名某条已停的车道」的要求，打包成一条可直接发的转达件。

为什么需要它：号令者 17:03 那块自己写着「用户不在，不能敲窗」，于是它把派单写进账本；
但冷车道不会自己回读账本（这条本项目记过很多次）。我能动车道（不能动号令者），所以我做信使。

用法：
  python -X utf8 relay.py 2.0          # 扫最近 2 小时的账本提交，为每个「被点名 + 之后没动」的车道生成 relay_<id8>.txt
  python -X utf8 relay.py --list       # 只列要转给谁、在第几行，不写文件
生成的每条都以 CLOSING_LINE.txt 逐字结尾，并断言没有未替换占位符。
本子命令本身不发消息——发不发由我逐条看过后决定。
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import wake_names as WN  # noqa: E402
import quota_now  # noqa: E402

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\CityNexus"
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
STATE = os.path.join(HERE, "relay_state.json")
OUTDIR = os.path.join(HERE, "relay")


def load_state():
    try:
        return json.load(io.open(STATE, encoding="utf-8"))
    except Exception:
        return {"sent": {}}


def save_state(st):
    io.open(STATE, "w", encoding="utf-8", newline="\n").write(json.dumps(st, ensure_ascii=False, indent=1))


def tip():
    r = subprocess.run(["git", "-C", REPO, "-c", "http.proxy=", "-c", "https.proxy=",
                        "ls-remote", "origin", AUTH_REF], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=90)
    sha = (r.stdout or "").split()[:1]
    if not sha:
        return None
    g = subprocess.run(["git", "-C", REPO, "log", "-1", "--date=iso-local", "--format=%ad | %s", sha[0]],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return sha[0], g.stdout.strip()


def blocks_with_lines():
    """账本里每枚块：(标题行号, 标题, 正文)。"""
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    out = []
    idx = [i for i, l in enumerate(lines) if l.startswith("### ")]
    for k, i in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(lines)
        out.append((i + 1, lines[i], "\n".join(lines[i + 1:end])))
    return lines, out


def idle_since(id8):
    g = glob.glob(os.path.join(quota_now.BASE, id8 + "*.jsonl"))
    if not g:
        return None, False
    mtime = os.stat(g[0]).st_mtime
    lr, ca, caps = quota_now.scan(g[0])
    capped = bool(ca) and ca >= lr
    return mtime, capped


def main():
    listing = "--list" in sys.argv
    # 只吃 wake_from_commits 的产物：那一份是「服务器提交时间」与「该车道最后落盘时间」两侧都量过的候选。
    # 不扫账本正文顺序——账本按作者分块插入，块在文件里的位置不代表新旧（这条本项目记过很多次）。
    art = os.path.join(HERE, "wake_candidates.json")
    # 允许指到别的清单文件（我用它做自测：`relay.py relay_selftest_candidates.json --dry`），
    # 这样测的时候不污染真实 relay_state.json
    for a in sys.argv[1:]:
        if not a.startswith("--") and a.endswith(".json"):
            art = os.path.join(HERE, a)
    if not os.path.exists(art):
        print("先跑：python -X utf8 wake_from_commits.py <小时数> 生成 wake_candidates.json")
        return 2
    d = json.load(io.open(art, encoding="utf-8"))
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split(chr(10))
    st = load_state()
    tp = tip()
    made = []
    for c in d.get("candidates") or []:
        nm, id8, head, body = c["lane"], c["id8"], c["head"], c["body"]
        # 09-29 05:28 的硬遮门：号令者的两个会话实例都不是车道，永远不给它们生成"待敲门"件
        # （用户明确要我不要给 494abfd7 发消息；这里就算上游判据漏了也到不了我手上）。
        if id8 in ("494abfd7", "6efab655") or nm in ("号令者", "号令者（实例 A）"):
            print("  跳过 → %s(%s)：号令者会话，不生成转达件" % (nm, id8))
            continue
        # 提交里捕获的块头**不含** `### ` 前缀（wake_from_commits 的正则吃掉了它），所以比对要先剥掉
        ln = next((i + 1 for i, l in enumerate(lines) if l.startswith("### ") and l[4:].strip() == head.strip()), None)
        key = "%s@%s@%s" % (nm, c["commit_at"], (ln or 0))
        if key in st["sent"]:
            continue
        mt, capped = idle_since(id8)
        idle_min = (time.time() - mt) / 60.0 if mt else 0.0
        if capped or idle_min < 12.0:
            print("  跳过 → %s：%s" % (nm, "被额度掐着" if capped else "在动（idle %.1f 分）" % idle_min))
            continue
        # 取正文里点到它的段落：必须命中这辆车的花名匹配式（含指向词），
        # 不能拿「段里出现 rel 三个字母」当点名——rel/map/Q 这类名字会落在 controller、mapping 里。
        all_paras = body.split(chr(10) + chr(10))
        idxs = [i for i, p in enumerate(all_paras) if WN.hits_for(nm, p) or id8 in p]
        # 「点名那句」和「它的要件」常常不在同一段（18:07 那次只送出一个小标题，车道没法做）
        # ⇒ 命中段之后连带取 3 段，直到下一枚标题或被取满
        paras = []
        for i in idxs[:2]:
            for q in all_paras[i:i + 4]:
                if q not in paras:
                    paras.append(q)
        fell_back = not paras
        if not paras:
            paras = [body[:1200]]
        # 文件名带块行号：同一分钟给同一辆车转达两块时不会互相覆盖（17:52 那次就撞过，靠手工核对才发现）
        fn = os.path.join(OUTDIR, "relay_%s_%s_L%s.txt" % (id8, time.strftime("%H%M"), ln or 0))
        os.makedirs(OUTDIR, exist_ok=True)
        b = []
        b.append("【值守 %s → %s（会话 %s）· 账本里有一块在等你一步，你 idle %.0f 分钟；号令者写「用户不在，不能敲窗」，我替它把要求送到】"
                 % (time.strftime("%H:%M"), nm, id8, idle_min))
        b.append("位置：" + ("`D:/moodle/CITYNEXUS_AGENT_CONTROL.md:%d`" % ln if ln else "账本里（行号这一轮没定位到，按块头找）") + "，块头逐字「%s」。" % head[:150])
        if tp:
            b.append("我独立核过的现尖：`git ls-remote origin %s` = `%s`（%s）。" % (AUTH_REF, tp[0], tp[1]))
        b.append("")
        b.append("它要你的那一段，逐字转达：" if not fell_back else "这块正文里我没认出点你名的段落（匹配式见 `wake_names.py`），所以把整块开头原样贴给你，去账本里找属于你的那一段：")
        for p in paras[:3]:
            b.append("> " + p.strip().replace(chr(10), " ")[:1400])
        b.append("")
        b.append("交件规矩（09-29 02:2x 校正：现行代插门与尺的名字，别照旧文档跑）："
                 "新块进 `D:\\moodle\\_qoder_ledger_inbox\\<你的车道前缀>_<HHMM>.md`，首行 `### `。"
                 "现行门是 `ledger_inbox_apply_r2.py` → `ledger_insert_after_r2.py:28` 调的尺是 "
                 "`claim_coordinate_check_r7.py`（本机文件 sha1，非 blob：`2690a3f7eb0b817a882212854ad906bfc8703e2d`），"
                 "**不是 r4e**；先自己跑 r7 再交，退出码非 0 就别交。"
                 "裸数字在**同一行**带 `path:line`/`field=value`/完整 40 位 blob，别删数字。"
                 "第二道闸（坐标闸）两条都满足才算干净：每个 40 位十六进制值要么能 `git cat-file`"
                 "（门会先 fetch 全部分支，所以 push 过的新枝 blob 取得到），要么它**自己那一行**写明不可取回"
                 "（`文件 sha1|本机 sha1|从未入 git|不在对象库|非 blob`…）**且**同一**段落**（连续非空行、中间不空行）"
                 "里有一枚可解析坐标。旧块改名留痕时**去掉尾巴的 `.md`**（门认 "
                 "`^[A-Za-z0-9._-]+_[0-9]{4}\\.md$`，留着会被当待插块反复拒）。"
                 "push 用新枝名，别覆盖已交过的 ref，并回一枚 `git ls-remote` 回读到的 40 位。")
        b.append("环境：本机 `HTTPS_PROXY` 指向没人听的端口（:7892/:7897 LISTENING 行数各 0），git 用 `git -c http.proxy= -c https.proxy=`，"
                 "跑供应商要么 `set HTTPS_PROXY=` 要么 `httpx.Client(trust_env=False)`；后端套件只有 `CityNexus/.venv` 的 3.12.14 跑得动。")
        b.append("边界：我不动权威线、不写账本、不插块、不碰别人的 worktree，也不替你判断方向——上面那段是号令者写进账本的原话。")
        b.append("")
        raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
        assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
        txt = "\n".join(b) + "\n" + raw.decode("utf-8").strip() + "\n"
        assert re.search(r"%[sd]", txt) is None, "正文残留未替换占位符"
        if listing:
            print("  要转达 → %-9s (%s) idle %.0f 分  块在行 %d  「%s」" % (nm, id8, idle_min, ln, head[:60]))
            continue
        io.open(fn, "w", encoding="utf-8", newline="\n").write(txt)
        st["sent"][key] = {"file": os.path.basename(fn), "at": time.strftime("%H:%M"), "lane": nm}
        made.append((nm, id8, fn, len(txt.encode("utf-8"))))
    save_state(st)
    if listing:
        print("(--list：只列，不写文件，也不记 state)")
        return 0
    for nm, id8, fn, size in made:
        print("生成 %s → %s (%d B)" % (nm, os.path.basename(fn), size))
    if not made:
        print("本轮没有需要转达的（要么没人被点名，要么被点名的都在动，要么已转达过）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
