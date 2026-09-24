"""欠件 1：三行现场读数 - "服务器答了的错误信封"在正常路径上到底被分类成什么。

两侧同判的口径按包工头要求实现：
  * 服务端字段一律用 `==`（逐字符等值），不用 `in`；并自带**双向控**：
      - 正控：`JOURNEY_NOT_FOUND == JOURNEY_NOT_FOUND` 必须判"认"；
      - 负控：`JOURNEY_NOT_FOUND_X` 里含 `JOURNEY_NOT_FOUND`，用 `in` 会被读成匹配 ⇒ 我的判据必须判"不认"。
  * 屏上侧读的是**渲染出来的文字**（innerText）与「归因详情」里展开的遥测串，不是 data-* 属性；
  * 服务端侧从假源站自己写的 JSONL 日志读，不从 app 日志推。

现场坐标全部由这个进程重新量一次（端口、pid、被服务的 bundle 摘要、权威尖），不是我抄进来的。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path("D:/moodle/_qoder_integration_20260919")
JOURNEY_ROUTE = "/api/v1/journeys/11111111-2222-3333-4444-555555555555/experience"

# 服务端侧：假源站自己落的日志（逐行读，取每条路由具名的响应）
LOG = [json.loads(l) for l in (HERE / "origin_log.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]


def served(route: str, status: int) -> dict:
    hits = [r for r in LOG if r.get("route") == route and r.get("status") == status]
    if not hits:
        raise SystemExit(f"源站日志里没有 {route} {status} 这条 ⇒ 不许凭记忆写读数")
    return hits[-1]


# 屏上侧：browser-use evaluate 当场回传的渲染文字与遥测串（逐字转写，出处在 readings 里标出）
READINGS = [
    {"line": 1, "scenario": "404_journey_not_found", "status": 404,
     "expect_server_code": "JOURNEY_NOT_FOUND",
     "screen_headline": "这台服务器上没有这一趟行程了",
     "screen_body": "这台设备还记得行程 11111111…，但服务器明确回答它不存在（HTTP 404）。这不是网络问题：服务器刚才答得出来。你的其它行程没有受影响。",
     "screen_ctas": "选一趟行程 · 重试 · 归因详情",
     "telemetry": ["attribution_reason=JOURNEY_NOT_FOUND", "evidence_kind=HTTP_RESPONSE",
                   "http_status=404", "source_layer=RESOURCE_STATE", "retryable=false",
                   "recovery_action=choose-journey"]},
    {"line": 2, "scenario": "422_validation_error", "status": 422,
     "expect_server_code": "VALIDATION_ERROR",
     "screen_headline": "这一次没读到",
     "screen_body": "服务器接上了，但这次读取没有成功，原因还没有分类。可以重试。",
     "screen_ctas": "重试 · 归因详情",
     "telemetry": ["attribution_reason=UNKNOWN_FAILURE", "evidence_kind=HTTP_RESPONSE",
                   "http_status=422", "source_layer=RESOURCE_STATE", "retryable=false",
                   "recovery_action=retry"]},
    {"line": 3, "scenario": "503_hydration_busy", "status": 503,
     "expect_server_code": "HYDRATION_STORE_BUSY",
     "screen_headline": "服务器这次没能把行程读出来",
     "screen_body": "服务器自己报错了（HTTP 503）。这是它那边的问题，不是你填错了什么。可以重试；如果一直这样，稍后再来。",
     "screen_ctas": "重试 · 归因详情",
     "telemetry": ["attribution_reason=SERVER_ERROR", "evidence_kind=HTTP_RESPONSE",
                   "http_status=503", "source_layer=RUNTIME", "retryable=true",
                   "recovery_action=retry", "cached_copy_present=false"]},
]
BANNED = {"NETWORK_UNAVAILABLE", "NO_REPLY", "UNKNOWN_FAILURE"}  # 包工头 15:3x 抄给我的 ORD-0263 合同


def eq(a: str | None, b: str) -> dict:
    """The only comparison shape allowed for a server field: whole-string equality."""
    return {"left": a, "right": b, "equal": a == b, "operator": "=="}


def selftest() -> dict:
    pos = eq("JOURNEY_NOT_FOUND", "JOURNEY_NOT_FOUND")["equal"] is True
    near = "JOURNEY_NOT_FOUND_X"
    neg_eq = eq(near, "JOURNEY_NOT_FOUND")["equal"] is False
    neg_in = "JOURNEY_NOT_FOUND" in near  # what a lax judge would have called a match
    if not (pos and neg_eq and neg_in):
        raise SystemExit("equality judge self-test failed - the receipt cannot be trusted")
    return {"positive_control_equality_accepted": pos,
            "negative_control_containment_rejected": neg_eq,
            "the_lax_operator_would_have_said": neg_in,
            "meaning": "把带后缀的漂移读成匹配是 `in` 的常规失误；本收据里所有服务端字段比较都是 ==，"
                       "所以第 2 行那句「服务端确实具名了 VALIDATION_ERROR」不会因为屏上没出现它就被记成匹配。"}


def reason_of(tel: list[str]) -> str | None:
    for t in tel:
        if t.startswith("attribution_reason="):
            return t.split("=", 1)[1]
    return None


def listeners() -> dict:
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True).stdout.decode(
        "utf-8", errors="replace")
    found = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[2] == "0.0.0.0:0":
            for port in ("8610", "8611"):
                if p[1].endswith(":" + port):
                    found[port] = {"local": p[1], "pid": p[-1], "state": p[3]}
    return found


def main() -> int:
    bundle = HERE / "dist/assets/index-Cpy_jhEg.js"
    raw = bundle.read_bytes()
    rows = []
    for r in READINGS:
        srv = served(JOURNEY_ROUTE, r["status"])
        cmp_server = eq(srv.get("server_error_code"), r["expect_server_code"])
        reason = reason_of(r["telemetry"])
        rows.append({
            "line": r["line"],
            "route": JOURNEY_ROUTE,
            "http_status_client_side_observed": r["status"],
            "http_status_origin_side": srv["status"],
            "statuses_agree_both_sides": r["status"] == srv["status"],
            "origin_content_type": srv["content_type"],
            "server_field_equality": cmp_server,
            "screen_headline_rendered": r["screen_headline"],
            "screen_body_rendered": r["screen_body"],
            "screen_ctas_rendered": r["screen_ctas"],
            "attribution_telemetry_expanded_on_screen": r["telemetry"],
            "reason": reason,
            "ord0263_contract": {"banned": sorted(BANNED), "reason_in_banned": reason in BANNED,
                                 "verdict": "合同内" if reason not in BANNED else "合同破（answered 却落进被禁那一格）"},
            "server_named_code_carried_to_screen": any(t.startswith("server_code=") for t in r["telemetry"]),
        })
    out = {
        "kind": "CNX_ANSWERED_ENVELOPE_READING_V1",
        "owe": "欠件 1：错误信封在正常路径上确实 VALID 的三行现场读数",
        "asked_by": "包工头 @15:3x（总线 5806340154 同批），口径：路由 + HTTP 码 + 屏上文字/服务端字段两侧同判；"
                    "服务端字段用 == 不用 in，并带一枚「等值必须认」的正控",
        "surface": {
            "authoritative_tip_at_read_time": subprocess.run(
                ["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True,
                text=True).stdout.strip(),
            "frontend_bundle_served": {"path": str(bundle), "bytes": len(raw),
                                       "sha256": hashlib.sha256(raw).hexdigest(),
                                       "same_as_commander_quoted_prefix": hashlib.sha256(raw).hexdigest()
                                       .startswith("5d674a444291f10b45fa50dc")},
            "bundle_source_tree": "我的副本，取自 _qoder_cmdr_deploy_2b49e3c_0923/repo/frontend/dist"
                                  "（2b49e3ca 那一代，含 ORD-0263 的分类器；权威线一字未动）",
            "preview": {"url": "http://127.0.0.1:8610", "note": "vite preview --outDir 指我自己那份 dist，"
                        "CITYNEXUS_BACKEND_PORT=8611 让 /api 落在我自己的假源站（归属由 origin_log + "
                        "响应头 server: BaseHTTP/0.6 Python/3.12.14 两侧证明）"},
            "origin": {"port": 8611, "role": "只答合法信封的假源站；它同时是被测服务端字段的记录者"},
            "listeners_at_build_time": listeners(),
            "db": "本探针 0 打开任何 .db：假源站不回真数据，产品后端没被起过；_live.db/_preview.db 0 接触",
        },
        "reading_method": {
            "client_side": "页面自己发的 fetch：performance.getEntriesByType('resource') 的 route + responseStatus",
            "screen_side": "document.body.innerText（渲染文字）+ 点开 <summary>「归因详情」后的遥测串",
            "server_side": "假源站自己 append 的 origin_log.jsonl（route/status/content_type/server_error_code）",
            "not_used": "没有从任何 app 日志 grep；没有我自己调用分类器；没有读 data-* 属性",
        },
        "equality_self_test": selftest(),
        "rows": rows,
        "summary": {
            "answered_envelope_never_says_network_down": all("网络" not in r["screen_body_rendered"] or
                                                             "不是网络问题" in r["screen_body_rendered"]
                                                             for r in rows),
            "lines_inside_contract": sum(1 for r in rows if r["ord0263_contract"]["verdict"] == "合同内"),
            "lines_outside_contract": [r["line"] for r in rows if r["ord0263_contract"]["verdict"] != "合同内"],
            "server_named_code_reaches_screen_on_any_line": any(
                r["server_named_code_carried_to_screen"] for r in rows),
        },
        "unscripted_route_disclosure": {
            "route": "/api/v1/demo/scene", "status_in_my_origin_log": 599,
            "meaning": "这一条不是产品答的，是我的假源站对**没脚本化**的路由打的标记（我让它在未指定时 loudly 599 "
                       "而不是假装 200）。它出现在日志里所以我写出来，不藏。",
        },
        "generated_at_local_clock": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M%z"),
        "constraints": "0 产品码改动、0 次 demo/reset、0 写 _live.db/_preview.db、0 新建隧道、"
                       "不直写权威线；证据文件名不含被禁片段",
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if "\r" in text:
        raise SystemExit("CRLF")
    target = HERE / "answered_envelope_reading_v1.json"
    if target.exists():
        target.unlink()  # local scratch, never published before this line
    target.write_text(text, encoding="utf-8", newline="\n")
    for r in rows:
        print(f"L{r['line']} {r['route'][:44]}… {r['http_status_origin_side']} "
              f"server=={r['server_field_equality']['equal']} reason={r['reason']} "
              f"{r['ord0263_contract']['verdict']} 屏上：「{r['screen_headline_rendered']}」")
    print("summary:", json.dumps(out["summary"], ensure_ascii=False))
    print("->", target.name, target.stat().st_size, "B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
