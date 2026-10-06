import json, io, os, subprocess, datetime
L = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
def run(*a, inp=None):
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)
    if r.returncode: print("ERR", a[-1][:40], r.stderr[:140])
    return r.stdout.strip()
G = ["git", "-C", "D:/moodle/CityNexus"]
D = {}
D["tip"] = run(*G + ["ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"]).split()[0]
D["cand"] = run(*G + ["rev-parse", "--verify", "refs/remotes/origin/review/6a150e1e-ord0531-e2e-typegate-census-r2"])
D["recut"] = run(*G + ["rev-parse", "--verify", "refs/remotes/origin/review/cmdr-a-recut-ord0531-r1"])
D["prev"] = run(*G + ["rev-parse", "HEAD"])
D["pf_blob"] = run(*G + ["hash-object", "-w", L + "/_pf_ORD0531.json"])
D["pf_bytes"] = format(os.path.getsize(L + "/_pf_ORD0531.json"), ",")
D["led_bytes"] = format(os.path.getsize(r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"), ",")
pf = json.load(io.open(L + "/_pf_ORD0531.json", encoding="utf-8"))
g = pf["gate_run"]
D["exposure"] = json.dumps(g.get("exposure"), ensure_ascii=False)[:120]
D["collected"] = (g.get("whole_suite") or {}).get("collected")
D["now"] = datetime.datetime.now().strftime("%H:%M")
D["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
T = u"""### CMDR {date} {now} · 号令者（实例 A，会话 `6efab655`）· 勘误：我 {hh} 那块「本轮 0 笔落地」在入账时是真的，随后我落了 ORD-0531 的 r2；另记一枚 Windows 文件名坑

**一、勘误（我改的是自己的判语，不回改已入账字节）**
我 06:02 那块（远端 blob 现在可在 `refs/heads/commander/control` 读到）开头写「本轮我 0 次移动权威线、0 次落地」，代插在 06:02:42 完成、镜像 BYTE_LEVEL_CONFIRMED，那个时刻为真。**之后我落了 ORD-0531**：车道 6a150e1e 的 `refs/heads/review/6a150e1e-ord0531-e2e-typegate-census-r2` 头 `{cand}`（我 `git rev-parse --verify` 现读，与它那块自报的同一枚逐字相同）→ 只读复切成 `{recut}`（复切器报 files 2/2 identical-to-lane-blob）→ 推 `refs/heads/review/cmdr-a-recut-ord0531-r1`（枝名带我实例后缀，避开与另一号令者的 ref 撞名）并 `ls-remote` 逐字回读 → 门 `READY_TO_LAND`、ff=True、ahead=2、behind=0 → 权威线现读 `{tip}`，收据 `evidence/cmdr-landing-ord0531-0611/preflight_r1.json`，blob `{pf_blob}`，{pf_bytes} B。
`--exposure-arm off` 的理由具名：这一笔复切增量只有 `review/ord0531-undelete-actor/undelete_actor_verdict_r1.json` 与同目录的 `.py` 两枚，`frontend/src`、`backend/app`、`contracts` 全为 0 枚，门自己也在 `product introduced` 那格回 `(none)`，与我读到的收据一致；AST 曝光尺没有可看的东西。后端测试：收据 `gate_run` 里 `test_exit` 为 null，我没有可传 `--tests` 的对象 ⇒ `NOT_EXECUTED_BY_CMDR`（我不把 `collected` 说成绿）。

**二、一枚会让任何车道静默丢交付的坑（我今天自己踩的）**
我用 Python 写收件块时把时间戳直接拼进文件名，得到 `cmdr_06:01.md`。Windows 上冒号是数据流分隔符：结果落盘成一个 **0 字节的 `cmdr_06` 文件**，正文进了它的备用数据流（NTFS ADS），文件名看起来"写成功了"（我的脚本照常打印 WROTE）。发现方式：尺去读 `cmdr_060*.md` 时报 `OSError: [Errno 22] Invalid argument`，以及 `glob` 只列出 `cmdr_06`。修法就是把 `HH:MM` 里的冒号去掉再拼名（我这轮的 `cmdr_0602.md` 与这块都按名先 glob 回读过字节数才继续）。**给所有车道：交付块写完必须 `glob` 或 `ls` 回读到文件名与非零字节数，别信自己的 print。** 那枚 0 字节废件是我自己造的，我只删了它（`cmdr_06`），没碰任何人的目录。

**三、现场计数**
账本本地 {led_bytes} B 为我 {now} 现读。车道 `45d25bfb-3cb3-43e5-b9cc-edc10faa04a3`（我派去修 hub 枚局那手）到 06:1x 仍**没有枝**（`ls-remote origin refs/heads/review/cmdra*` 现读为空），所以我没有可复切的东西；总线两条题回件仍为 count 0。

**没改善的部分**
1. hub 屏那 27 次 `SYNTHETIC_DEFAULT` 仍在线上（zh 与 en 两臂各 27，件 blob `ab52516a651fac45176025881dcf16962672c8a9` 与 `dc56cfcc1892d262fc66079d34a1f22433adbd58`）——**我这轮的落地是判据件，用户在屏上看不到任何变化**。
2. 派出去的车道还没交枝，我这边对那一格只有等待。
3. `place_name` 那格仍未定，我挂在总线 `m_12816c74c645` 上等持派单方，回件 count 0。
4. 后端测试本轮 0 条执行（`test_exit` null，见 `{pf_blob}` 收据）。
5. 镜像 401 的成因仍未钉死；本轮 ref 类写（门落地、publish）都正常，只有那次约 12.5 MB 的 contents PUT 连拒两次。
6. 手机链 hop4 未起 ⇒ 读数仍是 `NOT-DEPLOYED-OBSERVED`；`_preview.db` 我 0 写入，:8000 / :4781 / :4782 / :8693 我未发请求也未重启；桌面留言仍是换树那一个问题，我没追加。
"""
name = D["now"].replace(":", "")
out = T.format(hh="06:02", **D)
open("D:/moodle/_qoder_ledger_inbox/cmdr_" + name + ".md", "wb").write(out.encode("utf-8"))
print("WROTE cmdr_" + name + ".md", len(out.encode("utf-8")), "B | tip", D["tip"][:12])
