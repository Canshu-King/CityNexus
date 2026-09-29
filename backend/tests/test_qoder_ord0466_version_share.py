"""ORD-0466 - a share grant can be cut for one plan version, and the token reads that version.

Measured at the tip this slice was written against (`4efe7efb70ac4e08471da9bd5153f178348e4db9`): the
grant table carried `journey_id`, `token`, `visibility`, `created_by` and the two ending moments and
nothing else (`backend/app/db/models.py:1237`), so "share this trip" was the finest thing the store
could say about sharing; `plan_versions` (`backend/app/db/models.py:505`) had no share exit at all.
The preset design says journeys *and versions* are shareable, so the gap is a scope column, not a new
table and not a second token door.

What each arm holds the code to:

* V1 a journey-level grant keeps answering exactly what it answered before, plus `grant_scope` - the
  new key is additive, and an old row is a journey-level grant, not an unfinished choice;
* V2 a version-scoped grant reads that one version, and the plan it carries is the *same*
  `PlanVersion` shape `GET /journeys/{id}/plans` answers with - one shape, not a second one that can
  drift away from the owner's own view of the version;
* V3 the three ways a version id can be wrong are three named codes, and none of them mints a token
  (a grant born unopenable is the ORD-0460 defect repeating itself in another column);
* V4 the scope survives both read doors - the create answer and the list answer - because a grant
  whose scope only exists in the request that made it cannot be administered later;
* V5 when the version behind a live grant is gone, the token answers 409 with its own name rather
  than a 200 whose plan section is quietly absent;
* V6 the contract and the checked-in client both carry the new field and the new response keys, so
  the value is not something only the server knows about.

Every code this file names is prefixed `SHARE_GRANT_`, the rule ORD-0434 set so the words do not
collide with the agent-approval status enum.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.db.models import PlanVersion, Traveler
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts" / "openapi.yaml"
GENERATED = ROOT / "frontend/src/generated/api.ts"

GRANT_PATH = "/api/v1/journeys/{journey_id}/share-grants"
TOKEN_PATH = "/api/v1/shared/journeys/{token}"
TZ = timezone(timedelta(hours=8))
START = datetime(2026, 12, 3, 9, 0, tzinfo=TZ)


def _traveler() -> str:
    traveler_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            Traveler(
                id=traveler_id,
                display_name="ORD-0466 probe",
                email=None,
                locale="zh-CN",
                timezone="Asia/Shanghai",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    return traveler_id


def _journey() -> str:
    created = client.post(
        "/api/v1/journeys",
        json={
            "traveler_id": _traveler(),
            "title": "ORD-0466",
            "city_code": "CN-XIAMEN",
            "timezone": "Asia/Shanghai",
            "start_at": START.isoformat(),
            "end_at": (START + timedelta(days=2, hours=8)).isoformat(),
            "budget": {"amount_minor": 90000, "currency": "CNY"},
            "planning_mode": "balanced",
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _plan_version(journey_id: str, version_no: int = 1) -> str:
    """A version row, written the way the store holds it. No activity is needed: the grant is about
    which version a token opens, and an empty version is still a version."""
    plan_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.add(
            PlanVersion(
                id=plan_id,
                journey_id=journey_id,
                version_no=version_no,
                planning_mode="balanced",
                status="CANDIDATE",
                source="INITIAL",
                total_cost_minor=120000,
                currency="CNY",
                estimated_duration_min=480,
                created_at=now,
            )
        )
        session.commit()
    return plan_id


def _create(journey_id: str, plan_version_id: str | None = None) -> dict:
    body: dict = {"visibility": "LINK_READ", "created_by": "lane-newlane2"}
    if plan_version_id is not None:
        body["plan_version_id"] = plan_version_id
    response = client.post(GRANT_PATH.format(journey_id=journey_id), json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _reason(payload: dict) -> str:
    return str((payload.get("error") or {}).get("reason_code"))


def _grant_count(journey_id: str) -> int:
    response = client.get(GRANT_PATH.format(journey_id=journey_id))
    assert response.status_code == 200, response.text
    return len(response.json())


def test_v1_journey_level_grant_keeps_its_shape_and_names_its_scope() -> None:
    journey_id = _journey()
    grant = _create(journey_id)
    assert grant["plan_version_id"] is None, "a grant with no version sent must not carry one"

    read = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["grant_scope"] == "JOURNEY", body.get("grant_scope")
    assert "shared_plan" not in body, "a journey-level grant opened a plan it was never cut for"
    # the journey half of the body is still the same shape the owner's own read answers with
    owner = client.get(f"/api/v1/journeys/{journey_id}")
    assert owner.status_code == 200, owner.text
    shared_keys = set(body) - {"grant_scope"}
    assert shared_keys == set(owner.json()), sorted(shared_keys ^ set(owner.json()))


def test_v2_version_grant_reads_that_version_in_the_owners_own_shape() -> None:
    journey_id = _journey()
    plan_id = _plan_version(journey_id, version_no=3)
    grant = _create(journey_id, plan_id)
    assert grant["plan_version_id"] == plan_id

    read = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert read.status_code == 200, read.text
    body = read.json()
    assert body["grant_scope"] == "PLAN_VERSION"
    assert body["shared_plan"]["id"] == plan_id
    assert body["shared_plan"]["version_no"] == 3

    plans = client.get(f"/api/v1/journeys/{journey_id}/plans")
    assert plans.status_code == 200, plans.text
    owner_row = next(row for row in plans.json() if row["id"] == plan_id)
    assert set(body["shared_plan"]) == set(owner_row), sorted(
        set(body["shared_plan"]) ^ set(owner_row)
    )


def test_v3_three_ways_a_version_id_is_wrong_are_three_names_and_no_token() -> None:
    journey_id = _journey()
    other_journey = _journey()
    other_plan = _plan_version(other_journey)
    before = _grant_count(journey_id)

    malformed = client.post(
        GRANT_PATH.format(journey_id=journey_id),
        json={"visibility": "LINK_READ", "created_by": "x", "plan_version_id": "not-an-id"},
    )
    assert malformed.status_code == 422, malformed.text
    assert _reason(malformed.json()) == "SHARE_GRANT_VERSION_ID_UNREADABLE"

    unknown = client.post(
        GRANT_PATH.format(journey_id=journey_id),
        json={"visibility": "LINK_READ", "created_by": "x", "plan_version_id": str(uuid4())},
    )
    assert unknown.status_code == 422, unknown.text
    assert _reason(unknown.json()) == "SHARE_GRANT_VERSION_UNKNOWN"

    foreign = client.post(
        GRANT_PATH.format(journey_id=journey_id),
        json={"visibility": "LINK_READ", "created_by": "x", "plan_version_id": other_plan},
    )
    assert foreign.status_code == 409, foreign.text
    assert _reason(foreign.json()) == "SHARE_GRANT_VERSION_NOT_IN_JOURNEY"

    assert _grant_count(journey_id) == before, "a refused grant still minted a token"


def test_v4_scope_survives_the_list_door() -> None:
    journey_id = _journey()
    plan_id = _plan_version(journey_id)
    _create(journey_id, plan_id)
    listed = client.get(GRANT_PATH.format(journey_id=journey_id))
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert [row["plan_version_id"] for row in rows] == [plan_id]


def test_v5_a_grant_whose_version_is_gone_names_that_fact() -> None:
    journey_id = _journey()
    plan_id = _plan_version(journey_id)
    grant = _create(journey_id, plan_id)

    with SessionLocal() as session:
        row = session.get(PlanVersion, plan_id)
        session.delete(row)
        session.commit()

    read = client.get(TOKEN_PATH.format(token=grant["token"]))
    assert read.status_code == 409, read.text
    assert _reason(read.json()) == "SHARE_GRANT_VERSION_GONE"
    assert "shared_plan" not in read.json().get("error", {}), "the refusal leaked a plan body"


def test_v6_contract_and_checked_in_client_carry_the_scope() -> None:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    create = spec["components"]["schemas"]["ShareGrantCreate"]["properties"]
    grant = spec["components"]["schemas"]["ShareGrant"]["properties"]
    assert "plan_version_id" in create, sorted(create)
    assert "plan_version_id" in grant, sorted(grant)
    assert "plan_version_id" in spec["components"]["schemas"]["ShareGrant"]["required"]

    shared = spec["paths"]["/shared/journeys/{token}"]["get"]["responses"]["200"]
    schema = shared["content"]["application/json"]["schema"]
    assert schema["allOf"][1]["properties"]["grant_scope"]["enum"] == ["JOURNEY", "PLAN_VERSION"]
    assert (
        schema["allOf"][1]["properties"]["shared_plan"]["$ref"]
        == "#/components/schemas/PlanVersion"
    )

    generated = GENERATED.read_text(encoding="utf-8")
    assert "grant_scope" in generated, "the client cannot see the scope the server answers with"
    assert generated.count("plan_version_id") >= 2, "one of the two schemas never reached the client"
