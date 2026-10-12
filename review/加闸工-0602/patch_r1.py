# -*- coding: utf-8 -*-
"""ORD-0602 / CMDR-RULING-0608 甲半: report the source of the route fact on the recovery door and on screen.

Additive only: nothing in the authorization, gate or 422 path reads what this computes, so no existing
放行/拒绝 result can change.  Every replacement must match exactly once; files stay LF.
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WT = "D:/moodle/_jz_0602/wt2/"
MAIN = WT + "backend/app/main.py"
DICT = WT + "frontend/src/i18n/LocaleContext.tsx"
APP = WT + "frontend/src/app/V8Experience.tsx"

EDITS = [
    # 1. backend import, next to the clock import already in this file
    (MAIN,
     "from app.execution.clock import execution_clock\n",
     "from app.execution.clock import execution_clock\n"
     "from app.execution.route_session_contract import (  # ORD-0602 甲半: source of truth, reporting only\n"
     "    ROUTE_TRUTH_POLICY_VERSION,\n"
     "    classify_capture,\n"
     "    fact_is_eligible_for_live_readiness,\n"
     ")\n"),
    # 2. compute the two contract readings from the fact this flow already fetched
    (MAIN,
     '    if fact is None:\n'
     '        raise HTTPException(422, f"{requested_mode} is unavailable for this captured leg")\n',
     '    if fact is None:\n'
     '        raise HTTPException(422, f"{requested_mode} is unavailable for this captured leg")\n'
     '    # The ruling splits this in two halves: stating where a route fact came from is approved, while\n'
     '    # refusing a non-provider fact is not.  So nothing below feeds `authorized`, the gate or the 422.\n'
     '    route_truth_fact = fact_payload(fact)\n'
     '    route_truth_live = fact_is_eligible_for_live_readiness(route_truth_fact)\n'
     '    route_truth_status, route_truth_outcome = classify_capture(\n'
     '        explicit_fact=route_truth_fact,\n'
     '        provider_failed=False,\n'
     '        provider_degraded=not route_truth_live,\n'
     '    )\n'),
    # 3. the response gains one reporting key; every existing key keeps its bytes
    (MAIN,
     '        "post_action_gate": gate_status,\n'
     '        "option": option_payload(option, offers) if option else None,\n'
     '    }\n',
     '        "post_action_gate": gate_status,\n'
     '        "route_truth": {\n'
     '            "policy_version": ROUTE_TRUTH_POLICY_VERSION,\n'
     '            "provider": route_truth_fact["provider_key"],\n'
     '            "provenance": route_truth_fact["provenance"],\n'
     '            "capture_status": route_truth_status,\n'
     '            "capture_outcome": route_truth_outcome,\n'
     '            "eligible_for_live_readiness": route_truth_live,\n'
     '        },\n'
     '        "option": option_payload(option, offers) if option else None,\n'
     '    }\n'),
    # 4a. dictionary, English side
    (DICT,
     '  "shell.autopilotPaused": "Autopilot paused for confirmation · {reasons}.",',
     '  "shell.autopilotPaused": "Autopilot paused for confirmation · {reasons}.",\n'
     '  /* ORD-0602 甲半: where the route timing behind this switch came from.  Stating it is approved;\n'
     '     blocking on it is not, so the sentence says the system did not stop the operation. */\n'
     '  "shell.autopilotTruthLive": " The route timing here was measured by a provider, so it can carry a leave-now check.",\n'
     '  "shell.autopilotTruthSynthetic": " The route timing here is synthetic or estimated, not a provider measurement; this run states the source and did not block the operation over it.",'),
    # 4b. dictionary, Chinese side, same order
    (DICT,
     '  "shell.autopilotPaused": "自动驾驶暂停等待确认 · {reasons}。",',
     '  "shell.autopilotPaused": "自动驾驶暂停等待确认 · {reasons}。",\n'
     '  "shell.autopilotTruthLive": "这次换走法用的路线时长是供应商实测的，够格支撑出发判断。",\n'
     '  "shell.autopilotTruthSynthetic": "这次换走法用的路线时长是合成或估算的，不是供应商实测；这里只把来源说清，本次操作没有因此被拦下。",'),
    # 5a. screen: the response type carries the new reporting key
    (APP,
     '        reason_codes: string[];\n'
     '      }>(\n'
     '        `/api/v1/journeys/${data.journey.id}/stay-options/${selected.id}/autopilot/recover`,',
     '        reason_codes: string[];\n'
     '        route_truth?: { eligible_for_live_readiness: boolean };\n'
     '      }>(\n'
     '        `/api/v1/journeys/${data.journey.id}/stay-options/${selected.id}/autopilot/recover`,'),
    # 5b. screen: the sentence is appended to what the traveller already reads
    (APP,
     '      setMessage(\n'
     '        result.executed\n'
     '          ? t("shell.autopilotRecovered", {\n'
     '              mode: result.after_mode.toLowerCase(),\n'
     '            })\n'
     '          : t("shell.autopilotPaused", {\n'
     '              reasons: result.reason_codes.join(" · "),\n'
     '            }),\n'
     '      );',
     '      setMessage(\n'
     '        (result.executed\n'
     '          ? t("shell.autopilotRecovered", {\n'
     '              mode: result.after_mode.toLowerCase(),\n'
     '            })\n'
     '          : t("shell.autopilotPaused", {\n'
     '              reasons: result.reason_codes.join(" · "),\n'
     '            })) +\n'
     '        (result.route_truth\n'
     '          ? t(\n'
     '              result.route_truth.eligible_for_live_readiness\n'
     '                ? "shell.autopilotTruthLive"\n'
     '                : "shell.autopilotTruthSynthetic",\n'
     '            )\n'
     '          : ""),\n'
     '      );'),
]

by_file = {}
for path, old, new in EDITS:
    if path not in by_file:
        by_file[path] = io.open(path, "r", encoding="utf-8", newline="").read()
    src = by_file[path]
    n = src.count(old)
    if n != 1:
        print("ABORT %s :: 锚点命中 %d 次\n%s" % (path.split("/")[-1], n, old[:90]))
        raise SystemExit(1)
    by_file[path] = src.replace(old, new, 1)
    print("OK   %s  <-  %s" % (path.split("/")[-1], old.strip().split("\n")[0][:64]))

for path, src in by_file.items():
    io.open(path, "w", encoding="utf-8", newline="").write(src)
    print("WROTE %s  LF=%d  CRLF=%d" % (path.split("/")[-1], src.count("\n"), src.count("\r\n")))
