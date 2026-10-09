import json, io, os, subprocess, datetime
L = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
def run(*a, inp=None):
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)
    if r.returncode: print("ERR", a[-1][:40], r.stderr[:120])
    return r.stdout.strip()
G = ["git", "-C", "D:/moodle/CityNexus"]
D = {}
D["tip"] = run(*G + ["ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1"]).split()[0]
D["lane_r4"] = run(*G + ["rev-parse", "--verify", "refs/remotes/origin/review/2d2d7428-ord0509-landing-advice-day25-r4"])
D["recut"] = run(*G + ["rev-parse", "--verify", "refs/remotes/origin/review/cmdr-a-recut-ord0509-r2"])
D["pf_blob"] = run(*G + ["hash-object", "-w", L + "/_pf_ORD0509.json"])
D["pf_bytes"] = format(os.path.getsize(L + "/_pf_ORD0509.json"), ",")
pf = json.load(io.open(L + "/_pf_ORD0509.json", encoding="utf-8"))
D["files"] = json.dumps((pf.get("file_sets") or {}).get("candidate_only") or [], ensure_ascii=False)[:200]
D["test_exit"] = (pf["gate_run"] or {}).get("test_exit")
D["led_bytes"] = format(os.path.getsize(r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"), ",")
D["now"] = datetime.datetime.now().strftime("%H:%M")
D["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
T = u"""### CMDR {date} {now} · 号令者（实例 A，会话 `6efab655`）· ORD-0509 判据件进线；我自报一处 ref 贴错名（把车道枝头当成了复切片推出去，没重写、改走 -r2）

**现尖**：`{tip}`（我这半小时经门两次 ff 推到位：先是 ORD-0531 的 `6a06a0bb93ffb7e9462b24b611f4ce214ea04f55`，再是这一块下面的 ORD-0509）。账本本地 {led_bytes} B 为我 {now} 现读。

**一、ORD-0509 落地（纯判据件）**
车道 2d2d7428 那块 06:26 入账（`_processed/2d2d7428_0625.md.inserted_062652`），申报枝 `refs/heads/review/2d2d7428-ord0509-landing-advice-day25-r4`。我按规矩两侧对齐后才动手：`ls-remote` 现读 `{lane_r4}`，`git fetch` 后 `git rev-parse refs/remotes/origin/...` 回读同一枚（逐字相等），再确认它与当时尖 `6a06a0bb93ff` 的关系是**未进线**（`merge-base --is-ancestor` 判否）。只读复切成 `{recut}`，复切器报 files 1/1 identical-to-lane-blob；推 `refs/heads/review/cmdr-a-recut-ord0509-r2` 并 `ls-remote` 逐字回读；门 `READY_TO_LAND`、ff=True、ahead=3、behind=0、`product introduced: (none)`；落地后外部回读 `{tip}`，两路一致。收据 `evidence/cmdr-landing-ord0509-0631/preflight_r1.json`，blob `{pf_blob}`，{pf_bytes} B。
`--exposure-arm off` 的具名理由：这一笔相对当时尖的增量只有 `review/` 与 `evidence/` 之下文件，`frontend/src`、`backend/app`、`contracts` 均 0 枚，门自己在 `product introduced` 那格也回 `(none)` ⇒ AST 曝光尺没有可看对象。后端测试：收据 `gate_run.test_exit` 为 {test_exit}，我没有可传 `--tests` 的对象 ⇒ `NOT_EXECUTED_BY_CMDR`。

**二、我自报一处操作错（不改已推的 ref，按新名走）**
我第一次推 `-r1` 时取错了变量：本应推复切片 `{recut}`，结果把**车道自己的枝头** `{lane_r4}` 推成了 `refs/heads/review/cmdr-a-recut-ord0509-r1`。这枚 ref 名字因此名不符实（它指的不是复切片、也没合到当时尖）。我**没有 force、没有重写**它——已发布的线不回头改——改用新名 `refs/heads/review/cmdr-a-recut-ord0509-r2` 指向真正的复切片并由它过门落地。后果核实：那一笔误推对权威线 0 影响（门只读 `-r2`），但下一位若按 `-r1` 这个名字取用会取到未合切的内容，所以我把两枚 40 位都写在这里：`-r1` = `{lane_r4}`（勿用），`-r2` = `{recut}`（已进线）。同类坑我今天第三次踩（前两次：把 `12,587,540 B` 那发的 sha 手敲错过一位、把 `0210` 那行按错锚），共性都是**手敲 40 位**；已把「凡是要往外用的 40 位一律由 `git rev-parse`/`ls-remote` 现读进变量再拼命令」写给自己。

**三、我派出去的那手：枝有了，申报还没有**
车道会话 `45d25bfb-3cb3-43e5-b9cc-edc10faa04a3`（修 hub 枚局）已推出三枚枝：`review/cmdra-hub-enum-copy-r1` = `20eeedd1df07d217985d7e62ba4e1d826f606aa3`，反件枝 `-m1` = `1170e0a7340c26c7082dd5a5024cf5bdd1a1df1a`、`-m2` = `7427f5491e1c7c54fbb987b1f3e603c4cd46829f`（`git ls-remote origin refs/heads/review/cmdra*` 于 06:26 现读）。但收件口里它名下 0 块，所以按「未申报＝未交付」我**没有复切、没有落地、也没有判它合格**。06:3x 我向它发了一次只报事实的敲门（三枚 40 位、验收要件两枚读数件 blob、以及文件名带冒号会变成 0 字节加数据流这个坑）。它交块之后我再走复切与屏上复验。

**没改善的部分**
1. 用户在屏上仍看不见任何变化：这两笔落地产品字节均为 0（门的 `product introduced` 两格都回 `(none)`）。
2. hub 那 27 次 `SYNTHETIC_DEFAULT` 仍在线上（zh 与 en 各 27，件 `ab52516a651fac45176025881dcf16962672c8a9`、`dc56cfcc1892d262fc66079d34a1f22433adbd58`）；车道有枝无申报，我这边推进为 0。
3. 我留下一枚名不符实的 ref（`cmdr-a-recut-ord0509-r1`），没删也没改，只是具名标注勿用——清理归下一位决定。
4. `place_name` 那格仍未定，仍等持派单方读总线 `m_12816c74c645`（回件 count 0）。
5. 后端测试本轮没有任何一条被执行（`{pf_blob}` 与上一笔 `{pf545}` 两枚收据的 `test_exit` 同为 null）。
6. 手机链 hop4 未起 ⇒ 读数仍是私有舞台 `NOT-DEPLOYED-OBSERVED`；`_preview.db` 我 0 写入，:8000 / :4781 / :4782 / :8693 我未发请求也未重启；桌面留言仍是换树那一个问题，我没追加新请求。
"""
name = D["now"].replace(":", "")
out = T.format(pf545="72aa1f5f6028fb1396e97db96d0feaa2e14b7b2c", **D)
open("D:/moodle/_qoder_ledger_inbox/cmdr_" + name + ".md", "wb").write(out.encode("utf-8"))
print("WROTE cmdr_" + name + ".md", len(out.encode("utf-8")), "B")
