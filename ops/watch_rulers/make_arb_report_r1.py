"""Assemble the commander's hourly report for the arbiter window: gate it, then put it on the clipboard.

Nothing is typed by hand into the browser: the text is written to a UTF-8 file, run through the same
Q43 coordinate gate every outbound message passes, and only then loaded into the clipboard with an
explicit encoding, because PowerShell reads a BOM-less .ps1 as ANSI and ChatGPT's composer accepts paste.
"""
import datetime
import hashlib
import io
import json
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cnx-cmdr-arb-report"}


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


import urllib.parse as up
Q = up.quote
TIP = get("/repos/Canshu-King/CityNexus/branches/" + Q("mirror/integration-frontend-apple-pass1", safe=""))["commit"]["sha"]
LEDGER = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=" + Q("commander/control", safe=""))["sha"]
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()

L = [
    "【号令者 494abfd7 → 仲裁 · " + now + "+08 一拍：ORD-0302 已落地并完成一次换代；Q54=①/Q55=① 已照办；请回 Q56】",
    "",
    "一、落地与换代（照你 Q39=① 的单次窗口，未超）。权威尖 `dc964086c9d412573ac19d70b24b30e6c3ee6168` → `" + TIP + "`，落地前一刻重读 tip 才推（单写者、ff-only、三路回读）。手机侧随后 union-first 换代，换完逐条回读：`index-BTzTyrqI.js` 1253398 B、`index-I45CQek8.css` 183897 B、`/v10-sw.js` 2055 B，三条服务端字节与磁盘 sha256 全等、全 200、无 HTML 兜底。部署收据 blob `0ad4409facb716887808ee58f60b10a12975230f`，手机侧回读 blob `370fbb2e541b77050018013e4947b68199d6ce44`（都在 `commander/control:evidence/cmdr-phone-chain-1753/`）。",
    "",
    "二、状态分开写：**ORD-0302 = LANDED + DEPLOYED，未 CLOSED**。B 的 17:53 勘误帖（`issuecomment-5830413057`）我现场复算，三枚坐标全部重算相符（索引 `b45636c110578ad6b4dd8d2d54fe7a9431b2367a` 列 45 枚、独立回读件 `2d7048c27dbe28a8f76a365e192594ea3d2f1317`、收据 `910b78a9587fc96c714b4ab0bc01c70ed777b06c`）；那枚收据里 `cells` " + "12" + " 格的 `derived_result` 现值全为 `null`（另有一枚文档级同名键也是空，共 13 个键 —— 她的 12 格口径是对的，我把容器数进去了）。按 B-1，闭单只差 verifier 的派生。",
    "",
    "三、已开两单把它推完（账本 `## ORDERS`，镜像 blob `" + LEDGER + "`）：",
    "- **ORD-0312**：在已部署那一代重读 null-body 与 X-5 两形（RED/GREEN 双向 + 反件 + 代次绑定逐字节），测量 HJ-P3 `aad2d1f2`，派生红队 `d2305848`。这单的存在理由就是 Q24：B 原读数在 vite dev 那一代，不能携载到部署代。",
    "- **ORD-0313**：D 的 ORD-0308 三格（`B × 尖` ff-only、`A` = `NOT_APPLICABLE_missing_candidate`、`A × B` = `NOT_RUN`）派生归红队，主收据 blob `7a1a5eb7ebf7d8cde93792820b08c7157a48c3af`（12493 B）。我要求她那条 `NOT_APPLICABLE` 不许被升级、`NOT_RUN` 不许当结论用。",
    "",
    "四、刚收的另一件：D 的 0308 目录分类（`issuecomment-5830543183`）。她把 evidence 目录 43 条分成三类并逐件一次独立 GET，其中 11 条是我自己命令的 `--local-dir` 指错扫进来的尺输出。我的裁决：**不删、不改名**——已发布路径冻结这条对我也有效，清理由我来做只会制造新的不可复现。要做的修正在工具侧（下次只指向 `pub` 子目录），我已回给她。",
    "",
    "五、基座变了的影响我已点名处置：两枚未落候选需要 re-parent 重跑自证（B 的 `64d14b205263ec03fd4810b1b0877418495b87b0`、F 的 `fd8eaf3644b66b44c44ce3178a7babac2bf561c0`），与本代产品文件路径重叠为 0，不要求重写内容。F 还欠 ORD-0296 r3 的收据落到 evidence 新路径，落了我就 ff-only 落它。",
    "",
    "六、只有你能或只有用户能的两件事：手机数据面 `:8000` 仍无人监听（本帖组装时 `netstat -ano -p tcp` 现场命中 0 条 LISTENING），所以 M1/M2 之外的\"真行程\"读数今晚拿不到；是否允许我或某条车道用私有拷库起一个具名后端的实例来补这一半，仍在等你或用户的字——我没有自批，也没有让车道自批。",
    "",
    "七、请回一个符号（其余我按现有裁定自己执行，不占你）：",
    "**Q56：ORD-0302 的闭单前置按哪种口径算够？**",
    "① 只在部署代重读 null-body 与 X-5 两形（各含反件）+ 逐格派生，其余格按 Q24 判\"未触及子树\"携载 —— 我推荐这个：本代产品改动只有 `PlanWithAiSheet.tsx` 那两行守卫与它那条 e2e spec（收据 `at_ref` 栏就这两条路径），后端与网络层字节未动，携载是可算的不是猜的；",
    "② 收据 blob `910b78a9587fc96c714b4ab0bc01c70ed777b06c` 里那 12 格全部在部署代重跑一遍才谈 CLOSED —— 更贵，但代次证据最厚，代价是今晚还要多占一次 HJ-P3 的整轮。",
    "",
    "旁：本拍除落地那一跳外 `refs_pushed=0`、`product_files_written=0`、`demo_reset=0`、`_live`/`_preview` 库读写 0、凭据 0 打印。",
    "",
    cl,
]
body = "\n".join(L)
io.open("_arb_msg.txt", "w", encoding="utf-8", newline="\n").write(body)
p = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_arb_msg.txt", "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print((p.stdout or "").strip()[-900:])
if p.returncode:
    print(p.stderr[-400:])
    raise SystemExit("REFUSED by the Q43 gate")
if sum(ord(c) for c in cl) != 765852 or not body.rstrip().endswith(cl):
    raise SystemExit("REFUSED: closing line problem")
print("len", len(body), "chars | codesum", sum(ord(c) for c in body), "sha256", hashlib.sha256(body.encode()).hexdigest()[:12])
if "--clip" in sys.argv:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "$c = Get-Content -Raw -Encoding UTF8 'D:\\moodle\\_qoder_cmdr_ref_20260921\\live_checks\\_arb_msg.txt'; Set-Clipboard -Value $c"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    print("clip set rc", r.returncode, (r.stderr or "")[:200])
    v = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "$s = Get-Clipboard -Raw; $t = 0; foreach ($ch in $s.ToCharArray()) { $t += [int]$ch }; Write-Output ('chars ' + $s.Length + ' codesum ' + $t)"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    got = (v.stdout or "").strip().splitlines()
    print("clip readback:", got[-1] if got else "<empty>")
    want = "chars %d codesum %d" % (len(body), sum(ord(c) for c in body))
    print("expected      :", want)
    print("CLIPBOARD MATCHES THE GATED TEXT" if got and got[-1].strip() == want else "CLIPBOARD MISMATCH - do not paste")
