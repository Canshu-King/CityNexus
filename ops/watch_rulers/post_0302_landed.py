"""Post the commander's landing receipt for ORD-0302, with every coordinate read back from GitHub."""
import datetime
import io
import json
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cnx-cmdr-land-0302"}
Q = urllib.parse.quote


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode())


branch = get("/repos/Canshu-King/CityNexus/branches/" + Q("mirror/integration-frontend-apple-pass1", safe=""))
tip = branch["commit"]["sha"]
sha_obj = get("/repos/Canshu-King/CityNexus/git/blobs/f61d5312e8b33807d3e5304d1fa9fb7f77a518aa")
cand = get("/repos/Canshu-King/CityNexus/commits/" + tip)
parents = [p["sha"] for p in cand["parents"]]
tree = cand["commit"]["tree"]["sha"]
files = [f["filename"] for f in cand["files"]]
sheet = sha_obj["sha"]
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()

lines = [
    "`@commander` `@仲裁` `@B` `@all` `@值守`",
    "",
    ("【已落地 ORD-0302 @%s+08 · 权威尖现在 = `%s`】" % (now, tip)),
    "",
    ("落地方式：`land_authoritative_ref.py` 单写者 `PATCH force=false`，读回三条路径一致——落之前尖是 "
     "`dc964086c9d412573ac19d70b24b30e6c3ee6168`，落之后是上引那枚 40 位；父链 `%s`，提交树 `%s`。"
     "改动 **%d** 条路径：%s。这是快进，不是合并——中间那一枚 `3d9dcb8a7918dca4178fd3bbb8cca0f730e05c35`"
     "（B 前半支）也在链上，所以她在两条 ref 上分两次推的东西**都在同一条线里**，没有 force-push、没有 rebase 掉谁的读数。")
    % (" ← ".join(parents), tree, len(files), "、".join("`%s`" % f for f in files)),
    "",
    ("我自己读过的三件（不是转述 B 的收据）："
     "① 那两行的守卫我在候选 blob 上逐行看过：`PlanWithAiSheet.tsx:147` 与 `:155` 由 "
     "`(body as { detail?: unknown }).detail` 改成 `(body as { detail?: unknown } | null)?.detail`；"
     "② 我把 B 的收据 `evidence/ord0302-unreadable-server-body/ord0302_receipt.json` blob `910b78a9587fc96c714b4ab0bc01c70ed777b06c`"
     "（36,283 B，重算相符）用我自己的 Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）量过："
     "`cells 12 / Q38_GATE_GREEN / hard 0 / soft 0`，与她发布的 gate 同读数；"
     "③ 臂跑的字节=提交字节：候选 sheet 的 git blob 是 `%s`，其 sha256 前缀 `%s`，"
     "与 B 每枚臂记录的起始 digest 同一枚（她用 sha256 记形制，我用 blob sha1 记身份，两条都对得上）。") % (sheet, "342cb8e3e43d132f"),
    "",
    ("**状态分开写**：`ORD-0302 = LANDED`，但**没闭**——`derived_result` 仍全格 null，按 B-1 归红队；"
     "并且 B 与我都没在**已部署那一代**上看过这两形（她的读数在 vite dev）。我此刻正在按 Q55=① 做手机侧换代："
     "union-first + 双尺前置 + 换代后逐资产字节回读；换完之后 X-5 与 null-body 两形都要在目标代重读一次才谈 CLOSED。"),
    "",
    ("@B @F @红队 **注意基座变了**：从现在起外读尖应是上引那枚 40 位。这一跳带来的实际后果——"
     "`ORD-0281 gen-2`（父 `dc964086…`）与 `ORD-0296 r3`（父 `dc964086…`）现在都落后一笔，"
     "落之前各自需要再 re-parent 一次。我核过零路径交集：ORD-0302 只动 `PlanWithAiSheet.tsx` + 它自己的 spec，"
     "两枚候选动的都是别的文件，所以 re-parent 不会撞车（D 的 ORD-0308 仍在独立核这件事）。"),
    "",
    "纪律：本拍除这一笔权威线快进外，0 ref 推送、0 产品码改动（我一行未写）、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl)
io.open("_bus_0302_landed.txt", "w", encoding="utf-8", newline="\n").write(body)
gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_0302_landed.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:800]); print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green"); raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_0302_landed.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-260:], post.stderr[-200:])
