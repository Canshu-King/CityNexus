"""ORD-0219 ②③④ · 封存演示的无障碍证据生产者，走正常 Place -> evidence -> feasibility 消费链。

为什么要有这个文件：解析器补上 severity 之后（`5730004`），门确实会读 `stroller_accessible` /
`luggage_accessible`，但**没有任何生产者写过这两个键**——实测 `seed_demo` 灌出的 16 个地点里带无障碍
证据的 = 0/16（HARNESS `EXP-008` 追加，我在本树自己的临时库里复算同为 0）。证据永远读到 None，
就既不挡也不放。本文件把生产者钉进产品路径，并要求**删除/翻转 demo 证据字段 ⇒ 这里有节点变红**
（仲裁 `5778570154` 第 5 步）。

冻结边界（仲裁原文）在下面的节点里逐条可测：
* 只覆盖 sealed/demo-owned 地点（`CNX-DEMO`）；非封存城市 0 命中；
* provenance 由服务端代码盖章（`source_kind=DEMO`），fixture 里的任何字段都无法把它变成 provider truth；
* 消费走正常读取路径（`app.replanning.feasibility` 认的那个 metadata 形状），feasibility 里没有 demo 特例；
* 缺证据 = UNKNOWN，不许默认成 accessible。

期望值一律**算出来**：冲突地点来自 fixture 与 DB 行的实际读数，候选数来自 `_templates()` 的实际内容，
不写死数字，也不写死 "PASS"。
"""

import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.capabilities import (
    accessibility_state,
    evaluate_accessibility_requirement,
    extract_capabilities_from_text,
)
from app.db.models import Activity, Journey, Place
from app.db.session import SessionLocal
from app.integrations.mock.providers import MockCityDataProvider
from app.main import app
from app.replanning.feasibility import _accessibility_metadata
from app.services import _demo_accessibility_evidence, _templates, seed_demo

client = TestClient(app)

DEMO_CITY = "CNX-DEMO"
FACT_KEYS = ("stroller_accessible", "luggage_accessible")
HARD_SENTENCES = {
    "STROLLER": "我们带婴儿车，这是必须的。",
    "LARGE_LUGGAGE": "我们拉一个大箱子，这是必须的。",
}
NAMED_BLOCKER = {
    "STROLLER": "STROLLER_ACCESS_UNAVAILABLE",
    "LARGE_LUGGAGE": "LUGGAGE_ACCESS_UNAVAILABLE",
}


def _fixture_claims() -> dict[str, dict[str, bool]]:
    """What the deterministic demo fixture asserts, read from the fixture itself."""

    claims: dict[str, dict[str, bool]] = {}
    for item in MockCityDataProvider().places():
        claimed = item.get("accessibility") or {}
        facts = {
            key: claimed[key]
            for key in FACT_KEYS
            if isinstance(claimed.get(key), bool)
        }
        if facts:
            claims[item["id"]] = facts
    return claims


def _seed() -> tuple[str, str]:
    """Bootstrap through the product's own demo seed (never the shared reset route)."""

    with SessionLocal() as session:
        seed_demo(session)
        journey = session.execute(select(Journey)).scalars().first()
    assert journey is not None, "SETUP 失败：seed_demo 之后库里没有 journey"
    assert journey.city_code == DEMO_CITY, (
        f"SETUP：本门的舞台是封存演示城 {DEMO_CITY}，实际 {journey.city_code}"
    )
    return journey.id, journey.traveler_id


def _evidence(place_id: str) -> dict:
    with SessionLocal() as session:
        row = session.get(Place, place_id)
    assert row is not None, f"封存演示地点 {place_id} 不在库里"
    assert row.city_code == DEMO_CITY, f"{place_id} 不属于封存城市 {DEMO_CITY}"
    return _accessibility_metadata(row) or {}


def _plan_stops(plan_id: str) -> list[str]:
    with SessionLocal() as session:
        rows = (
            session.query(Activity)
            .filter(Activity.plan_version_id == plan_id)
            .order_by(Activity.sequence_no)
            .all()
        )
    return [str(row.place_id) for row in rows if row.place_id]


def _conflicting_stops(plan_id: str, fact_key: str) -> list[str]:
    """The stops this plan actually visits whose demo evidence says False."""

    return [
        place_id
        for place_id in _plan_stops(plan_id)
        if _evidence(place_id).get(fact_key) is False
    ]


def _fact_key_for(code: str) -> str:
    return {"STROLLER": "stroller_accessible", "LARGE_LUGGAGE": "luggage_accessible"}[code]


def _generate() -> list[str]:
    response = client.post("/api/v1/journeys/%s/plans/generate" % _JOURNEY, json={})
    assert response.status_code == 201, f"plans/generate 期望 201，实际 {response.status_code} {response.text[:200]}"
    body = response.json()
    entries = body if isinstance(body, list) else (body.get("plans") or [])
    return [str(entry.get("id") or entry.get("plan_version_id")) for entry in entries]


def _confirm_capability(code: str) -> list[dict]:
    """State the requirement the way the product hears it: natural language, then /confirm."""

    items = [
        {**dict(item), "confirmed": True}
        for item in extract_capabilities_from_text(HARD_SENTENCES[code], scope="TRAVELER")
    ]
    assert {item.get("code") for item in items} >= {code}, (
        f"解析器没把「{HARD_SENTENCES[code]}」读成 {code}，实际 {items}"
    )
    assert all(item.get("severity") == "HARD" for item in items), (
        f"硬性措辞被降级，实际 severity={[i.get('severity') for i in items]}（期望全部 HARD）"
    )
    response = client.post(
        "/api/v1/travelers/%s/capabilities/confirm" % _TRAVELER, json=items
    )
    assert response.status_code == 200, f"capabilities/confirm 实际 {response.status_code} {response.text[:200]}"
    return items


def _select(plan_id: str):
    return client.post("/api/v1/journeys/%s/plans/%s/select" % (_JOURNEY, plan_id), json={})


_JOURNEY, _TRAVELER = _seed()


# ------------------------------------------------------------------------------------------
# 生产者本身：证据落到库里、provenance 由代码盖章、且只落在封存城市
# ------------------------------------------------------------------------------------------
def test_demo_producer_lands_every_claimed_fact_with_demo_provenance():
    claims = _fixture_claims()
    assert claims, (
        "demo fixture 一个无障碍事实都没有声明 ⇒ 生产者无米下锅，这条门就是空的（先修 fixture）"
    )
    for place_id, facts in claims.items():
        evidence = _evidence(place_id)
        for key, value in facts.items():
            assert evidence.get(key) is value, (
                f"{place_id}.{key} 期望 fixture 声明的 {value}，库里读到 {evidence.get(key)!r}"
            )
        assert evidence.get("source_kind") == "DEMO", (
            f"{place_id} 的无障碍证据没有 DEMO 出处标记，实际 {evidence.get('source_kind')!r}"
        )
        assert "live" not in json.dumps(evidence).lower(), (
            f"{place_id} 的证据里出现了 live/provider 字样：{evidence}"
        )
        assert "evidence_status" not in evidence, (
            f"{place_id} 带着全局 evidence_status，会把 STEP_FREE 一族一起判掉：{evidence}"
        )


def test_demo_producer_reaches_exactly_the_places_the_fixture_claims():
    claims = set(_fixture_claims())
    with SessionLocal() as session:
        rows = session.query(Place).all()
    carrying = {
        row.id
        for row in rows
        if isinstance(json.loads(row.metadata_json or "{}").get("accessibility_evidence"), dict)
    }
    assert carrying == claims, (
        f"带证据的地点集合必须等于 fixture 声明的集合：库里 {sorted(carrying)} vs fixture {sorted(claims)}"
    )


def test_demo_evidence_stays_out_of_non_sealed_cities():
    with SessionLocal() as session:
        others = session.query(Place).filter(Place.city_code != DEMO_CITY).all()
    assert others, "库里没有非封存城市地点，这条负例就成了空断言"
    leaked = [
        row.id
        for row in others
        if "accessibility_evidence" in json.loads(row.metadata_json or "{}")
    ]
    assert not leaked, f"demo 无障碍证据泄进了非封存城市：{leaked}"


def test_missing_demo_evidence_is_unknown_and_never_implicit_access():
    claims = set(_fixture_claims())
    with SessionLocal() as session:
        untouched = [
            row for row in session.query(Place).filter(Place.city_code == DEMO_CITY).all()
            if row.id not in claims
        ]
    assert untouched, f"{DEMO_CITY} 每个地点都有证据了，UNKNOWN 这一格就无法演示"
    for row in untouched:
        evidence = _accessibility_metadata(row) or {}
        for key in FACT_KEYS:
            assert key not in evidence, (
                f"{row.id} 没被 fixture 声明却有 {key}={evidence.get(key)!r}：缺证据不能变成事实"
            )


def test_demo_producer_refuses_non_boolean_and_provenance_keys_from_the_fixture():
    """生产者只搬运白名单布尔值：出处由代码盖章，改 JSON 改不出 provider truth。"""

    projected = _demo_accessibility_evidence(
        {
            "id": "place-synthetic",
            "accessibility": {
                "stroller_accessible": True,
                "luggage_accessible": "no",       # 非布尔：不搬运
                "evidence_status": "VERIFIED",    # 全局裁决：不搬运
                "source_kind": "LIVE_PROVIDER_CAPTURE",  # 伪造出处：由代码覆盖
                "wheelchair": True,               # 白名单外：不搬运
            },
        }
    )
    assert projected == {
        "stroller_accessible": True,
        "source_kind": "DEMO",
        "source": "data/mock/places.json#place-synthetic",
    }, f"生产者搬运了不该搬的东西，实际 {projected}"


def test_a_single_stroller_fact_never_launderes_the_record_into_step_free_verified():
    """C 的移植件①（仲裁 00:44）：单点婴儿车事实绝不能把整条记录说成"无台阶已验证"。

    这条只管求值，不管键列表（那是上一条的归属），这样"白名单被放宽"能指名到它自己。
    """

    hostile = {
        "id": "place-synthetic",
        "accessibility": {
            "stroller_accessible": True,
            "step_free": True,
            "evidence_status": "VERIFIED",
            "source_kind": "LIVE_PROVIDER_CAPTURE",
        },
    }
    projected = _demo_accessibility_evidence(hostile) or {}
    verdicts = {
        "accessibility_state": accessibility_state(projected),
        "STEP_FREE_REQUIRED": evaluate_accessibility_requirement("STEP_FREE_REQUIRED", projected),
    }
    assert "ACCESSIBILITY_VERIFIED" not in verdicts.values(), (
        f"单点婴儿车事实把整条记录洗成已验证：{projected} -> {verdicts}"
    )
    # 正控：这些键一旦真的穿过，读取链就会量出 VERIFIED——所以上面那条不是永真断言。
    crossed = {key: value for key, value in hostile["accessibility"].items() if key != "source_kind"}
    assert evaluate_accessibility_requirement("STEP_FREE_REQUIRED", crossed) == "ACCESSIBILITY_VERIFIED", (
        f"正控失效（读取链根本量不出 VERIFIED），这条 tripwire 就成了永真：{crossed}"
    )


# ------------------------------------------------------------------------------------------
# 消费链：真实封存 demo journey，两向都测
# ------------------------------------------------------------------------------------------
def _two_way(code: str) -> None:
    fact_key = _fact_key_for(code)
    _seed()
    plans = _generate()
    assert plans, "没有任何候选方案，两向门成了空断言"
    _confirm_capability(code)
    blocked_expected = {
        plan_id: _conflicting_stops(plan_id, fact_key) for plan_id in plans
    }
    assert any(blocked_expected.values()), (
        f"三个候选里没有一个含 {fact_key}=False 的地点 ⇒ 负例不存在，门是空的"
    )
    assert any(not stops for stops in blocked_expected.values()), (
        f"每个候选都含冲突地点 ⇒ 正例不存在，门会误伤整趟"
    )
    for plan_id, stops in blocked_expected.items():
        response = _select(plan_id)
        if stops:
            expected = "%s:%s" % (NAMED_BLOCKER[code], stops[0])
            assert response.status_code == 422, (
                f"{plan_id} 含冲突证据 {stops}，期望 422 具名阻塞，实际 {response.status_code} {response.text[:160]}"
            )
            assert expected in response.text, (
                f"{plan_id} 期望响应里点名 {expected}，实际 {response.text[:200]}"
            )
        else:
            assert response.status_code == 200, (
                f"{plan_id} 全部地点满足或未知（{fact_key} 无 False），却被挡：{response.status_code} {response.text[:200]}"
            )


def test_hard_stroller_names_the_blocker_and_does_not_misfire():
    """负证据 ⇒ STROLLER_ACCESS_UNAVAILABLE:<地点>；正/无证据 ⇒ 200，不误伤。"""

    _two_way("STROLLER")


def test_hard_luggage_names_the_blocker_and_does_not_misfire():
    """同上，行李码走 `LUGGAGE_ACCESS_UNAVAILABLE`（六码里只有这两码在门名单内）。"""

    _two_way("LARGE_LUGGAGE")


def test_generation_never_persists_a_candidate_that_conflicts_with_a_hard_capability():
    """约束先落在文件上时，权威门在落库之前就把它看得懂的候选筛掉（feasibility 里没有 demo 特例）。"""

    code = "STROLLER"
    fact_key = _fact_key_for(code)
    _seed()
    _confirm_capability(code)
    plans = _generate()
    assert plans, "带硬性婴儿车要求时一个候选都没有 ⇒ 整趟不可规划，正是 HARNESS 警告的形状"
    clean_templates = [
        template
        for template in _templates()
        if not any(_evidence(place_id).get(fact_key) is False for place_id, *_ in template)
    ]
    conflicting_templates = [
        template for template in _templates() if template not in clean_templates
    ]
    assert conflicting_templates and clean_templates, (
        f"这条门要求生成阶段真的筛掉过东西：无冲突模板 {len(conflicting_templates)} 个 / "
        f"有冲突模板 {len(clean_templates)} 个 ⇒ 一边为空就是空断言"
    )
    conflicting = [plan_id for plan_id in plans if _conflicting_stops(plan_id, fact_key)]
    assert not conflicting, (
        f"这些候选含 {fact_key}=False 的地点却被生成出来了：{conflicting}"
    )
    assert len(plans) == len(clean_templates), (
        f"候选数应等于无冲突模板数：实际 {len(plans)} vs 期望 {len(clean_templates)}"
    )


# ------------------------------------------------------------------------------------------
# SILENT_CANDIDATE_LOSS 的 API 半边：被筛掉的候选必须留下具名持久事实，且从"前端已经在调"的读取面能拿到
# ------------------------------------------------------------------------------------------
def _rejection_events() -> list[dict]:
    """读 `GET /journeys/{id}/agent-feed`（前端 citynexus.ts:857 调的就是它）。"""

    feed = client.get("/api/v1/journeys/%s/agent-feed" % _JOURNEY, params={"limit": 200})
    assert feed.status_code == 200, f"agent-feed 实际 {feed.status_code} {feed.text[:200]}"
    body = feed.json()
    events = body if isinstance(body, list) else (body.get("events") or body.get("items") or [])
    assert isinstance(events, list), f"agent-feed 形状不认识：{str(body)[:200]}"
    return [
        event for event in events
        if isinstance(event, dict) and event.get("event_type") == "plans.candidate_rejected"
    ]


def test_a_dropped_candidate_leaves_a_named_fact_on_a_route_the_frontend_already_calls():
    """两向：断言在档 ⇒ 被丢的候选留下具名事实；什么都没断言 ⇒ 一个具名事实都不许出现。"""

    _seed()
    plain = client.post("/api/v1/journeys/%s/plans/generate" % _JOURNEY, json={})
    assert plain.status_code == 201, f"无断言时生成期望 201，实际 {plain.status_code} {plain.text[:200]}"
    assert len(plain.json()) == len(_templates()), "无断言就不该少候选"
    assert _rejection_events() == [], (
        f"什么都没冲突却写出了具名拒绝事实：{_rejection_events()}"
    )

    _seed()
    _confirm_capability("STROLLER")
    generated = client.post("/api/v1/journeys/%s/plans/generate" % _JOURNEY, json={})
    assert generated.status_code == 201, f"带硬性婴儿车要求仍要能出可用方案（不许抛错）：{generated.status_code} {generated.text[:200]}"
    kept = generated.json()
    assert len(kept) < len(_templates()), (
        f"本单要的就是「有候选被筛掉」这一格：{len(kept)} vs {len(_templates())}"
    )
    events = _rejection_events()
    assert len(events) == len(_templates()) - len(kept), (
        f"被丢几个候选就该有几条具名事实：{len(events)} vs 期望 {len(_templates()) - len(kept)}"
    )
    for event in events:
        facts = event.get("facts") or {}
        assert "CANDIDATE_REJECTED_BY_FEASIBILITY_GATE" in (facts.get("reason_codes") or []), (
            f"具名事实没有可寻址的 reason code：{facts}"
        )
        assert facts.get("failures"), f"具名事实里一个门自己叫出的失败名都没有：{facts}"
        assert "STROLLER" in (facts.get("hard_rule_codes") or []), (
            f"在档的硬性规则没进事实：{facts.get('hard_rule_codes')}"
        )


def test_the_named_reason_points_at_the_stop_whose_demo_evidence_conflicted():
    """事实里点名的地点必须就是「该候选自己的 stop 且证据为 False」那个——不许写死。"""

    fact_key = _fact_key_for("STROLLER")
    _seed()
    _confirm_capability("STROLLER")
    generated = client.post("/api/v1/journeys/%s/plans/generate" % _JOURNEY, json={})
    assert generated.status_code == 201, f"SETUP：生成实际 {generated.status_code}"
    events = _rejection_events()
    assert events, "没有任何具名拒绝事实，这条归因就成了空断言"
    for event in events:
        facts = event.get("facts") or {}
        stops = [str(place_id) for place_id in (facts.get("stops") or [])]
        assert stops, f"事实里没留下候选自己的地点清单：{facts}"
        blocking = [place_id for place_id in stops if _evidence(place_id).get(fact_key) is False]
        assert blocking, (
            f"这个被丢的候选里没有一个地点的 {fact_key} 是 False，那它凭什么被丢：{stops} -> {facts.get('failures')}"
        )
        for code in facts.get("hard_rule_codes") or []:
            if code != "STROLLER":
                continue
            named = [
                failure for failure in (facts.get("failures") or [])
                if any(place_id in str(failure) for place_id in blocking)
            ]
            assert named, (
                f"事实点名的冲突地点与实际证据不符：期望提到 {blocking} 之一，实际 {facts.get('failures')}"
            )
