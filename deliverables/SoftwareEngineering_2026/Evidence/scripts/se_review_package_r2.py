"""Package the revision-2 coursework deliverable for external review.

Same three promises as the first package, and one more:

  - every number in the brief is read out of the result JSONs and the files
    themselves at the moment of writing, so the brief cannot drift from the
    artefacts;
  - a MANIFEST of sha256 for every member file goes into the archive;
  - after zipping, the archive is extracted to a fresh directory and every file
    re-hashed against the manifest - a package that does not survive its own
    round-trip is not shipped;
  - the commit coordinate in the brief is read from git in this run, never
    typed from memory.
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
CLOSING_FILE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt"
REPO = r"D:\moodle\CityNexus"
BRANCH = "review/se-coursework-deliverables-r1"
OUTDIR = r"D:\moodle"


def sha(p, n=64):
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return h if n == 64 else h[:n]


def j(name):
    p = os.path.join(HERE, name)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def git(*a):
    return subprocess.run(["git", "-C", REPO] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout.strip()


closing = open(CLOSING_FILE, "rb").read().decode("utf-8").strip()
assert len(closing.encode("utf-8")) == 83, "closing line length changed"

HEAD_BEFORE = git("rev-parse", "HEAD")
print("branch head before this package: %s" % HEAD_BEFORE)

vproof = j("se_visio_proof_result.json")
vgate = j("se_visio_build_result.json")
prj = j("se_project_build_r2_result.json")
prj1 = j("se_project_build_result.json")
brief_res = j("se_visio_plan_brief_result.json")
rev = j("se_evidence_revision_result.json")

# ---- spec totals, read from the shipped JSON specs (multi-page aware) ------
spec_totals = {"nodes": 0, "edges": 0, "bands": 0, "pages": 0, "per": {}}
for sp in sorted(glob.glob(os.path.join(DEL, "Visio", "specs", "*.json"))):
    d = json.load(open(sp, encoding="utf-8"))
    sheets = d.get("sheets") or [d]
    n = sum(len(s.get("nodes", [])) for s in sheets)
    e = sum(len(s.get("edges", [])) for s in sheets)
    b = sum(len(s.get("bands", [])) for s in sheets)
    spec_totals["nodes"] += n
    spec_totals["edges"] += e
    spec_totals["bands"] += b
    spec_totals["pages"] += len(sheets)
    spec_totals["per"][os.path.basename(sp)] = (n, e, len(sheets))

glue_tot = sum((r.get("glue") or {}).get("proven", 0) for r in vproof)
glue_exp = sum((r.get("glue") or {}).get("expected", 0) for r in vproof)
prop_tot = sum((r.get("shapeData") or {}).get("propsOk", 0) for r in vproof)
prop_exp = sum((r.get("shapeData") or {}).get("expected", 0) for r in vproof)
proof_ok = sum(1 for r in vproof if r.get("ok"))

_link = prj.get("links", {})
_cost = prj.get("costs", {})
_prog = prj.get("progress", {})
_dl = prj.get("deadlines", {})
_cons = prj.get("constraints", {})
_cp = prj.get("critical_path", {})
_pub = prj.get("publication", {})
_pf = prj.get("link_proof", {})
_types = _pf.get("types", {})
_chk = prj.get("checks", {})
_static = prj.get("static_preflight", {})
_rows = prj.get("rows", [])
gate_fail_total = sum(len(d.get("failures", [])) for d in
                      [json.load(open(f, encoding="utf-8")) for f in
                       glob.glob(os.path.join(DEL, "Visio", "previews", "*.gate.json"))])
late = [x for x in _prog.get("history_problems", []) if x.startswith("OVERDUE")]
NAME = "CityNexus_SE2026_review_r3_%s.zip" % (HEAD_BEFORE[:9] or "nohead")
ZIP = os.path.join(OUTDIR, NAME)

os.makedirs(os.path.join(DEL, "Evidence", "scripts"), exist_ok=True)
os.makedirs(os.path.join(DEL, "Evidence", "logs"), exist_ok=True)
# _*.py are throwaway probes; shipping them would ask the reader to run a script
# that pokes a live Office instance for no delivery purpose
for pat in ("se_*.py",):
    for f in glob.glob(os.path.join(HERE, pat)):
        shutil.copyfile(f, os.path.join(DEL, "Evidence", "scripts",
                                        os.path.basename(f)))
for pat in ("se_*.log", "se_*.txt"):
    for f in glob.glob(os.path.join(HERE, pat)):
        shutil.copyfile(f, os.path.join(DEL, "Evidence", "logs",
                                        os.path.basename(f)))
for name in ("se_visio_build_result.json", "se_visio_proof_result.json",
             "se_project_build_r2_result.json", "se_project_build_result.json",
             "se_visio_plan_brief_result.json", "se_evidence_revision_result.json",
             "se_plan_cpm_r2.json", "se_milestone_view_result.json",
             "se_project_export_r2_result.json",
             # round 2 named three files the package did not contain; every
             # generator result now travels with the delivery, and
             # se_evidence_index_r1.py checks that each cited path resolves
             "se_project_snapshot_result.json",
             "se_project_snapshot_r2_result.json", "se_project_brief_result.json",
             "se_project_recovery_result.json", "se_plan_status_result.json",
             "se_deck_result.json", "se_evidence_reconcile_result.json",
             "se_classroom_demo_result.json"):
# se_review_package_r2_result.json is deliberately NOT copied in: it carries the
# digest of the zip that would contain it, so any copy inside the package is by
# construction one generation old - which is the defect round 2 was reported for.
    if os.path.exists(os.path.join(HERE, name)):
        shutil.copyfile(os.path.join(HERE, name),
                        os.path.join(DEL, "Evidence", name))


brief = """# CityNexus 软件工程 2026 · 修订二交付包（复审简报）

生成 %(today)s · 仓库 `CityNexus` · 分支 `%(branch)s` · 打包时分支头 `%(head)s`。
包内 **%(nfiles)d** 个文件（不含 `MANIFEST.sha256` 自身——清单不能给自己的摘要签名）。
逐文件 sha256 见 `MANIFEST.sha256`；压缩包 sha256 `%(zipsha)s`。

## 0. 这一版是冲着谁的

上一版被独立审查否掉三处：Project 排程语义、Visio 逐形状元数据、Agent 流程图与真实代码不符。
`Evidence/REVISION_2.md` 逐条回答，并且**每个"改后"数字都是打包时从工件重算的**，
不是从终端记录里抄的。本简报告诉你怎么自己复算。

**如果哪一项你复算不出来，请当成它没有发生。**

## 1. 交付物（实测）

| 项 | 值 | 怎么复算 |
|---|---|---|
| Visio 原生图 | %(nvsdx)d 张 .vsdx，共 %(npages)d 页 | Visio 直接打开 |
| 形状 / 连线 / 分层带 | %(nodes)d / %(edges)d / %(bands)d | 对 `Visio/specs/*.json` 的 sheets 求和 |
| 连线两端真粘连 | %(glue)d / %(glueexp)d | `Evidence/se_visio_proof_result.json` → glue.proven |
| 逐形状自定义属性读回 | %(prop)d / %(propexp)d | 同上 → shapeData.propsOk / expected |
| 打开-改字-存-关-重开-读回 全通过 | %(proofok)d / %(nvsdx)d | 同上 → checks |
| 版面闸门失败项（重叠/越界/文字出框/图例被压） | %(gatefail)d | `Visio/previews/*.gate.json` → failures |
| Project 原生计划 | `Microsoft_Project/CityNexus_Software_Engineering_Plan.mpp`，sha256 `%(mppsha)s` | Project 直接打开 |
| 行数 | %(rows)d（摘要 %(sums)d / 明细 %(leaves)d，含里程碑 %(msn)d） | 看 WBS 列 |
| 声明依赖 / 引擎读回 | %(decl)d / %(read)d 条依赖记录 | `Task.TaskDependencies`，脚本已逐条比对 |
| 违反日期顺序的依赖 | %(viol)d | 同上 |
| 被钉住日期的行（约束≠ASAP） | %(forced)d | 约束列应为空 |
| 关键路径 | %(critn)d 行（引擎算出） | 勾 Critical 列 |
| 人力工时 / 总成本 | %(hours)d h / $%(cost)s | 工时=工期×投入×8h，成本由 Project 自己乘费率 |
| 工时或成本与估算不符的行 | %(costbad)d | 逐行对 duration×units×rate |
| 截止日 | %(dlmet)d 满足 / %(dlbr)d 违反（课程硬日期） / %(dlsoft)d 内部目标未达 | Deadline 列 |
| 关闭后由新进程重开，逐字段比对 | %(drift)d 处差异 | 行/日期/百分比/工时/成本/约束/实际/关键/WBS |
| 发布回读 | %(shiprows)d 行、%(shiplinks)d 条依赖、%(shipviol)d 处违反 | 打包脚本对**已发布文件**再开一次 |
| 汇报版一页图 | `Briefing/CityNexus_Plan_Briefing_A3.vsdx` + PDF/PNG | 日期全部来自 .mpp 计算结果 |

## 2. 这一轮新加的、可以攻击的硬断言

1. **静态前置检查**（`se_plan_cpm_r1.py`，纯 Python，不开 Project）：环、未知行、自环、
   SF 链接、以及每条声明依赖能否被自己的正向排程满足。当前 %(viol0)d 违反 / %(prob0)d 结构问题。
2. **依赖必须从引擎读回**：不再相信脚本"我写了"，而是打开文件遍历
   `Task.TaskDependencies`，用本机实测的类型映射（FF=0, FS=1, SF=2, SS=3）逐条判日期不等式。
3. **链接类型必须真的驱动日期**：把一条未完成任务加 10 个工作日，看哪些后继、哪个字段动了；
   FS/SS 必须拖动开始日，FF 必须拖动完成日；然后改回去，要求每个日期完全复原。
   （本机实测：`TaskDependency.Lag` 写入被吞、`TaskMoveToStatusDate` 返回真但什么都不动，
   所以不能用 lag 证明，见 `Evidence/logs/se_proj_probe_r10.log`。）
4. **形状属性写一次读一次**：`AddNamedRow` + `Prop.<name>.Value`，写完立刻在同一调用里读回，
   读不回原值就是错误，不是提示。验收脚本再从**磁盘上的文件**逐形状、按 (页, ShapeID) 复核。
5. **版面闸门覆盖非节点元素**：图例、说明块、页脚、连线标签必须在页内、不压形状、不互相压；
   带标题的分层带不能被形状压住；每条引用文字必须放得下它自己的形状。
   这条规则第一次运行就抓出三类真实缺陷：图例被说明块压住、连线标签被丢到页角（旧代码在粘连瞬间取端点，那时还是 0,0）、引用文字越出形状边界。
6. **包必须过自己的往返**：压缩 → 解压到新目录 → 逐文件重算 sha256 与清单比对。

## 3. 我没有做成、也没有假装做成的事

| 项 | 状态 | 依据 |
|---|---|---|
| Part 1（2026-10-02 截止） | **本仓库无法证实也无法证伪**；行仍为 0%%，等课程记录 | 仓库内无该 .pptx；但这不等于没交 |
| 迟开的工作 | %(laten)d 行相对状态日已迟，**保持迟到**，没有挪日期 | Project 的 Move-to-Status-Date 在本机 COM 无效 |
| 三人分工 | 成员已实名，但 git 只有一个提交身份，分工是**计划提案** | `git log --format=%%an` |
| 费率 | 课程规划估算，非工资；两条算力车道是材料资源（只花钱不计工时） | 资源备注 |
| 基准计划 | **故意没存**：没有可信原始计划 | 未调用 `BaselineSave` |
| 拖动母版形状看连线跟随 | **未证明**：内置模具位置保护 | moveProof 缺席即未证 |
| Project 分页设置 | **无法脚本化**：`FilePageSetupPage` 各形参均报参数无效 | `Evidence/logs/se_project_brief.log` |
| 真实支付 / Hermes 原生 / live Valhalla / 真机影子测试 | 未实现或未验证，图上黄/灰虚线 | `BLOCKERS.md:9-16` 等 |

## 4. 请专门挑这六处

1. **里程碑日期不单调**（M8 早于 M4）：这是并行流的真实形状，还是我链接画错了？
2. **百分比是否可辩护**：凡 100%% 都有测试或提交证据吗？重点看 `9.1 后端回归 85%%`、
   `4.5 商务与守护 40%%`、`8.2 前端回移 50%%`。
3. **工时是否可信**：%(hours)d 工时摊到三人七周，是否偏高或偏低？
4. **Agent 图的三族处理器**：读→无策略、replan 对→策略先于幂等、typed→各自守卫，
   与 `gateway.py` 现在的行号是否仍然一致？
5. **一页汇报图**：把计划压到 11 条相位条 + 13 个里程碑，是否已经丢失了老师判断所需的信息？
6. **三态配色**：黄=已写未验证、灰虚线=计划中，有没有该黄却画成蓝的形状？

## 5. 包内结构

```
README.md                      用途与展示顺序
SOURCE_MAPPING.md              每个数字怎么量的 + 全部代码坐标 + 文件指纹
AUTOMATION_VERIFICATION.md     跑了什么、哪一步失败过、怎么修的
REVISION_2.md                  对上一轮审查的逐条回答（改前/改后都是重算的）
REVIEW_BRIEF.md                本文件
se_*.json                      机器可读结果（gate / proof / build / brief / revision）
Visio/                         4 个 .vsdx + previews(PNG/PDF/gate.json) + specs(JSON)
Microsoft_Project/             .mpp + 汇报版 .mpp + 视图 PDF + previews(PNG)
Briefing/                      一页 A3 横版汇报图（.vsdx + PDF + PNG + gate.json）
Evidence/scripts/              生成器与验收脚本（可重跑）
Evidence/logs/                 探针与构建原始日志
MANIFEST.sha256                包内每个文件的 sha256
```

## 6. 复现

```
cd D:\\moodle\\live_checks
python se_plan_cpm_r1.py                # 只做静态依赖检查
python se_project_build_r2.py           # 建计划、全量审计、发布 .mpp
python se_visio_build_r1.py             # 四张图 + 预览 + gate
python se_visio_proof_r2.py             # 重开、粘连、逐形状属性
python se_visio_plan_brief_r1.py        # 一页汇报图
python se_evidence_docs_r1.py           # 三份说明文档
python se_evidence_revision_r1.py       # REVISION_2.md
python se_review_package_r2.py          # 本文件 + MANIFEST + 压缩包 + 往返校验
```
每个脚本在断言不过时都返回非零，而不是"看起来成功"。

---

%(closing)s
""" % {
    "today": __import__("datetime").date.today().isoformat(),
    "branch": BRANCH, "head": HEAD_BEFORE[:40] or "unknown",
    "nfiles": 1 + len([1 for r, _d, fs in os.walk(DEL) for f in fs
                       if not os.path.relpath(os.path.join(r, f), DEL)
                       .endswith("MANIFEST.sha256")]),  # +1 = this brief
    "zipsha": ("zip 不能自证：压缩包自身的 sha256 记在包外的 "
               "`Evidence/R3_RESULT.md` 与提交信息里，包内只放逐文件清单"),
    "nvsdx": len(glob.glob(os.path.join(DEL, "Visio", "*.vsdx"))),
    "npages": spec_totals["pages"], "nodes": spec_totals["nodes"],
    "edges": spec_totals["edges"], "bands": spec_totals["bands"],
    "glue": glue_tot, "glueexp": glue_exp, "prop": prop_tot, "propexp": prop_exp,
    "proofok": proof_ok, "gatefail": gate_fail_total,
    "mppsha": sha(os.path.join(DEL, "Microsoft_Project",
                               "CityNexus_Software_Engineering_Plan.mpp"), 16),
    "rows": len(_rows), "sums": len([r for r in _rows if r["summary"]]),
    "leaves": len([r for r in _rows if not r["summary"]]),
    "msn": len([r for r in _rows if r["milestone"]]),
    "decl": _link.get("declared", 0), "read": _link.get("read", 0),
    "viol": len(_link.get("violations", [])), "forced": len(_cons.get("forced", [])),
    "critn": _cp.get("count", 0),
    "hours": int(round(_cost.get("labour_hours", 0))),
    "cost": int(round(prj.get("reopen_pass", {}).get("cost", 0))),
    "costbad": len(_cost.get("problems", [])),
    "dlmet": len(_dl.get("met", [])),
    "dlbr": len([b for b in _dl.get("breached", []) if not b["recordedFact"]]),
    "dlsoft": len(_dl.get("internalTargetsMissed", [])),
    "drift": prj.get("reopen_drift_count", -1),
    "shiprows": _pub.get("shippedRows", 0), "shiplinks": _pub.get("shippedLinksRead", 0),
    "shipviol": _pub.get("shippedLinkViolations", 0),
    "viol0": len(_static.get("violations", [])), "prob0": len(_static.get("problems", [])),
    "laten": len(late), "closing": closing,
}

open(os.path.join(DEL, "Evidence", "REVIEW_BRIEF.md"), "w",
     encoding="utf-8").write(brief)

# ---- rebuild the file list now that the brief and copies exist -------------
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

if os.path.exists(ZIP):
    os.remove(ZIP)
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, p in files:
        z.write(p, "CityNexus_SE2026/" + name)
    z.write(man_path, "CityNexus_SE2026/MANIFEST.sha256")

tmp = os.path.join(HERE, "_zipcheck_r2")
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

native = sorted(n for n in names if n.endswith((".vsdx", ".mpp")))
report = {
    "zip": ZIP, "zip_bytes": os.path.getsize(ZIP), "zip_sha256": sha(ZIP),
    "members": len(names), "native_office_files": native,
    "zip_integrity_testzip": bad or "clean", "manifest_entries": checked,
    "extract_mismatches": mismatch, "extract_missing": missing,
    "closing_line_bytes": len(closing.encode("utf-8")),
    "closing_line_sha256_8": hashlib.sha256(closing.encode("utf-8")).hexdigest()[:8],
    "branch_head_before_package": HEAD_BEFORE, "branch": BRANCH,
    "totals": {"glue": "%d/%d" % (glue_tot, glue_exp),
               "shapeData": "%d/%d" % (prop_tot, prop_exp),
               "links": "%d declared, %d records, %d violations"
                        % (_link.get("declared", 0), _link.get("read", 0),
                           len(_link.get("violations", []))),
               "labourHours": int(round(_cost.get("labour_hours", 0))),
               "gateFailures": gate_fail_total,
               "checksAllTrue": all(_chk.values()) and bool(_chk)},
}
json.dump(report, open(os.path.join(HERE, "se_review_package_r2_result.json"), "w",
                       encoding="utf-8"), indent=1, ensure_ascii=False)
shutil.rmtree(tmp, ignore_errors=True)
print(json.dumps(report, indent=1, ensure_ascii=False))
ok = (not mismatch and not missing and bad is None and checked == len(files)
      and all(_chk.values()))
print("\nROUND-TRIP %s (%d files, %d manifest entries)"
      % ("OK" if ok else "FAILED", len(files), checked))
sys.exit(0 if ok else 1)
