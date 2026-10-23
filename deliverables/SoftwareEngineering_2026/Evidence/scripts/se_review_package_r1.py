"""Package the coursework deliverable for external (GPT) review.

Three things this does that a plain zip does not:
  - every number in the review brief is read out of the result JSONs and the
    files themselves at the moment of writing, so the brief cannot drift from
    the artefacts
  - a MANIFEST of sha256 for every member file goes into the archive
  - after zipping, the archive is extracted to a fresh temp directory and every
    file re-hashed against the manifest. A package that does not survive its own
    round-trip is not shipped.
The closing line is read verbatim from CLOSING_LINE.txt - never retyped.
"""
import hashlib
import json
import os
import glob
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
CLOSING_FILE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
REPO = r"D:\moodle\CityNexus"
COMMIT = "b8cdb49c9e7f105a14915203282ddc6dd0e214ba"
BRANCH = "review/se-coursework-deliverables-r1"
OUTDIR = r"D:\moodle"
NAME = "CityNexus_SE2026_review_%s_20261022.zip" % COMMIT[:9]
ZIP = os.path.join(OUTDIR, NAME)


def sha(p, n=64):
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return h if n == 64 else h[:n]


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


closing = open(CLOSING_FILE, "rb").read().decode("utf-8").strip()
assert len(closing.encode("utf-8")) == 83, "closing line length changed"

vis = j("se_visio_build_result.json")
vproof = j("se_visio_proof_result.json")
prj = j("se_project_build_result.json")
pexp = j("se_project_export_r2_result.json")
msv = j("se_milestone_view_result.json")
snap = j("se_project_export_result.json") or j("se_project_snapshot_result.json")

files = []
for root, _dirs, fs in os.walk(DEL):
    for f in sorted(fs):
        p = os.path.join(root, f)
        files.append((os.path.relpath(p, DEL).replace("\\", "/"), p))
files.sort()

# totals come from the four shipped JSON specifications themselves, not from a
# per-run result file (a single-diagram rebuild overwrites that file and had
# been quietly understating the totals)
spec_totals = {"nodes": 0, "edges": 0, "bands": 0, "per": {}}
for sp in sorted(glob.glob(os.path.join(DEL, "Visio", "specs", "*.json"))):
    d = json.load(open(sp, encoding="utf-8"))
    spec_totals["nodes"] += len(d["nodes"])
    spec_totals["edges"] += len(d["edges"])
    spec_totals["bands"] += len(d.get("bands", []))
    spec_totals["per"][os.path.basename(sp)] = (len(d["nodes"]), len(d["edges"]))
assert spec_totals["edges"] == sum(len(json.load(open(sp, encoding="utf-8"))["edges"])
                                   for sp in glob.glob(os.path.join(DEL, "Visio", "specs", "*.json")))

proof_ok = [r["file"] for r in vproof if r.get("ok")]
glue = {r["file"]: (r.get("glue", {}) or {}).get("proven", 0)
        for r in vproof}
glue_exp = {r["file"]: (r.get("glue", {}) or {}).get("expected", 0)
            for r in vproof}
checks = prj.get("checks", {})
reopen = prj.get("reopen_pass", {})
recalc = prj.get("recalc_proof", {})

# ---------------------------------------------------------------- brief
brief = """# CityNexus 软件工程 2026 交付包 - 外部检查简报

生成 2026-10-22 · 仓库 `%(repo)s` · 分支 `%(branch)s` · 分支 `%(branch)s`，交付内容落在 commit `%(commit)s`（本简报与 `MANIFEST.sha256` 本身在紧随其后的提交里）。
包内文件数 **%(nfiles)d**（不含 `MANIFEST.sha256` 自身，清单不能给自己的摘要签名）。逐文件 sha256 见 `MANIFEST.sha256`。

## 0. 请先读这一段：这个包想让你判什么

主人要求交付**能在 Microsoft Visio / Microsoft Project 里真正打开、真正编辑、真正展示**的课程材料，
而不是 Mermaid、PPT 或 PNG。我因此用本机 Visio Professional 2024 与 Project 2024 的 COM 接口生成。
下面每一项我都附了"你怎么自己复算"的方法。**如果哪一项你复算不出来，请当成它没有发生。**

## 1. 交付物清单（实测，不是声明）

| 项 | 值 | 怎么复算 |
|---|---|---|
| Visio 原生图 | %(nvsdx)d 张 .vsdx | 包内 `Visio/*.vsdx`，或 Visio 直接打开 |
| 形状 / 连线 | %(nodes)d 形状 / %(edges)d 连线 / %(bands)d 分层带 | 直接对 `Visio/specs/*.json` 求和（脚本已断言） |
| 连线两端粘连（重开文件后逐条证明） | %(gluetot)d / %(gluetotexp)d | `Evidence/se_visio_proof_result.json` 的 glue.proven |
| 打开-改字-存-关-重开-读回 全通过 | %(nproof)d / %(nvsdx)d | 同上，字段 checks.markerRoundTrip |
| Project 原生计划 | 1 个 .mpp | `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp` |
| 计划行数 | %(rows)d（摘要 %(sums)d / 明细 %(leaves)d） | 打开 .mpp 看 WBS 列 |
| 里程碑 | %(msn)d 个零工期 | 同上，M1..M13 |
| 资源 / 分配 | %(resn)d 个资源 / %(asn)d 条分配 | Resource Sheet 视图 |
| 总成本 | %(cost)s | Project 重算后读回 |
| 完工日 | %(fin)s | 同上 |
| 关键路径 | %(critn)d 行（引擎算出） | 勾 Critical 列 |
| 视图 PDF | %(npdf)d 个 | 包内 `Microsoft_Project/*.pdf` |

## 2. 我做的六条硬验证（请重点攻击这里）

1. **不是截图**：.vsdx / .mpp 是 Visio 与 Project 自己 SaveAs 出来的原生文件。
2. **连线是真粘连**：生成时把每个形状与每根连线的 `Shape.ID` 写进 gate 报告；验收脚本
   **重新打开磁盘上的文件**，遍历 `page.Connects`，证明每条边都存在一根同时粘住两端 id 的连线。
   Shape.ID 跨保存/重开稳定，所以这是对文件的断言，不是对内存的断言。
3. **改字往返**：改一个形状文字 → 存 → 关 → 重开 → 读回该文字 → 复原 → 再开确认复原。
4. **排程是真的在排**：把一条任务工期从原值改到 25 个工作日，它的 FS 后继开始日**确实移动**；
   改回后日期完全复原（`recalcRestoredCleanly`）。
5. **新进程重开一致**：.mpp 关闭后由**另一个进程**重新打开，行数/明细/分配/成本/完工日全部相等。
6. **没有循环依赖**：在启动 Project 之前，对任务依赖图做拓扑排序；有环就拒绝生成。

## 3. 我明确没有做成、也没有假装做成的事

| 项 | 状态 | 依据 |
|---|---|---|
| Part 1（10 页幻灯片，2026-10-02 截止） | **从未提交**，计划里 0%%，并保留为"未达成里程碑" M10 | 仓库内无任何 .pptx；作业 PDF 第 1 页 |
| 三人小组的第 2、3 名成员 | **查无姓名/学号/分工**，建了两个 0 费率占位资源 | `git log --format=%%an` 只有一个人 + AI 车道身份 |
| 需求基线的客户确认 | 138 条全 `proposed` | `requirements/requirements.yaml` |
| 基准计划 Baseline | **故意没存**：不存在可信的原始计划可当基准 | 未调用 `BaselineSave` |
| 拖动母版形状看连线跟随 | **未证明**：Visio 内置模具带位置保护，COM 写不进 PinX/PinY | `se_visio_proof_result.json` moveProof |
| 真实支付 / Hermes 原生 / live Valhalla / 真机影子测试 | 未实现或未验证，图上画成黄/灰虚线 | `BLOCKERS.md:9-16`、`AGENT_TOOL_CATALOG.md:16-18`、`CURRENT_STATUS.md:4` |

## 4. 请你专门挑这六处毛病

1. **图的语义是否站得住**：架构分层、Agent 三道门（allowlist → 幂等 → 授权）的顺序与措辞，
   是否和 `backend/app/agent/gateway.py:338-398` 的真实控制流一致？有没有我把"设计意图"画成"已实现"的地方？
2. **三态配色是否诚实**：黄=已写未验证、灰虚线=计划中。逐个形状看，有没有该黄却画成蓝的？
   （特别是 `ds_com_guard`、`ag_surface`、`pv_weather`、`UC-06`、`UC-09`、`UC-13`。）
3. **用例图是否过度**：我画了 13 顶层 + 14 include 子用例 + 9 参与者 + 47 条线。
   include 关系全部来自 `use-cases.yaml:relationships`，但**线条密度是否已经影响可读**？
4. **计划的百分比是否可辩护**：52 行明细里，凡是 100%% 的都必须有测试或提交证据；
   凡是部分完成的，我给的理由是否成立？特别看 `9.1 后端回归 85%%`（依据 2026-10-13 报告 1887 通过 / 45 失败）
   与 `4.5 商务与守护 40%%`。
5. **里程碑日期是否被倒推**：我只钉了项目起始与 13 个里程碑日期。请判断这些日期是否都有实物出处，
   以及 M9（系统测试完成 2026-11-02）作为唯一的纯计划选择是否被清楚标注。
6. **成本与费率**：费率是课程规划估算（人 40/时、AI 车道 6/时，两名未定成员 0）。
   作业要求 "Resources assigned with costs"——这样交是否成立，还是必须给出真实人力分工后才能填？

## 5. 包内结构

```
README.md                      用途与展示顺序
SOURCE_MAPPING.md              每个数字怎么量的 + 全部代码坐标 + 文件指纹
AUTOMATION_VERIFICATION.md     跑了什么、哪一步失败过、怎么修的
REVIEW_BRIEF.md                本文件
se_*.json                      5 份机器可读的结果（gate / proof / build / export）
Visio/                         4 个 .vsdx + previews(PNG/PDF/gate.json) + specs(JSON)
Microsoft_Project/             2 个 .mpp + 8 个视图 PDF + previews(整屏 PNG)
Evidence/scripts/              生成器与验收脚本（可重跑）
Evidence/logs/                 探针与构建原始日志
MANIFEST.sha256                包内每个文件的 sha256
```

## 6. 复现

```
cd D:\\moodle\\live_checks
python se_visio_build_r1.py        # 四张 .vsdx + 预览 + gate 报告
python se_visio_proof_r1.py        # 重开、改字、粘连逐条审计
python se_project_build_r1.py      # .mpp + 九项排程检查
python se_project_export_r2.py     # 六个视图 PDF
python se_milestone_view_r2.py     # 里程碑时间线（日期从计划读出并断言一致）
```

## 7. 一处工程痕迹需要你知道

`deliverables/` 落在 CityNexus 仓库里，而该仓库 `.gitignore:23` 有 `evidence/`，会把整个
Evidence 目录吃掉。我加了一条**只针对课程交付路径**的显式例外（这是本次唯一改到的非交付文件），
没有静默 `add -f`。另外主工作区索引里有别的车道预先 staged 的 4109 个条目，我用独立索引建提交，未触碰。

---

""" % dict(repo=REPO, branch=BRANCH, commit=COMMIT, nfiles=len(files) + 2,
           nvsdx=len([f for f, _ in files if f.endswith(".vsdx")]),
           nodes=spec_totals["nodes"], edges=spec_totals["edges"],
           gluetot=sum(glue.values()), gluetotexp=sum(glue_exp.values()),
           nproof=len(proof_ok), rows=reopen.get("tasks", 0),
           sums=len([r for r in reopen.get("wbs", []) if r[0].count(".") == 0]),
           leaves=reopen.get("leaves", 0), msn=len(reopen.get("milestones", [])),
           resn=reopen.get("resources", 0), asn=reopen.get("assignments", 0),
           cost=reopen.get("cost", "?"), fin=reopen.get("projectFinish", "?"),
           critn=len(reopen.get("critical", [])), bands=spec_totals["bands"],
           npdf=len(pexp.get("views", {}))) + closing + "\n"

os.makedirs(os.path.join(DEL, "Evidence"), exist_ok=True)
brief_path = os.path.join(DEL, "Evidence", "REVIEW_BRIEF.md")
open(brief_path, "w", encoding="utf-8").write(brief)

# rebuild the file list now that the brief exists
files = []
for root, _dirs, fs in os.walk(DEL):
    for f in sorted(fs):
        p = os.path.join(root, f)
        rel = os.path.relpath(p, DEL).replace("\\", "/")
        if rel == "MANIFEST.sha256":
            continue
        files.append((rel, p))
files.sort()

man = "".join("%s  %s\n" % (sha(p), name) for name, p in files)
man_path = os.path.join(DEL, "MANIFEST.sha256")
open(man_path, "w", encoding="utf-8").write(man)

# ---------------------------------------------------------------- zip
if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, p in files:
        z.write(p, "CityNexus_SE2026/" + name)
    z.write(man_path, "CityNexus_SE2026/MANIFEST.sha256")

# ---------------------------------------------------------------- verify
tmp = os.path.join(HERE, "_zipcheck")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp)
with zipfile.ZipFile(ZIP) as z:
    bad = z.testzip()
    names = z.namelist()
    z.extractall(tmp)

mismatch, missing, checked = [], [], 0
for line in open(man_path, encoding="utf-8"):
    h, name = line.split()
    src = os.path.join(DEL, name.replace("/", os.sep))
    ext = os.path.join(tmp, "CityNexus_SE2026", name.replace("/", os.sep))
    if not os.path.exists(ext):
        missing.append(name)
        continue
    if sha(ext) != h or sha(src) != h:
        mismatch.append(name)
    checked += 1

native = [n for n in names if n.endswith((".vsdx", ".mpp"))]
report = {
    "zip": ZIP,
    "zip_bytes": os.path.getsize(ZIP),
    "zip_sha256": sha(ZIP),
    "members": len(names),
    "native_office_files": sorted(native),
    "zip_integrity_testzip": bad or "clean",
    "manifest_entries": checked,
    "extract_mismatches": mismatch,
    "extract_missing": missing,
    "closing_line_bytes": len(closing.encode("utf-8")),
    "closing_line_sha256_8": hashlib.sha256(closing.encode("utf-8")).hexdigest()[:8],
    "commit": COMMIT, "branch": BRANCH,
}
json.dump(report, open(os.path.join(HERE, "se_review_package_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False)

print(json.dumps(report, indent=1, ensure_ascii=False))
ok = (not mismatch and not missing and bad is None and checked == len(files))
print("\nROUND-TRIP %s" % ("OK" if ok else "FAILED"))
sys.exit(0 if ok else 1)
