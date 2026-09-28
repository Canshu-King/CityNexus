"""h11_autonomous.py — H11: the model gets a goal, not a recipe.

Withheld on purpose: the trigger event id, the affected activity, which tool to call and
in what order. Not faked: the disruption is real world-state, persisted through the
product's own HTTP endpoint, because "this journey has a problem" is the premise of the
gate rather than a hint.

Every predicate is computed from the database and the backend access log. If the agent
cannot get there, the run records where it stopped and what it actually saw — the
predicates are not relaxed to buy a green.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location("arm", Path(__file__).with_name("dsh_arm_streak.py"))
arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arm)  # main() is guarded; module-level code is import-safe

GOAL = (
    "你是 CityNexus 的运维代理。行程 22222222-2222-4222-8222-222222222222 现在可能正受到一次"
    "真实中断的影响。请你自己完成下面这些判断，不要问我怎么做：\n"
    "1) 到底有没有问题、问题落在哪个站点；\n"
    "2) 如果有，提出一次改判（我不会告诉你触发事件的 id，你得自己从工具能读到的内容里找到它）；\n"
    "3) 如果授权政策允许自动接受，就把它接受落地；\n"
    "4) 最后确认当前生效的计划版本有没有变化。\n"
    "只用名字以 mcp__citynexus__ 开头的工具。每一步把你依据的原文（decision 字段、reason_codes、"
    "你读到的关键字段名）抄出来。如果某一步做不到，直接说做不到、卡在哪、你看到了什么，不要编造 id。"
)


def write_patch(path: Path) -> None:
    path.write_text(
        "- insert:\n    - id: mcp-citynexus\n      name: '@deepseek-ai/dsh-mcp-client'\n"
        "      config:\n        serverName: citynexus\n        transport: stdio\n"
        f"        command: '{arm.PY}'\n        args: ['-m', 'citynexus_mcp.server', '--v2']\n"
        f"        cwd: '{arm.CAND}\\agent-mcp'\n        env:\n"
        f"          PYTHONPATH: '{arm.CAND}\\agent-mcp'\n"
        f"          CITYNEXUS_API_BASE_URL: '{arm.BASE}'\n"
        "        toolCallTimeoutMs: 120000\n        failOnStartupError: true\n",
        encoding="utf-8", newline="\n")


def main():
    db = arm.LANE / f"_h11_{arm.TAG}.db"
    arm.DB_PATH = db
    for suffix in ("", "-wal", "-shm"):
        Path(str(db) + suffix).unlink(missing_ok=True)

    seed_env = {**os.environ, "CITYNEXUS_DATABASE_URL": "sqlite:///" + str(db).replace("\\", "/"),
                "LANE_BACKEND_ROOT": str(arm.CAND / "backend")}
    s = arm.sh([str(arm.PY), str(arm.LANE / "seed_lane_db.py")], env=seed_env, timeout=300)
    if s.returncode != 0:
        print(json.dumps({"fatal": "seed", "tail": (s.stderr or s.stdout)[-400:]}, ensure_ascii=False))
        return 1

    log = arm.LANE / f"_h11_{arm.TAG}_backend.log"
    proc = arm.boot(db, log)
    doc: dict = {"gate": "H11 model-driven flagship", "tree": str(arm.CAND), "port": arm.PORT,
                 "withheld": ["trigger_event_id", "affected_activity", "tool order"],
                 "goal": GOAL}
    try:
        arm.sh([str(arm.PY), str(arm.LANE / "build_active_plan.py")], timeout=420)
        doc["policy"] = arm.set_policy()
        event_id, activity = arm.make_event()
        doc["world_has_event"] = bool(event_id)
        doc["event_id_not_told_to_model"] = event_id
        before = arm.db_state(db)
        doc["before"] = before

        patch = arm.LANE / f"_h11_{arm.TAG}_mcp.yml"
        write_patch(patch)
        t0 = time.time()
        r = arm.sh(["node", str(arm.DSH_BIN), "--profile", "headless", "--patch", str(patch), GOAL],
                   timeout=1200)
        doc["wall_s"] = round(time.time() - t0, 1)
        doc["dsh_rc"] = r.returncode
        doc["answer"] = (r.stdout or "")[-2500:]
        doc["stderr_tail"] = (r.stderr or "")[-300:]

        wire = log.read_text(encoding="utf-8", errors="replace")
        hits = re.findall(r"POST /api/v1/agent/tools/([a-z_]+)", wire)
        doc["tools_hit"] = {t: hits.count(t) for t in sorted(set(hits))}
        after = arm.db_state(db)
        doc["after"] = after

        doc["Q1_found_the_affected_activity"] = bool(re.search(r"Tech Art|受影响的站点|affected", doc["answer"]))
        doc["Q2_attempted_request_replan"] = "request_replan" in doc["tools_hit"]
        doc["Q3_replan_produced_a_proposal"] = after["accepted"] > before["accepted"] or bool(
            re.search(r"proposal_id|提案 id|proposal id", doc["answer"], re.I))
        doc["Q4_active_flipped"] = before["active_ids"] != after["active_ids"]
        doc["Q5_single_active"] = len(after["active_ids"]) == 1
        doc["Q6_no_overreach"] = not [t for t in ("create_booking", "cancel_refundable_booking")
                                      if t in doc["tools_hit"]] and after["bookings"] == 0
        doc["H11_green"] = all(doc[k] for k in ("Q1_found_the_affected_activity",
                                                "Q2_attempted_request_replan",
                                                "Q4_active_flipped", "Q5_single_active", "Q6_no_overreach"))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()

    out = arm.LANE / f"H11_AUTONOMOUS_{arm.TAG}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps({k: doc.get(k) for k in ("world_has_event", "wall_s", "dsh_rc", "tools_hit",
                                              "H11_green", "Q1_found_the_affected_activity",
                                              "Q2_attempted_request_replan", "Q3_replan_produced_a_proposal",
                                              "Q4_active_flipped", "Q5_single_active", "Q6_no_overreach")},
                     ensure_ascii=False, indent=1))
    print("WROTE", out)
    return 0 if doc.get("H11_green") else 1


if __name__ == "__main__":
    raise SystemExit(main())
