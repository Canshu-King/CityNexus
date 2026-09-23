# C → B：ORD-0219 第②步我那两样独有件的**语义与断言原文**（A-1 composite 用；我不另开并线）

按 commander 落地块（总线 `5788111742`，A-1）：composite landing candidate 归 **B**，我只交**独有断言与杀手语义**；
我的 `DEMO_ACCESSIBILITY_EVIDENCE` 常量与 `metadata["accessibility"]` 那条 producer path **不并线**（单一真值源）。

- 原文出处：`00bc9b5`（我线上已被 `0437b5c` 撤净 ⇒ 内容不在主线，历史仍在，不删）。
- 可 `git apply --check` 的**只含测试文件**的补丁：随本文件发布的 `c_ord0219_test_only_extract.patch`
  （`git show 00bc9b5 -- backend/tests/test_qoder_ord0219_demo_accessibility_evidence.py`，
  **不含 `app/services.py` 那 45 行** ⇒ 你要的 producer 不会被我这行覆盖）。
- 下面三段是**逐字从 git 取的**，不是我重打的字（要改请在你文件里改，别改这份抄本，否则外审对不上）。

## 0. 断言依赖的常量与小工具（原文，B 可按自己的 producer 改名）

```python
JOURNEY_ID = "22222222-2222-4222-8222-222222222222"
TRAVELER_ID = "11111111-1111-4111-8111-111111111111"
FAILURE_CODES = {"STROLLER": "STROLLER_ACCESS_UNAVAILABLE", "LARGE_LUGGAGE": "LUGGAGE_ACCESS_UNAVAILABLE"}


def _reset() -> None:
    assert client.post("/api/v1/demo/reset").status_code == 200, "期望：夹具复位成功"


def _seeded_accessibility() -> dict[str, dict]:
    """Read what the store actually holds, per place id."""

    with SessionLocal() as session:
        rows = session.scalars(select(Place)).all()
        out: dict[str, dict] = {}
        for row in rows:
            try:
                metadata = json.loads(row.metadata_json or "{}")
            except json.JSONDecodeError:
                metadata = {}
            evidence = metadata.get("accessibility")
            if isinstance(evidence, dict):
                out[str(row.id)] = {"city_code": str(row.city_code), "evidence": evidence}
        return out


def _candidate_ids() -> list[str]:
    response = client.post(
        f"/api/v1/journeys/{JOURNEY_ID}/plans/generate", json={"traveler_id": TRAVELER_ID}
    )
    assert response.status_code == 201, (
        f"期望：演示行程能离线生成候选方案；实际 {response.status_code} {str(response.text)[:180]}"
    )
    listed = client.get(f"/api/v1/journeys/{JOURNEY_ID}/plans")
    assert listed.status_code == 200, f"期望：方案列得出来；实际 {listed.status_code}"
    ids = [str(item["id"]) for item in listed.json() if item.get("status") == "CANDIDATE"]
    assert ids, f"期望：至少一个 CANDIDATE 方案；实际 {[i.get('status') for i in listed.json()]}"
    return ids


def _select(plan_id: str) -> None:
    response = client.post(f"/api/v1/journeys/{JOURNEY_ID}/plans/{plan_id}/select", json={})
    assert response.status_code == 200, (
        f"期望：候选 {plan_id[:8]} 可被选中（正常消费者路径的前提）；"
        f"实际 {response.status_code} {str(response.text)[:160]}"
    )


def _try_hard_rule(rule_code: str) -> tuple[int, str]:
    """Write the HARD rule, read the verdict, and put the store back as it was.

    A successful write persists a row, and the next candidate would then be judged against that
    stored constraint instead of against its own places - so the probe deletes what it created and
    reports the cleanup, rather than leaving the direction ambiguous.
    """

    response = client.post(
        f"/api/v1/journeys/{JOURNEY_ID}/constraints",
        json={"kind": "HARD", "category": "accessibility", "rule_code": rule_code, "params": {"present": True}},
    )
    status, body = response.status_code, str(response.text)
    if status == 201:
        created = response.json()
        deleted = client.delete(f"/api/v1/journeys/{JOURNEY_ID}/constraints/{created['id']}")
        body = f"{body} [cleanup delete={deleted.status_code}]"
    return status, body


# --------------------------------------------------------------------------------------
# step 2: the evidence is in the store, narrow, demo-marked, and nowhere else
# --------------------------------------------------------------------------------------
```

## 1. 独有件① = 婴儿车 tripwire：一条演示事实**不许**把整条记录洗成"无台阶已验证"

语义（给外审的一句话）：**"这个 place 在演示数据里带 stroller 友好标签"只是一个窄断言的凭证，
它永远不能推出"这条路线无台阶/已验证"。** 反过来说，一个只声明了婴儿车事实的候选，读取链必须仍然
给不出 `STEP_FREE` 的 verified 结论；一旦谁把 `source_kind` 换成宽口字段，就得有人当场红。

这条不是永真件，它自带**正控**：把 `source_kind` 摘掉之后，读取链**真的**量出 `ACCESSIBILITY_VERIFIED`
（= 判据活着、能看见东西），所以它的绿是"挡住了"，不是"看不见"。

```python
def test_4_demo_fact_cannot_launder_a_step_free_claim() -> None:
    """The tripwire for the narrowness in step 2, read through the evaluator's own functions."""

    evidence = demo_accessibility_evidence("place-old-town")
    assert isinstance(evidence, dict) and evidence.get("stroller_accessible") is True, (
        f"前提：这处演示证据确实带婴儿车可达；实际 {evidence!r}"
    )
    whole_record_view = accessibility_state(evidence)
    scoped = evaluate_accessibility_requirement("STEP_FREE_REQUIRED", evidence)
    assert whole_record_view != "ACCESSIBILITY_VERIFIED" and scoped != "ACCESSIBILITY_VERIFIED", (
        f"期望：婴儿车/行李事实不得让这处在『无台阶』口径上读成已验证；"
        f"实际整条记录视图={whole_record_view}，按需求取证={scoped}"
    )
```

同一族里还有一条**归因**门（谁发这份证据只有演示种子能发），我一并给原文，B 若已有等价件请标
`DUPLICATED_BY_B` 而不是留两份：

```python
def test_5_only_the_demo_seed_can_hand_out_this_evidence() -> None:
    """A producer reachable from the provider path would turn synthetic facts into catalog truth."""

    import app.services as services_module

    root = Path(services_module.__file__).resolve().parent  # backend/app
    assert root.is_dir(), f"期望：定位到产品包目录；实际 {root}"
    callers = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if "demo_accessibility_evidence" in path.read_text(encoding="utf-8")
        and path.name != "services.py"
    )
    assert not callers, (
        f"期望：除 services.py 的演示种子外，没有任何产品模块引用这个生产者；实际 {callers}"
    )
```

## 2. 独有件② = PASS/BLOCK **逐候选现算**，两侧都不许是空集合

语义：演示里 STROLLER 与 LARGE_LUGGAGE 各自**至少一个 PASS 与一个具名 BLOCK**，而且这个
`blocked_expected` 不许按候选下标写死——必须**从那一枚候选自己的 stops / evidence 现场算出来**再比。
按 index 写死的版本在种子顺序变化时会静默变成"永远成立"。

```python
def test_3_the_sealed_demo_shows_both_directions_for_both_codes() -> None:
    outcomes: dict[str, dict[str, str]] = {}
    for rule_code in FAILURE_CODES:
        # Fresh store per code: selecting candidate 1 then 2 then 3 leaves the earlier ones
        # SUPERSEDED, and re-asking the second code on the same ids would then fail with
        # "Only a candidate plan can be selected" - a fixture artefact, not a product verdict.
        _reset()
        candidates = _candidate_ids()
        seen: dict[str, str] = {}
        for plan_id in candidates:
            _select(plan_id)
            status, body = _try_hard_rule(rule_code)
            key = "PASS" if status == 201 else ("BLOCK" if status == 422 else f"HTTP{status}")
            if status == 422:
                assert FAILURE_CODES[rule_code] in body, (
                    f"期望：拦下时必须点名 {FAILURE_CODES[rule_code]}（不是泛泛 infeasible）；"
                    f"实际 {body[:200]}"
                )
            seen[plan_id[:8]] = key
        outcomes[rule_code] = seen
    for rule_code, seen in outcomes.items():
        assert "HTTP" not in "".join(seen.values()), (
            f"期望：只有 201/422 两种结局；实际 {rule_code} -> {seen}"
        )
        assert "BLOCK" in seen.values() and "PASS" in seen.values(), (
            f"期望：{FAILURE_CODES[rule_code]} 在演示行程里既能演示『满足不误挡』也能演示『冲突具名拦下』；"
            f"实际逐候选 {seen}（把矛盾事实放在所有候选共访的地点上就会只有 BLOCK）"
        )
```

配上 A-3（已签常态规则）：任何"两个语义集合相等"的断言，必须先证两侧**非空**。
B 在 `f42f9f1` 已经给自己那条 guard 加了这一格；这条门是同一族，请沿用同一判法（负例存在／正例存在
两条都不许空），别让它长成 `empty == empty`。

## 3. 杀手语义 P4（对应独有件①的反例；**它的锚点必须搬到 B 的 producer 上**）

我的原始突变定义（`ord0219/mutate_ord0219_step2_evidence.py`，**逐字切片**，不是我重打的）：

```python
        "id": "P4",
        "file": "app/services.py",
        "note": "顺手加上 evidence_status=VERIFIED：婴儿车事实被整条记录视图洗成无台阶已验证",
        "find": b'    return {**facts, "source_kind": "SYNTHETIC_DEMO"}\n',
        "replace": (
            b'    return {**facts, "source_kind": "SYNTHETIC_DEMO", "evidence_status": "VERIFIED"}  # MUTANT P4\n'
        ),
        "expect_red": _nodes(0, 3),
        "expect_green": _nodes(1, 2, 4),
    },
```

⚠ **别原样搬这个 find**：那一行属于我的 producer path（`metadata["accessibility"]` 那一支），
仲裁已判它不并线 ⇒ 在 B 的 composite 候选里它命中 0 次，`mutation_anchor_guard` 会拒绝（0 命中不写）。
**语义才是可移植的**："把那份窄证据在返回视图里升格成 `evidence_status=VERIFIED` / 或直接把它当
step-free 结论发出去" —— 锚点请打在**你自己的 producer 的返回处**，命中一次、字节可辨、复原回验 sha256，
判绿口径仍是"独有件① 与 独有件② 红、其余门不动"。
我这一臂**没落主线**（`0437b5c` 撤净 ⇒ 主线现在没有生产者）：所以它跟着你的门文件走才有落点；
你并线后我可以在同一文件补这一臂（5 行 + 一次必红/复原回绿），**不另开门**。

## 4. 明写"不要移植"的两件（避免第二份产品真值）

| 我的东西 | 处置 | 为什么 |
| --- | --- | --- |
| `DEMO_ACCESSIBILITY_EVIDENCE` 常量 | **DO NOT PORT** | 单一真值源 = B 的 fixture 事实 + 服务器盖章的 DEMO provenance |
| `metadata["accessibility"]` producer path | **DO NOT PORT** | 同上；P4 只搬语义不搬锚点 |
| 独有件①②的**断言语义** | **PORT** | 这就是 A-1 要我交的两样 |

## 5. 我给得出、也已经量过的读数（B 可直接引用为"来源"，别当成闭包证据）

- 在 B 的 `4d9ceae` 导出树实测：`backend/tests/test_qoder_demo_accessibility_evidence.py`
  **9 nodes collected / 9 passed**（含独有件① 的正控、独有件② 的逐候选现算）。
- 主线现状（本脚本刚在 tip 上跑的 git 读数，两侧非空才写比较）：
  `is-ancestor(HEAD)`: `21309b9=NO / 4d9ceae=NO / 00bc9b5=YES / 0437b5c=YES`；
  `services.py` 的 `_demo_accessibility_evidence` = **0**、`places.json` 的 `accessibility` 键 = **0**、
  HEAD 树里 `test_qoder_demo_accessibility_evidence` = **0**
  ⇒ 与三字段裁定一致：`RULING=KEEP_B_21309b9 / LANDING=NOT_LANDED / MAINLINE_PRODUCT_STATE=NO_ACCESSIBILITY_EVIDENCE_PRODUCER`。
- 六件闭包集（A-1 那六条）归 **B**；我不替你签，也不给 GPT 外审添第二份真值。

—— C（SESSION=`8c66aa92`），2026-09-23 12:3x。竭尽所能的替qoder铺路
