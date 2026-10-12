# ORD-0606 双臂证据件 · A臂（未接线）

- 权威尖 `8940570c022950b705cc3b37139d1b8f7052c42a`（ls-remote 现取）；模块来源代表枝 `a5a2f1096e0fbd806acd8be134fe8fb6095ad1a9`
- 解释器 CPython 3.12.14 + pytest 8.4.2 + SQLAlchemy 2.0.52；树 = **整棵提交导出**（含 `backend/`、`data/`、`contracts/`），未起服务、未开库，树内零 `.db` 文件
- 早先两次我只导出了 `backend` 与 `data`，`contracts/openapi.yaml` 缺失造出 48 条 `FileNotFoundError` 假红，那批读数已作废，本件的数来自完整树
- 本臂状态：权威尖 `8940570c` 原样的 `operations/v9.py`：那时 `backend/app/execution/truth.py` 还没上线，本臂是我在 0606 写下之前自己接了一版三处改动之后、又把那三处退回原样所测的读数
- 同批回归（引用 `app.operations.v9` 的 7 个测试模块）：81 passed, 2 warnings in 23.52s
- 本臂红集合条数：0；逐条列表见文末

## 出口投影的真读数（同一支探针、同一个 now）

```json
{
 "clock": "2026-10-12T23:20:00+00:00",
 "projection_keys": [
  "cursor_status",
  "next",
  "next_activity_id",
  "next_eta_min",
  "next_leg_id",
  "next_mode",
  "next_state",
  "now",
  "now_activity_id",
  "now_state",
  "persisted_cursor"
 ],
 "now_keys": [
  "end_at",
  "id",
  "locked",
  "start_at",
  "state",
  "title"
 ],
 "projection_has_execution_truth": false,
 "now_has_execution_truth": false,
 "projection_execution_truth": "<<absent>>",
 "now_execution_truth": "<<absent>>",
 "now_state": "EN_ROUTE",
 "next_activity_id": "act-2"
}
```

## 逐条红名

```
(none)
```

