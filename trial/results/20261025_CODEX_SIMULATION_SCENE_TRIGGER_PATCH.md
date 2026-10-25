# SimulationRun 场景事件与守护触发事件对齐（给 Codex 的补丁建议）

关联 Issue #47 / `docs/revolution/SIMULATION_RUN_API_20261025.md`。我只读了分支 `a8f9b8ed16` 的代码、在隔离栈上量了读数，没有改后端的树。

## 现象（隔离栈，真模型，课堂服务未动）

1. `POST /scenes` 注入一条 CLOSURE，run 的 `state.pending_event_id` 指向新事件 A。
2. `POST /guardian` 真模型跑了 218 秒成功：`PAUSED_FOR_ACCEPTANCE`、`SERVER_GUARDIAN_EXECUTED`、`PROPOSAL_PRESENTED`、有 `agent_run_id` 与 `proposal_id`（`trial/results/20261022_v3_human_chrome/guardian-model-walk-1.txt:5`、`:9`）。
3. 在守护屏接受提案后，A 仍是 `DETECTED`；接受的是一条约会事件 B 的提案。
4. `POST /resume` 回 409 `SIMULATION_EVENT_REQUIRES_SIGNED_RESOLUTION`；控制台停在「等待接受调整」（另一次干净场景复跑在 335 秒内没有落定：`classroom-presenter-model-loop-26.txt:8`）。

## 机制（三条各自正确，组合起来差一件）

- `app/agent/guardian.py` 的 `_open_events` 按 `detected_at` 升序取未决事件，守护处理的是最早那条；run 注入的事件是最晚的一条，排在演示库预置事件之后。
- `app/simulation/api.py` 的 `resume` 只认 `state.pending_event_id` 对应事件处于 `RESOLVED` 或 `IGNORED`。
- `app/main.py` 接受重规划时只把提案自己的 `trigger_event` 置为 `RESOLVED`（`JOURNEY_ADAPTED`）。

## 最小修法（推荐）：注入场景时复用同一趟里已有的同类未决事件

```diff
--- a/app/simulation/runtime.py
+++ b/app/simulation/runtime.py
@@ -10,7 +10,7 @@
-from app.db.models import Activity, Place, PlanVersion, SimulationClock
+from app.db.models import Activity, Event, Place, PlanVersion, SimulationClock
@@ def inject_scene(session, journey, run, scene):
-    event, _ = _upsert_fixture_event(
-        session,
-        journey,
-        event_type=scene["event_type"],
-        severity="MAJOR",
-        activity=row,
-        scope_key=row.place_id or row.id,
-        occurred_at=run.virtual_now,
-        provenance="SIMULATED",
-        payload={
-            "source": "CLASSROOM_SIMULATION",
-            "simulation_run_id": run.id,
-            "scene_id": scene["scene_id"],
-            "disruption_class": scene["event_type"],
-            "delay_minutes": scene.get("delay_minutes", 0),
-            "is_closed": scene["event_type"] == "CLOSURE",
-        },
-    )
+    # 一堂课一次同类事故：守护只会拾起最早那条未决事件，所以这里必须复用它，
+    # 否则 run 自己的事件永远排在它后面，`/resume` 也就永远等不到解决。
+    event = session.scalars(
+        select(Event)
+        .where(
+            Event.journey_id == journey.id,
+            Event.status.in_(("DETECTED", "ACKNOWLEDGED")),
+            Event.event_type == scene["event_type"],
+        )
+        .order_by(Event.detected_at, Event.id)
+    ).first()
+    if event is None:
+        event, _ = _upsert_fixture_event(
+            session,
+            journey,
+            event_type=scene["event_type"],
+            severity="MAJOR",
+            activity=row,
+            scope_key=row.place_id or row.id,
+            occurred_at=run.virtual_now,
+            provenance="SIMULATED",
+            payload={
+                "source": "CLASSROOM_SIMULATION",
+                "simulation_run_id": run.id,
+                "scene_id": scene["scene_id"],
+                "disruption_class": scene["event_type"],
+                "delay_minutes": scene.get("delay_minutes", 0),
+                "is_closed": scene["event_type"] == "CLOSURE",
+            },
+        )
```

复用时要保持旧事件的 `provenance` 不动（它可能是 `PROVIDER_VERIFIED`），只把 `scene_id` 与 `simulation_run_id` 合并进 payload；`SIM_SCENE_INJECTED` 历史照旧写 `event.id`。如果产品坚持「每次注入都要新事件」，那就得换成下面的备选。

## 备选：guardian 以 run 的 pending 为唯一输入

- `api.py` 的 `guardian` 在调用 `scan_guardian` 前，把 `state["pending_event_id"]` 对应事件作为焦点传入（需要给 `scan_guardian` 加参数），或把其它未决 actionable 事件在该次扫描里排除。
- 改动面更大，会影响 autopilot 的扫描路径；建议先做上面的复用方案。

## 验证步骤

1. `python trial/play_launcher/classroom_demo/rehearse_simulation_console_r1.py --with-model --keep --stack-only`
2. `SIM_BASE=http://127.0.0.1:14493 node trial/human_walk/_classroom_presenter_model_loop_r26.mjs`
3. 期望读数：注入后只有一条同类 CLOSURE 未决；守护成功后 `pending_event_id` 指向提案的 trigger；接受提案后 `resume` 回 `RUNNING`；控制台出现「走到下一阶段」。

## 边界

- 我没有改你们的树；补丁只是建议，需要在 fixture 与真实演示库上各复验一次。
- 真模型耗时波动大（218 秒到 335 秒以上），课堂主链不应现场等模型；这是产品口径，不是本补丁的范围。
