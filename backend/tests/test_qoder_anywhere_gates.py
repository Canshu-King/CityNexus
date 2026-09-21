"""ORD-0094 lane F - the seven hard gates of CITYNEXUS-ANYWHERE, as failing evidence.

Mission §19 says this mission is not done because "Beijing works". These seven doors are the
shape of that sentence turned into assertions, written **before** the implementation exists,
so that lane C/D cannot define "done" as whatever their code happens to do.

Rules this file obeys, per the order:
* nothing here is skipped, marked xfail, or relaxed into a tautology - a vacuous gate is worse
  than no gate, which is the failure this project has been charged with repeatedly;
* every assertion message states 期望 and 实际, and every door has a precondition assert in
  front of it, so a red caused by an unfixed fixture can never be read as a red about the
  product;
* no provider network: `tests/conftest.py` strips credentials and AI is off, so these doors
  exercise backend truth only.

Status at authoritative HEAD `4c8c911` (measured, see
`backend/tests/test_qoder_anywhere_contract_parity.py`): G1-G4 and G6b/G7 are red because the
four operations they need do not exist; G5 is red because an AI run that changes nothing still
has no machine-readable outcome; G6a is green and is only a contract-shape guard, labelled as
such so nobody mistakes it for a behaviour proof.
"""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DRAFT_PATH = Path(__file__).resolve().parents[2] / "contracts" / "openapi-anywhere-draft.yaml"

CAPABILITY = "/api/v1/destinations/capability"
HYDRATIONS = "/api/v1/catalog-hydrations"
# 任务书硬要求的"从未预录的县"，车道 E 也用它做 CASE3。
UNSEEN_COUNTY = "贡山独龙族怒族自治县"
COVERAGE_KEYS = {"attractions", "food", "nightlife", "lodging", "mobility", "booking"}
STATES = {"READY", "HYDRATABLE", "UNAVAILABLE", "UNKNOWN"}
OUTCOME_STATUSES = {"PLAN_CREATED", "NO_ACTION", "BLOCKED"}


def _router_absent(response) -> bool:
    """Starlette's own no-such-route answer; the app's refusals look different and mean more."""
    if response.status_code != 404:
        return False
    try:
        body = response.json()
    except Exception:  # noqa: BLE001
        return False
    return isinstance(body, dict) and body.get("detail") == "Not Found"


def _summary(response) -> str:
    try:
        return f"{response.status_code} / {str(response.json())[:220]}"
    except Exception:  # noqa: BLE001
        return f"{response.status_code} / <non-json>"


def _require_endpoint(operation: str, response) -> None:
    """Precondition assert shared by every door that needs the target contract."""
    assert not _router_absent(response), (
        f"期望：{operation} 已实现（任务书 §6 的四个端点之一）；"
        f"实际：{_summary(response)} —— 路由级 404，即后端根本没有这个操作。"
        "这条红是车道 C 的收口条件，不是环境噪声，也不许用 skip 绕开"
    )


def _seeded_journey_id() -> str:
    reset = client.post("/api/v1/demo/reset")
    assert reset.status_code == 200, (
        f"SETUP 失败：/api/v1/demo/reset 期望 200，实际 {_summary(reset)}。"
        "conftest 会把测试进程声明成模拟舞台；若这条红，先查环境，不要改产品语义"
    )
    scene = client.get("/api/v1/demo/scene")
    assert scene.status_code == 200, f"SETUP 失败：/api/v1/demo/scene 实际 {_summary(scene)}"
    journey_id = scene.json().get("journey_id")
    assert journey_id, f"SETUP 失败：reset 之后 scene 里没有 journey_id，实际 {_summary(scene)}"
    return str(journey_id)


# --------------------------------------------------------------------------------------
# G1 · capability truth
# --------------------------------------------------------------------------------------
def test_g1_destination_capability_comes_from_the_backend_not_from_a_count():
    """§2: READY / HYDRATABLE / UNAVAILABLE is backend truth, never a place count or a string."""
    response = client.get(CAPABILITY, params={"query": "Beijing"})
    _require_endpoint("GET /api/v1/destinations/capability", response)

    body = response.json()
    assert body.get("state") in STATES, (
        f"期望：state ∈ {sorted(STATES)}（§2 的语义态，UNKNOWN 与 UNAVAILABLE 必须分开）；"
        f"实际：state={body.get('state')!r}，完整响应 {_summary(response)}"
    )
    coverage = body.get("coverage")
    assert isinstance(coverage, dict) and set(coverage) == COVERAGE_KEYS, (
        f"期望：coverage 六个分类一个不少（缺键是违约，不是「没有数据」）；实际：{coverage!r}"
    )
    assert body.get("reason_code"), (
        f"期望：状态伴随机器可读 reason_code，供界面查表而不是匹配英文句子（§11）；"
        f"实际：reason_code={body.get('reason_code')!r}"
    )


# --------------------------------------------------------------------------------------
# G2 · existing journey recovery
# --------------------------------------------------------------------------------------
def test_g2_an_existing_journey_becomes_plannable_without_being_recreated():
    """§13 hard requirement: the user's journey id survives hydration; no delete/recreate."""
    journey_id = _seeded_journey_id()

    hydration = client.post(HYDRATIONS, json={"destination": UNSEEN_COUNTY, "journey_id": journey_id})
    _require_endpoint("POST /api/v1/catalog-hydrations", hydration)
    operation_id = hydration.json().get("operation_id")
    assert operation_id, f"期望：202 返回 operation_id；实际：{_summary(hydration)}"

    status = client.get(f"{HYDRATIONS}/{operation_id}")
    _require_endpoint("GET /api/v1/catalog-hydrations/{operation_id}", status)
    assert status.json().get("phase"), (
        f"期望：投影里有真实 phase（§6 状态机的名字，不是百分比）；实际：{_summary(status)}"
    )
    assert "progress" not in status.json(), (
        f"期望：没有 progress 百分比字段（§6 原话 No fake percentage）；"
        f"实际：出现了 progress={status.json().get('progress')!r}"
    )

    generate = client.post(f"/api/v1/journeys/{journey_id}/plans/generate")
    scene_after = client.get("/api/v1/demo/scene").json()
    assert generate.status_code in (200, 201), (
        f"期望：水合完成后，**同一个** journey_id（{journey_id}）能出计划（§13）；"
        f"实际：plans/generate 返回 {_summary(generate)}，"
        f"scene 里的 journey 仍是 {scene_after.get('journey_id')!r} / 状态 {scene_after.get('journey_status')!r}"
    )
    assert str(scene_after.get("journey_id")) == journey_id, (
        "期望：旅程身份不变；实际：scene 说台上换成了 "
        f"{scene_after.get('journey_id')!r} —— 悄悄重建一张就是假通过"
    )


# --------------------------------------------------------------------------------------
# G3 · hydration idempotency + concurrency
# --------------------------------------------------------------------------------------
def test_g3_five_concurrent_hydrations_of_one_county_converge_on_one_operation():
    """§7: reuse the same operation_id; no provider storm, no duplicate rows, no lock race."""
    first = client.post(HYDRATIONS, json={"destination": UNSEEN_COUNTY})
    _require_endpoint("POST /api/v1/catalog-hydrations", first)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(
            pool.map(lambda _: client.post(HYDRATIONS, json={"destination": UNSEEN_COUNTY}), range(5))
        )
    codes = sorted(response.status_code for response in responses)
    assert all(code in (200, 201, 202, 409) for code in codes), (
        f"期望：并发 2-5 个同指纹请求，只可能是受理或具名 409；实际状态码 {codes}"
    )
    ids = {response.json().get("operation_id") for response in responses if response.status_code != 409}
    assert len(ids) == 1, (
        f"期望：五个并发请求收敛到**同一个** operation_id（§7 幂等；§17-D 并发）；"
        f"实际拿到 {len(ids)} 个不同的：{sorted(str(x) for x in ids)}。"
        "两个 operation 就是两次 provider 风暴加两份重复目录"
    )
    reused = sum(1 for response in responses if response.json().get("reused") is True)
    assert reused >= 1, (
        f"期望：至少一个调用者被告知 reused=true（「我没开始，是接上别人的」）；"
        f"实际：reused=true 的数量是 {reused}。幂等如果不说实话，就等于没做"
    )


# --------------------------------------------------------------------------------------
# G4 · category coverage
# --------------------------------------------------------------------------------------
def test_g4_partial_catalog_is_never_reported_as_fully_ready():
    """§2: two museums and no food/nightlife/lodging must not read READY for every intent."""
    response = client.get(CAPABILITY, params={"query": UNSEEN_COUNTY})
    _require_endpoint("GET /api/v1/destinations/capability", response)
    body = response.json()
    coverage = body.get("coverage") or {}
    assert set(coverage) == COVERAGE_KEYS, f"期望：六个分类齐全；实际：{sorted(coverage) or coverage!r}"

    if body.get("state") == "READY":
        not_ready = {key: value for key, value in coverage.items() if value != "READY"}
        assert not not_ready, (
            f"期望：state=READY 时每个分类都是 READY；实际：{not_ready} —— "
            "整体 READY、局部 MISSING 就是「能规划一切」的谎"
        )
    places = body.get("place_count")
    if places is not None:
        assert not (places > 0 and body.get("state") != "READY"), (
            f"期望：READY 不由地点数量决定（§2 READY != places.length > 0）；"
            f"实际：place_count={places} 而 state={body.get('state')!r}"
        )


# --------------------------------------------------------------------------------------
# G5 · AI no-op visibility
# --------------------------------------------------------------------------------------
def test_g5_an_ai_run_that_changed_must_say_which_it_was():
    """§11: 0 mutations / 0 proposals / 0 errors must not vanish silently.

    Measured shape today (`4c8c911`, own DB, AI off): the response is
    `{event_id, mission, run}`; `run.outcome` exists but is `null`; `run.status` and
    `mission.status` are the runtime label `SKIPPED_EXTERNAL_DEPENDENCY`. So the seam is
    already there - what is missing is the truth poured into it.
    """
    journey_id = _seeded_journey_id()
    response = client.post(
        f"/api/v1/journeys/{journey_id}/agent/commands",
        json={"command": "帮我把这趟行程重新安排一下", "requested_autonomy": "PLAN_ONLY"},
    )
    assert response.status_code < 500, (
        f"期望：AI 无动作/被挡也要给出可读回答，而不是 5xx；实际：{_summary(response)}"
    )
    body = response.json() if isinstance(response.json(), dict) else {}
    run = body.get("run")
    assert isinstance(run, dict) and run, (
        f"期望：响应里有 `run`（§11 说 outcome 挂在这一层）；实际：顶层键 {sorted(body)[:10]}，"
        f"{_summary(response)[:160]}"
    )

    outcome = run.get("outcome")
    assert isinstance(outcome, dict) and outcome, (
        f"期望：`run.outcome` 带上 §11 的机器可读语义；实际：run.outcome={outcome!r}，"
        f"而 run.status={run.get('status')!r} / failure_reason={str(run.get('failure_reason'))[:60]!r} —— "
        "这次运行确实什么都没改（没 key、没动作），可它只留下一个运行时标签；"
        "一个既没变化也没原因的 200，正是用户早上看到的那句「转了半天啥也没发生」"
    )
    assert outcome.get("status") in OUTCOME_STATUSES, (
        f"期望：status ∈ {sorted(OUTCOME_STATUSES)}（区分「办了/什么都没做/被挡住了」）；"
        f"实际：status={outcome.get('status')!r}，运行时的 SKIPPED_EXTERNAL_DEPENDENCY 不是这个语义"
    )
    assert outcome.get("reason_code"), (
        f"期望：reason_code 具名（§11 的 CATALOG_EMPTY / CATALOG_INSUFFICIENT / "
        f"NO_EXISTING_PLAN_TO_REPLAN / PROVIDER_* 一族），界面才能不靠匹配英文句子分类；"
        f"实际：reason_code={outcome.get('reason_code')!r}"
    )
    assert outcome.get("user_summary") and outcome.get("recommended_action"), (
        f"期望：一句人话 + 一个具体恢复动作（准备数据/重试/改预算/改日期/看可用地点）；"
        f"实际：user_summary={outcome.get('user_summary')!r} "
        f"recommended_action={outcome.get('recommended_action')!r}"
    )


# --------------------------------------------------------------------------------------
# G6 · provenance stays distinguishable
# --------------------------------------------------------------------------------------
def test_g6a_contract_registers_provenance_values_that_can_be_told_apart():
    """Contract-shape guard only, and labelled as such: it proves the vocabulary exists, not
    that any route uses it. G6b is the behaviour half."""
    with DRAFT_PATH.open("r", encoding="utf-8") as handle:
        draft = yaml.safe_load(handle)
    values = set(((draft.get("components") or {}).get("schemas") or {}).get("PlaceProvenance", {}).get("enum", []))
    required = {"FIXTURE", "FETCHED", "SIMULATED", "INFERRED"}
    assert required <= values, (
        f"期望：契约里至少登记 {sorted(required)} 四种来源，彼此可区分；实际：{sorted(values)}"
    )


def test_g6b_capability_answer_carries_the_provenance_of_what_it_found():
    """§5/§10/§11: a sealed fixture, a live fetch and a simulated stage fact cannot share a label."""
    response = client.get(CAPABILITY, params={"query": "Beijing"})
    _require_endpoint("GET /api/v1/destinations/capability", response)
    body = response.json()
    provenance = body.get("provenance") or (body.get("coverage_provenance") or {})
    assert provenance, (
        f"期望：能力结论说得出自己依据哪一类来源（FIXTURE/FETCHED/SIMULATED/…）；"
        f"实际：provenance 缺失，响应键 {sorted(body)[:12]}"
    )
    text = str(provenance).upper()
    assert "LIVE" not in text or "SIMULATED" not in text, (
        f"期望：模拟台产出的数据不得被标成实况（§11/§14，也是本项目反复被记账的假真值）；"
        f"实际：{provenance!r}"
    )


# --------------------------------------------------------------------------------------
# G7 · no manual-city treadmill
# --------------------------------------------------------------------------------------
def test_g7_a_destination_with_no_hand_authored_file_still_gets_an_answer():
    """§19 items 2/3/16/17: "add another JSON city" must stop being the only way forward.

    Measured at `4c8c911`: the hand-authored catalog the product actually reads
    (`MOCK_ROOT/places.json`, i.e. `<repo>/data/mock/places.json`) carries 16 places across
    exactly two codes - CN-BEIJING and CNX-DEMO. Two cities is the treadmill.
    """
    from app.integrations.mock.providers import MOCK_ROOT  # 用产品自己认得的那个路径

    places_path = MOCK_ROOT / "places.json"
    assert places_path.exists(), (
        f"SETUP 失败：产品读的手工目录 {places_path} 不存在 —— 前提变了，这条门要连同任务书一起重写"
    )
    places = json.loads(places_path.read_text(encoding="utf-8"))
    hand_authored = {str(item.get("city_code")) for item in places if isinstance(item, dict)}
    hand_authored.discard("None")
    assert hand_authored, (
        f"SETUP 失败：{places_path} 里没解析出任何 city_code（条目 {len(places)} 个），"
        "这条门的「今天靠手工 JSON 撑城市」前提已不成立，请改门而不是改产品语义"
    )
    assert UNSEEN_COUNTY not in {str(item.get("city_code")) for item in places if isinstance(item, dict)}, (
        f"SETUP 失败：{UNSEEN_COUNTY} 已经出现在手工目录里，那它就不是「从未预录」的县，"
        "本门要换目标（车道 E 的 CASE3 同理）"
    )

    response = client.get(CAPABILITY, params={"query": UNSEEN_COUNTY})
    _require_endpoint("GET /api/v1/destinations/capability", response)
    body = response.json()
    assert body.get("state") in {"HYDRATABLE", "READY", "UNAVAILABLE"}, (
        f"期望：未预录的 {UNSEEN_COUNTY} 也要得到一个语义态（能备 / 已可 / 确实不行）；"
        f"实际：state={body.get('state')!r}，{_summary(response)}。"
        f"手工目录现在只有 {sorted(hand_authored)} 这 {len(hand_authored)} 个城市码，"
        "答案不该由它决定"
    )
    assert body.get("recommended_action") or body.get("state") == "READY", (
        f"期望：不能备就明说不能备，并给用户一条出路（§11/§14）；实际："
        f"recommended_action={body.get('recommended_action')!r} state={body.get('state')!r}"
    )


if __name__ == "__main__":  # pragma: no cover - convenience for a human re-running one door
    raise SystemExit(pytest.main([__file__, "-v"]))
