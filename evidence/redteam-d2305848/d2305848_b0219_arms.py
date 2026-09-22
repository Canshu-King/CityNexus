"""红队三臂：用 B 未用过的形状打 ORD-0219 的九条门（tree17 = 4d9ceae）。

不改任何产品码、不改 B 的门；本脚本是只读探针。
  A1 洗白载荷的其它形状（字符串/嵌套/大小写/整数/step_free/evidence_status 组合）
  A1e 端到端 tags 通道（需临时改 fixture，见 run_a1e.py）
  A2 HARD 咬合面：两个 HARD 同时 / 两个冲突地点
  A3 生成期持久化：查库里的 PlanVersion/Activity 行（B 的门只读响应）
用法：D:/moodle/CityNexus/.venv/Scripts/python.exe raw/d2305848_b0219_arms.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(os.environ.get("REDTEAM_TREE", str(HERE.parent / "tree17"))).resolve()
BACKEND = TREE / "backend"
OUT = HERE / ("d2305848_b0219_arms_" + (sys.argv[1] if len(sys.argv)>1 else "all") + ".json")
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.capabilities import accessibility_state, evaluate_accessibility_requirement, extract_capabilities_from_text  # noqa: E402
from app.db.models import Activity, Journey, PlanVersion, Place  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.replanning.feasibility import _accessibility_metadata  # noqa: E402
from app.services import _demo_accessibility_evidence, _templates, seed_demo  # noqa: E402

client = TestClient(app)
DEMO_CITY = "CNX-DEMO"
FACT_KEYS = ("stroller_accessible", "luggage_accessible")
HARD_SENTENCES = {
    "STROLLER": "我们带婴儿车，这是必须的。",
    "LARGE_LUGGAGE": "我们拉一个大箱子，这是必须的。",
}
NAMED_BLOCKER = {"STROLLER": "STROLLER_ACCESS_UNAVAILABLE", "LARGE_LUGGAGE": "LUGGAGE_ACCESS_UNAVAILABLE"}

report: dict = {"tree": str(TREE), "arms": {}}


# ---------------------------------------------------------------- A1 shapes
def arm1() -> dict:
    """每个形状：喂给生产者，报 projected / verdicts。穿透 = 投影里出现白名单外的键，或求值出 VERIFIED。"""
    shapes = {
        "bool_true_baseline": {"stroller_accessible": True},
        "string_true": {"stroller_accessible": "true"},
        "string_TRUE_upper": {"stroller_accessible": "TRUE"},
        "int_one": {"stroller_accessible": 1},
        "nested_value": {"stroller_accessible": {"value": True}},
        "step_free_bool": {"stroller_accessible": True, "step_free": True, "evidence_status": "VERIFIED"},
        "step_free_string": {"stroller_accessible": True, "step_free": "true", "evidence_status": "VERIFIED"},
        "evidence_status_only": {"stroller_accessible": True, "evidence_status": "VERIFIED"},
        "step_free_verified": {"stroller_accessible": True, "step_free_verified": True},
        "route_step_free": {"stroller_accessible": True, "route_step_free": True, "evidence_status": "VERIFIED"},
        "wheelchair_bool": {"stroller_accessible": True, "wheelchair": True, "evidence_status": "VERIFIED"},
        "osm_tags_nested": {"stroller_accessible": True, "osm_tags": {"step_free": True, "evidence_status": "VERIFIED"}},
        "tags_nested": {"stroller_accessible": True, "tags": {"step_free": True, "evidence_status": "VERIFIED"}},
        "subject_status": {"stroller_accessible": True, "subject": "step_free", "status": "VERIFIED"},
    }
    rows = []
    for name, claimed in shapes.items():
        item = {"id": "place-synthetic", "accessibility": claimed}
        projected = _demo_accessibility_evidence(item)
        verdicts = {}
        if projected:
            verdicts = {
                "accessibility_state": accessibility_state(projected),
                "STEP_FREE_REQUIRED": evaluate_accessibility_requirement("STEP_FREE_REQUIRED", projected),
            }
        leaked_keys = [k for k in (projected or {}) if k not in FACT_KEYS + ("source_kind", "source")]
        pierced = bool(leaked_keys) or ("ACCESSIBILITY_VERIFIED" in verdicts.values())
        rows.append({"shape": name, "projected": projected, "verdicts": verdicts,
                     "leaked_keys": leaked_keys, "pierced": pierced})
    return {"shapes": rows, "any_pierced": any(r["pierced"] for r in rows)}


# ---------------------------------------------------------------- A1e tags channel (end-to-end, needs fixture edit)
def arm1e() -> dict:
    """消费侧是否从 tags/osm_tags 读：直接构造一条 Place 行（绕过 seed），看 _accessibility_metadata 读数。"""
    with SessionLocal() as session:
        row = Place(
            id="rt-tags-probe", provider_key="mock", external_id="rt-tags-probe", city_code=DEMO_CITY,
            name="RT tags probe", category="attraction", latitude=39.0, longitude=117.0,
            opening_hours_json=json.dumps({"open": "09:00", "close": "18:00"}),
            tags_json=json.dumps({"step_free": "yes", "evidence_status": "VERIFIED", "wheelchair": "yes"}),
            metadata_json=json.dumps({"duration_min": 30, "cost_minor": 1000}),
            updated_at="2026-09-23T00:00:00+00:00",
        )
        session.add(row)
        session.commit()
        read = _accessibility_metadata(row)
        state = accessibility_state(read) if read else None
        sf = evaluate_accessibility_requirement("STEP_FREE_REQUIRED", read) if read else None
        session.delete(row)
        session.commit()
    pierced = bool(read) and (state == "ACCESSIBILITY_VERIFIED" or sf == "ACCESSIBILITY_VERIFIED")
    return {"metadata_read": read, "accessibility_state": state, "STEP_FREE_REQUIRED": sf, "pierced": pierced,
            "note": "tags_json 里的 step_free/evidence_status 是否被消费侧读到"}


# ---------------------------------------------------------------- A2 two HARD / two conflicting stops
def _seed():
    with SessionLocal() as session:
        seed_demo(session)
        journey = session.execute(select(Journey)).scalars().first()
    return journey.id, journey.traveler_id


def _evidence(place_id: str) -> dict:
    with SessionLocal() as session:
        row = session.get(Place, place_id)
    return _accessibility_metadata(row) or {} if row else {}


def _templates_public():
    return _templates()


def arm2() -> dict:
    journey_id, traveler_id = _seed()
    # 修正：B 的真实形状是先 generate（无约束）拿候选，再 confirm —— 这样候选里才有冲突地点
    g = client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={})
    plans0 = g.json() if isinstance(g.json(), list) else (g.json() or {}).get("plans") or []
    plan_ids = [str(p.get("id") or p.get("plan_version_id")) for p in plans0]
    items = []
    for code in ("STROLLER", "LARGE_LUGGAGE"):
        for item in extract_capabilities_from_text(HARD_SENTENCES[code], scope="TRAVELER"):
            items.append({**dict(item), "confirmed": True})
    r = client.post(f"/api/v1/travelers/{traveler_id}/capabilities/confirm", json=items)
    conf = {"status": r.status_code, "codes": sorted({i.get("code") for i in items})}
    selects = []
    for pid in plan_ids:
        with SessionLocal() as session:
            acts = session.query(Activity).filter(Activity.plan_version_id == pid).all()
        stops = [str(a.place_id) for a in acts if a.place_id]
        sf_conf = [s for s in stops if _evidence(s).get("stroller_accessible") is False]
        lg_conf = [s for s in stops if _evidence(s).get("luggage_accessible") is False]
        resp = client.post(f"/api/v1/journeys/{journey_id}/plans/{pid}/select", json={})
        body = resp.text
        selects.append({
            "plan": pid, "status": resp.status_code,
            "stroller_conflicts": sf_conf, "luggage_conflicts": lg_conf,
            "names_stroller": "STROLLER_ACCESS_UNAVAILABLE" in body,
            "names_luggage": "LUGGAGE_ACCESS_UNAVAILABLE" in body,
            "mentions_each_conflict": [s for s in sf_conf + lg_conf if s in body],
            "body_head": body[:220],
        })
    return {"confirm": conf, "plan_count": len(plan_ids), "selects": selects,
            "both_hard_confirmed": conf["codes"] == ["LARGE_LUGGAGE", "STROLLER"]}


# ---------------------------------------------------------------- A3 persisted rows
def arm3() -> dict:
    journey_id, traveler_id = _seed()
    items = [{**dict(i), "confirmed": True}
             for i in extract_capabilities_from_text(HARD_SENTENCES["STROLLER"], scope="TRAVELER")]
    client.post(f"/api/v1/travelers/{traveler_id}/capabilities/confirm", json=items)
    g = client.post(f"/api/v1/journeys/{journey_id}/plans/generate", json={})
    plans = g.json() if isinstance(g.json(), list) else (g.json() or {}).get("plans") or []
    returned = {str(p.get("id") or p.get("plan_version_id")) for p in plans}
    # 库里所有 PlanVersion 行（不只是响应里的）
    with SessionLocal() as session:
        rows = session.query(PlanVersion).filter(PlanVersion.journey_id == journey_id).all()
        persisted = []
        for row in rows:
            acts = session.query(Activity).filter(Activity.plan_version_id == row.id).all()
            stops = [str(a.place_id) for a in acts if a.place_id]
            conf = [s for s in stops if _evidence(s).get("stroller_accessible") is False]
            persisted.append({"plan": row.id, "status": row.status, "version_no": row.version_no,
                              "in_response": row.id in returned, "stroller_conflicts": conf})
    return {"response_plan_ids": sorted(returned), "persisted_rows": persisted,
            "persisted_but_not_returned": [p for p in persisted if not p["in_response"]],
            "persisted_conflicting": [p for p in persisted if p["stroller_conflicts"]]}


def main() -> int:
    arm = sys.argv[1] if len(sys.argv) > 1 else "all"
    if arm in ("all", "a1"):
        report["arms"]["A1_shapes"] = arm1()
        print("A1 any_pierced:", report["arms"]["A1_shapes"]["any_pierced"])
    if arm in ("all", "a1e"):
        report["arms"]["A1e_tags_channel"] = arm1e()
        print("A1e pierced:", report["arms"]["A1e_tags_channel"]["pierced"])
    if arm in ("all", "a2"):
        report["arms"]["A2_two_hard"] = arm2()
        print("A2:", json.dumps(report["arms"]["A2_two_hard"], ensure_ascii=False)[:600])
    if arm in ("all", "a3"):
        report["arms"]["A3_persisted"] = arm3()
        print("A3:", json.dumps(report["arms"]["A3_persisted"], ensure_ascii=False)[:700])
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
