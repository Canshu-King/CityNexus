"""ORD-0219 step 2+3+4 - the sealed demo carries its own accessibility evidence, and the normal
`Place -> evidence -> feasibility` chain demonstrates **both** directions of both codes.

Arbiter `5778570154`: "不接受『只在合成夹具可演示』".  Before this change the demo library had
0/16 accessibility facts, so a traveller opening CityNexus could never see a stroller or luggage
rule pass or block, even though the gate already executes both codes.

What these doors refuse to do:
* they never trust an HTTP 201 alone - the store is read back for every claim about what was seeded;
* they compute which candidate passes and which blocks rather than assuming a plan index, because
  placement of the contradicting fact on a *shared* place makes the pass direction unsatisfiable
  while a hardcoded door still looks green (measured that way once, comment in `services.py`);
* they pin the negative side of the ruling too: a demo place without evidence must stay UNKNOWN,
  and a demo stroller/luggage fact must not launder a step-free claim.

Chain under test is the product's own: `POST /demo/reset` -> `POST /plans/generate` ->
`POST /plans/{id}/select` -> `POST /constraints` (kind=HARD), which is the same path a real
traveller's write takes through `validate_selected_plan_feasibility`.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.capabilities import accessibility_state, evaluate_accessibility_requirement
from app.db.models import Place
from app.db.session import SessionLocal
from app.main import app
from app.services import DEMO_ACCESSIBILITY_EVIDENCE, demo_accessibility_evidence

client = TestClient(app)
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
def test_1_seeded_demo_evidence_is_narrow_and_explicitly_not_live() -> None:
    _reset()
    seeded = _seeded_accessibility()
    assert sorted(seeded) == sorted(DEMO_ACCESSIBILITY_EVIDENCE), (
        f"期望：只有点名的演示地点带证据（其余 13 个保持无证据）；"
        f"实际带证据 {sorted(seeded)}，点名 {sorted(DEMO_ACCESSIBILITY_EVIDENCE)}"
    )
    for place_id, row in sorted(seeded.items()):
        evidence = row["evidence"]
        assert row["city_code"] == "CNX-DEMO", (
            f"期望：带证据的地点属于演示城市（不得泄进 normal-city）；"
            f"实际 {place_id} 的 city_code={row['city_code']!r}"
        )
        assert evidence.get("source_kind") == "SYNTHETIC_DEMO", (
            f"期望：provenance 显式 SYNTHETIC_DEMO；实际 {place_id} -> {sorted(evidence)}"
        )
        leaked = sorted(
            key
            for key in evidence
            if key in {"evidence_status", "status", "step_free", "step_free_verified", "wheelchair_access"}
        )
        assert not leaked, (
            f"期望：婴儿车/行李的事实不得伪装成台阶可达性凭证（{leaked} 会被整条记录的视图读成已验证）；"
            f"实际 {place_id} -> {sorted(evidence)}"
        )
        assert not any("LIVE" in str(value).upper() for value in evidence.values()), (
            f"期望：任何取值里都不出现 LIVE 字样（不得冒充 provider truth）；实际 {place_id} -> {evidence}"
        )


def test_2_a_place_without_demo_evidence_stays_unknown() -> None:
    _reset()
    unmarked = "place-riverside-museum"
    with SessionLocal() as session:
        row = session.get(Place, unmarked)
        metadata = json.loads(row.metadata_json or "{}")
    assert "accessibility" not in metadata, (
        f"期望：没点名的地点完全没有 accessibility 段（None/UNKNOWN 语义要演示得出来）；"
        f"实际 {unmarked} -> {sorted(metadata)}"
    )
    assert demo_accessibility_evidence(unmarked) is None, (
        "期望：生产者对这个地点返回 None（不是造一个默认可达）"
    )
    assert demo_accessibility_evidence("place-a-real-city-one") is None, (
        "期望：演示表外的任何 id 都拿不到证据（正常城市不受影响）"
    )


# --------------------------------------------------------------------------------------
# step 3 + 4: the same normal chain shows pass and block for both codes
# --------------------------------------------------------------------------------------
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
