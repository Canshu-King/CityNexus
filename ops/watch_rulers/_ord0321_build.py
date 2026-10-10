"""Build _ord0321_reachability_r1.json: for each of the 16 upstream_prose cells from the Q64 sweep,
judge only one thing - can a traveller on a phone actually reach this render.

Frontend quotes are read by line number from the tip tree exported with `git archive`; backend quotes are
read from `git show <tip>:backend/app/main.py`. Nothing here was observed on a device: the phone surface's
`:8000` was NOT AVAILABLE this session, no `vite build` ran, and `frontend/node_modules` (a junction) was
never entered. Every cell therefore carries live_observed=false, and UNKNOWN names the step that is missing.
"""
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
from _sweep_build import TIP  # noqa: E402

ROOT = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
TREE = os.path.join(ROOT, "_sweep_scratch", "tree", "frontend", "src")
BACKEND = os.path.join(ROOT, "_sweep_scratch", "backend_main.py")
R3 = "44e062e6ce9c7b5d97d78e09e432072da102292c"
R2 = "608016f6a538097041554b76cfe3e9a4192f299c"


def fe(rel, n):
    p = os.path.join(TREE, rel.replace("frontend/src/", ""))
    lines = io.open(p, encoding="utf-8", errors="replace").read().splitlines()
    return lines[n - 1].strip()


def be(n):
    lines = io.open(BACKEND, encoding="utf-8", errors="replace").read().splitlines()
    return lines[n - 1].strip()


# (cell_file, cell_line, verdict, phone_path, endpoint, prose_source[(kind,line)], render_sink[(kind,line)], missing)
CELLS = [
 ("frontend/src/app/V8Experience.tsx", 1028, "REACHABLE_ON_PHONE",
  "启动后进设置向导 → 填一张单 → 服务器按字段拒",
  "POST /api/v1/journeys",
  [("backend", 539), ("backend", 555), ("backend", 640)],
  [("frontend", 1030), ("frontend", 169), ("frontend", 1562)], ""),
 ("frontend/src/components/ProductErrorBoundary.tsx", 104, "UNKNOWN",
  "任意一次渲染路径崩溃就会显示这面屏（Boundary 包在 app 外层）",
  "不经 HTTP —— 崩的是 React 树本身",
  [], [("frontend", 104), ("frontend", 105)],
  "缺一步：一个旅客在手机上能自己撞出来的崩溃。本会话 :8000 NOT AVAILABLE，我没有活面可跑，"
  "只能证到'组件确实挂在根上'（main.tsx:1668）与'崩溃即渲染'，证不到'崩得了'。"),
 ("frontend/src/features/agent/AgentComposer.tsx", 95, "REACHABLE_ON_PHONE",
  "底栏第 4 项 Copilot（agent 在 mobileRoutes 里）→ 打字发送",
  "POST /api/v1/journeys/{id}/copilot/messages",
  [("backend", 11221)], [("frontend", 95), ("frontend", 196)], ""),
 ("frontend/src/features/agent/CopilotDock.tsx", 615, "REACHABLE_ON_PHONE",
  "Dock 无条件挂载，窄屏还有专属布局（贴底、让位规则）",
  "POST /api/v1/journeys/{id}/copilot/messages",
  [("backend", 11221)], [("frontend", 615), ("frontend", 743)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 307, "REACHABLE_ON_PHONE",
  "底栏 Trips → 预订 tab → 手工录入并提交",
  "POST /api/v1/journeys/{id}/inbox/import",
  [("backend", 4036), ("backend", 4046), ("backend", 4077), ("backend", 640)],
  [("frontend", 308), ("frontend", 687)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 317, "REACHABLE_ON_PHONE",
  "底栏 Trips → 预订 tab，挂载即自动读行程记忆",
  "GET /api/v1/journeys/{id}/memory",
  [("backend", 640)], [("frontend", 318), ("frontend", 687), ("frontend", 346)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 336, "REACHABLE_ON_PHONE",
  "同上，挂载即自动读待办队列",
  "GET /api/v1/journeys/{id}/inbox",
  [("backend", 640)], [("frontend", 339), ("frontend", 731), ("frontend", 350)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 386, "UNKNOWN",
  "要先有 decodedText（扫凭证得到），而扫描器只挂在抽屉里的 bookings 路由",
  "POST /api/v1/journeys/{id}/inbox/extract/text",
  [("backend", 640)], [("frontend", 387), ("frontend", 687), ("frontend", 394)],
  "缺两步：(1) 菜单→全部路由→预订 才能见到扫描器（V8Experience.tsx:1729），Trips 的预订 tab 里没有它；"
  "(2) 手机摄像头的真二维码解码本会话没跑过。"),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 407, "REACHABLE_ON_PHONE",
  "预订 tab → 选一张凭证图片上传",
  "POST /api/v1/journeys/{id}/inbox/extract/image",
  [("backend", 3809), ("backend", 3811), ("backend", 640)],
  [("frontend", 408), ("frontend", 687)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 435, "REACHABLE_ON_PHONE",
  "预订 tab → 对一张草稿点智能应用",
  "POST /api/v1/journeys/{id}/inbox/{draftId}/smart-apply",
  [("backend", 3849), ("backend", 3867), ("backend", 640)],
  [("frontend", 436), ("frontend", 687)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 459, "REACHABLE_ON_PHONE",
  "预订 tab → 审核完点确认",
  "POST /api/v1/journeys/{id}/inbox/{draftId}/confirm",
  [("backend", 4036), ("backend", 4077), ("backend", 640)],
  [("frontend", 460), ("frontend", 474), ("frontend", 691)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 517, "REACHABLE_ON_PHONE",
  "预订 tab → 改字段后保存修改",
  "PATCH /api/v1/journeys/{id}/inbox/{draftId}",
  [("backend", 3849), ("backend", 3867), ("backend", 640)],
  [("frontend", 518), ("frontend", 687)], ""),
 ("frontend/src/features/inbox/JourneyInboxWorkbench.tsx", 691, "REACHABLE_ON_PHONE",
  "确认失败后，同一屏的技术详情折叠里就是服务器原话",
  "承 :459 的失败回答",
  [("backend", 640), ("backend", 4077)], [("frontend", 474), ("frontend", 691)], ""),
 ("frontend/src/features/planning/PlanComparison.tsx", 92, "REACHABLE_ON_PHONE",
  "Today 在未选定方案时就是这面 chooser → 点采用",
  "POST /api/v1/journeys/{id}/plans/{plan_version_id}/select",
  [("backend", 4938), ("backend", 4952), ("backend", 5005), ("backend", 640)],
  [("frontend", 95), ("frontend", 96), ("frontend", 260)], ""),
 ("frontend/src/features/planning/PlanWithAiSheet.tsx", 1016, "REACHABLE_ON_PHONE",
  "Today 建完行程自动开这面 sheet（也可从行程条目进）",
  "POST /api/v1/journeys/{id}/plans/generate",
  [("backend", 4661), ("backend", 4694), ("backend", 4759), ("backend", 640)],
  [("frontend", 159), ("frontend", 161), ("frontend", 1016)], ""),
 ("frontend/src/features/stay/HotelsPanel.tsx", 91, "REACHABLE_ON_PHONE",
  "底栏 Trips → 住宿 tab → 点采用这家",
  "POST /api/v1/journeys/{id}/stay-options/{option_id}/select",
  [("backend", 3156), ("backend", 3172), ("backend", 640)],
  [("frontend", 93), ("frontend", 104), ("frontend", 229)], ""),
]

# structural facts every REACHABLE verdict leans on, quoted not asserted
STRUCTURE = [
 ("frontend/src/routes/v8Routes.ts", 21, "手机底栏只有 5 个键"),
 ("frontend/src/app/V8Experience.tsx", 424, "但抽屉用的是 desktopRoutes ∪ mobileRoutes 的合并表"),
 ("frontend/src/app/V8Experience.tsx", 1440, "窄屏顶栏的汉堡按钮开这个抽屉"),
 ("frontend/src/app/V8Experience.tsx", 1839, "抽屉逐条渲染合并表 ⇒ 手机能走到全部路由键"),
 ("frontend/src/styles.css", 176, "默认 .v8-mobile-nav 不显示"),
 ("frontend/src/app/V8Experience.tsx", 1911, "Trips 的 tab 状态"),
 ("frontend/src/app/V8Experience.tsx", 1959, "住宿 tab 才挂 HotelsPanel"),
 ("frontend/src/app/V8Experience.tsx", 1962, "预订 tab 才挂 JourneyInboxWorkbench"),
 ("frontend/src/app/V8Experience.tsx", 1777, "CopilotDock 在路由分支之外，无条件挂载"),
 ("backend/app/main.py", 492, "所有拒绝都套在 {\"error\": ...} 里"),
 ("backend/app/main.py", 570, "HTTPException 的 detail 原样进 error.message"),
 ("backend/app/main.py", 485, "message 就是那句服务器原话"),
]
CAVEATS = [
 "服务器从不发 `detail` 顶层键（信封是 code/message/message_key/trace_id/details，main.py:483-489）。"
 "所以先读 body?.detail 的那些格子（HotelsPanel.tsx:93、LiveRecovery.tsx:238、PlanComparison.tsx:96）"
 "实际取到的是第二个选择 error.message —— 正文照样进屏，只是取的是 message 不是 detail。",
 "500 不走这条通道：未捕获异常由框架答 'Internal Server Error'，无 JSON 体，前端 :82 的 response.json() "
 "自己抛，屏上看到的是浏览器解析话术，不是服务器原话。所以本表所有 REACHABLE 判的触发前置都是 4xx/5xx "
 "具名拒绝（require 的 404 是最普遍的一条），不是 500。",
 "行程 id 失效是手机上的常见态（本机 localStorage 存的 id 被别处清掉/重置掉），而每个 inbox handler 开头都调 "
 "require(...)，所以那 9 格的 404 正文几乎不需要旅客额外动作。",
 "几何可达我没有量：本会话没有活手机面，`visible_without_scroll` 一律 unmeasured。DOM 里有这句话与"
 "拇指够得着这句话是两件事（账本里 Amendment F 那格实测过：填一个字能把入口从 y=929 顶到视口外）。",
]


def main():
    tip_now = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin",
                              "refs/heads/mirror/integration-frontend-apple-pass1"],
                             capture_output=True).stdout.decode().split()[0]
    # re-read the baseline cell at whichever tip is authoritative right now (task book: 若尖已移动，重读那一格)
    base_recheck = None
    cited_drift = []
    if tip_now != TIP:
        rc = subprocess.run([sys.executable, "-X", "utf8",
                             os.path.join(ROOT, "ui_exposure_field_check_r3.py"),
                             "--ref", tip_now,
                             "--path", "frontend/src/features/planning/PlanWithAiSheet.tsx",
                             "--out", os.path.join(ROOT, "_sweep_scratch", "baseline_newtip.json")],
                            capture_output=True)
        if rc.returncode == 0:
            nb = json.load(io.open(os.path.join(ROOT, "_sweep_scratch", "baseline_newtip.json"),
                                   encoding="utf-8"))
            base_recheck = {"tip": tip_now, "verdict": nb["verdict"], "n_hits": len(nb["hits"]),
                            "rule": nb["hits"][0]["rule"] if nb["hits"] else None,
                            "line": nb["hits"][0]["line"] if nb["hits"] else None,
                            "taint_chain": nb["hits"][0].get("taint_chain") if nb["hits"] else None}
        seen = sorted({c[0] for c in CELLS} | {s[0] for s in STRUCTURE if s[0].startswith("frontend")})
        seen.append("backend/app/main.py")
        for rel in seen:
            a = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "rev-parse", "%s:%s" % (TIP, rel)],
                               capture_output=True).stdout.decode().strip()
            b = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "rev-parse", "%s:%s" % (tip_now, rel)],
                               capture_output=True).stdout.decode().strip()
            if a != b:
                cited_drift.append({"file": rel, "blob_at_generation": a, "blob_at_new_tip": b})

    cells = []
    for f, ln, verdict, path, ep, src, sink, missing in CELLS:
        cells.append({
            "cell": "%s:%d" % (f, ln),
            "cite": "%s:%d" % (f, ln),
            "cell_text": fe(f, ln),
            "verdict": verdict,
            "phone_path": path,
            "endpoint": ep,
            "prose_source": [{"file": "backend/app/main.py" if k == "backend" else f,
                              "line": n, "text": (be(n) if k == "backend" else fe(f, n))}
                             for k, n in src],
            "render_sink": [{"file": f, "line": n, "text": fe(f, n)} for k, n in sink],
            "live_observed": False,
            "visible_without_scroll": "unmeasured",
            "missing_step": missing,
        })
    dist = {}
    for c in cells:
        dist[c["verdict"]] = dist.get(c["verdict"], 0) + 1
    doc = {
     "schema": "CNX_ORD0321_REACHABILITY_V1",
     "order": "ORD-0321",
     "lane": "S1-q64sweep",
     "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
     "generation": TIP,
     "tip_moved": tip_now != TIP,
     "authoritative_tip_now": tip_now,
     "baseline_recheck_at_new_tip": base_recheck,
     "cited_files_drift_between_tips": cited_drift,
     "ruler": R3,
     "ruler_previous": R2,
     "ruler_delta": 0,
     "question_answered": "只判一件事：这格渲染在手机上旅客真能撞到吗。不改产品、不提修法。",
     "cells_total": len(cells),
     "cells_from_sweep": 16,
     "verdict_distribution": dist,
     "live_observed_any": any(c["live_observed"] for c in cells),
     "command_i_ran": "尺本体逐文件 ui_exposure_field_check_r3.py --ref <tip> --path frontend/src/... 扫 74 枚；"
                      "可达性全部静态追证：git show <tip>:backend/app/main.py 落盘后按行号读 require/信封/各 "
                      "handler 的 raise 原文，前端用 git archive <tip> frontend/src 的导出树按行号读挂载条件与 "
                      "CSS 断点；未跑 vite build、未进 frontend/node_modules、未碰 *_live.db。",
     "why_no_live_run": "号令者 03:10 写明 :8000 仍 NOT AVAILABLE 且手机不换代（Q61），本会话没有活手机面；"
                        "所以每格 live_observed=false，UNKNOWN 两格写清缺哪一步。",
     "structural_basis": [{"file": f, "line": n, "text": fe(f, n) if f.endswith((".tsx", ".ts", ".css")) else be(n),
                           "note": t} for f, n, t in STRUCTURE],
     "caveats": CAVEATS,
     "cells": cells,
     "claim_kind": "code_path_determined_not_device_observed",
     "claimed_result": None,
     "derived_result": None,
    }
    doc["claimed_result"] = ("%d cells judged: %s; live_observed=%s"
                             % (doc["cells_total"], json.dumps(dist, sort_keys=True), doc["live_observed_any"]))
    doc["derived_result"] = ("ORD-0321 reachability for tip %s: %d of %d cells reachable on a phone by a "
                             "traveller tap or an auto-run read, %d UNKNOWN with the missing step named"
                             % (TIP[:12], dist.get("REACHABLE_ON_PHONE", 0), doc["cells_total"],
                                dist.get("UNKNOWN", 0)))
    out = os.path.join(ROOT, "_ord0321_reachability_r1.json")
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("cells=%d dist=%s live_observed_any=%s tip_moved=%s" % (doc["cells_total"],
          json.dumps(dist, sort_keys=True), doc["live_observed_any"], doc["tip_moved"]))
    print("empty_quotes=%d" % sum(1 for c in doc["cells"] for b in c["prose_source"] + c["render_sink"] if not b["text"]))
    print("out=%s bytes=%d" % (out, os.path.getsize(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
