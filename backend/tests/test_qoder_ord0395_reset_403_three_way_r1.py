"""ORD-0395: code, `contracts/openapi.yaml` and the served `/openapi.json` must say the same thing
about one failure input -- `POST /api/v1/demo/reset` presented without the operator's token.

Measured at the authoritative tip, before this file existed:

* the door answers `403` with three distinct codes -- `DEMO_MODE_REQUIRED` (flag off, measured with
  `CITYNEXUS_DEMO_MODE` absent from the process environment), `RESET_TOKEN_REQUIRED` (no header),
  `RESET_TOKEN_INVALID` (a header that is not the operator's, which is also what a deployment with no
  configured token answers to every header);
* `contracts/openapi.yaml` enumerated all three;
* the served document named only two, because the decorator's `responses` block was written by hand.

That last gap is the one this order is about: the app-wide parity door
(`backend/tests/test_contract.py`) compares path x method, so a refusal missing from the decorator
leaves every other gate green while a consumer of the generated document cannot see the answer.
These arms read all three surfaces for the same input and require one claim, and they keep the arm
that presents the right token answering `200` -- a document that agrees because the door was widened
is not a fix.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Activity, Journey, PlanVersion, Traveler
from app.db.session import SessionLocal
from app.main import (
    DEMO_RESET_ENV,
    DEMO_RESET_HEADER,
    DEMO_RESET_REFUSALS,
    app,
)

CONTRACT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.yaml"
DOOR = "/api/v1/demo/reset"
CONTRACT_DOOR = "/demo/reset"
RIGHT = "ord0395-arm-token"
CODE_NAME = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")

client = TestClient(app)


@pytest.fixture()
def _stage_with_token(monkeypatch) -> None:
    """A deployment that is a stage and has configured the token, so the token arms answer."""

    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: True)
    monkeypatch.setenv(DEMO_RESET_ENV, RIGHT)


def _served() -> dict:
    response = client.get("/openapi.json")
    assert response.status_code == 200, response.text
    return response.json()["paths"][DOOR]["post"]


def _contract_door() -> dict:
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return spec["paths"][CONTRACT_DOOR]["post"]


def _refusal_schema_part(door: dict) -> dict:
    schema = door["responses"]["403"]["content"]["application/json"]["schema"]
    parts = [part for part in schema["allOf"] if "properties" in part]
    assert len(parts) == 1, schema["allOf"]
    return parts[0]


def _contract_refusal_codes(door: dict) -> set[str]:
    """The `error.code` enum the hand contract puts on the 403."""

    code = _refusal_schema_part(door)["properties"]["error"]["properties"]["code"]
    return set(code["enum"])


def _served_refusal_codes(served: dict) -> set[str]:
    return set(CODE_NAME.findall(served["responses"]["403"]["description"]))


def _counts() -> dict[str, int]:
    with SessionLocal() as session:
        return {
            "travelers": session.scalar(select(func.count(Traveler.id))) or 0,
            "journeys": session.scalar(select(func.count(Journey.id))) or 0,
            "plan_versions": session.scalar(select(func.count(PlanVersion.id))) or 0,
            "activities": session.scalar(select(func.count(Activity.id))) or 0,
        }


def test_the_two_openapi_documents_name_the_same_refusals() -> None:
    """One status, the same code names, in both artifacts, checked in both directions."""

    served, door = _served(), _contract_door()
    contract_statuses = {code for code in door["responses"] if code.isdigit()}
    assert contract_statuses == set(door["responses"]), door["responses"].keys()
    missing = contract_statuses - set(served["responses"])
    assert not missing, f"a refusal the hand contract declares is absent from /openapi.json: {missing}"

    from_contract, from_served = _contract_refusal_codes(door), _served_refusal_codes(served)
    assert from_contract == from_served, (
        "the two documents disagree about which codes the 403 carries; "
        f"contract-only={sorted(from_contract - from_served)} "
        f"served-only={sorted(from_served - from_contract)}"
    )
    assert from_contract == set(DEMO_RESET_REFUSALS), DEMO_RESET_REFUSALS


def test_every_code_the_served_document_names_is_one_the_door_answers(monkeypatch) -> None:
    """No dead declaration and no undeclared answer: the two sets are the same set."""

    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: True)
    monkeypatch.setenv(DEMO_RESET_ENV, RIGHT)

    answered: dict[str, int] = {}
    for headers in (None, {DEMO_RESET_HEADER: "not-the-operator"}):
        response = client.post(DOOR, headers=headers)
        answered[response.json()["error"]["code"]] = response.status_code
    monkeypatch.setattr("app.main.demo_mode_enabled", lambda: False)
    response = client.post(DOOR, headers={DEMO_RESET_HEADER: RIGHT})
    answered[response.json()["error"]["code"]] = response.status_code

    assert set(answered) == _served_refusal_codes(_served()), (
        f"the door answers {sorted(answered)} but the served document names "
        f"{sorted(_served_refusal_codes(_served()))}"
    )


def test_the_same_failure_input_gives_all_three_surfaces_the_same_answer(
    _stage_with_token,
) -> None:
    """The order's judgement: one input, one claim from each surface, and nothing deleted."""

    assert client.post(DOOR, headers={DEMO_RESET_HEADER: RIGHT}).status_code == 200
    before = _counts()
    assert before["journeys"] > 0, "the arm is vacuous unless a journey exists to lose"

    refused = client.post(DOOR)
    body = refused.json()["error"]
    served, door = _served(), _contract_door()

    assert refused.status_code == 403, refused.text
    assert "403" in served["responses"], served["responses"].keys()
    assert "403" in door["responses"], door["responses"].keys()
    assert body["code"] == "RESET_TOKEN_REQUIRED", body
    assert body["code"] in _contract_refusal_codes(door), body
    assert body["code"] in _served_refusal_codes(served), body
    assert body["details"]["tables_protected"] is True, body

    details = _refusal_schema_part(door)["properties"]["error"]["properties"]["details"]
    assert details["required"] == ["tables_protected"], details
    assert details["properties"]["tables_protected"] == {"type": "boolean", "const": True}, details
    assert details["properties"]["header"] == {"type": "string", "const": DEMO_RESET_HEADER}, details

    assert _counts() == before, "a refused reset moved a row count"


def test_the_correct_token_arm_still_opens(_stage_with_token) -> None:
    """Counter-control: agreement bought by widening the door is not a fix."""

    served, door = _served(), _contract_door()
    accepted = client.post(DOOR, headers={DEMO_RESET_HEADER: RIGHT})

    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "reset", accepted.json()
    assert "200" in served["responses"], served["responses"].keys()
    assert "200" in door["responses"], door["responses"].keys()
    assert client.post(DOOR).status_code == 403, "the tokenless arm opened"


def test_both_documents_promise_the_same_header_claim() -> None:
    """The claim that opens the door is described identically by both artifacts."""

    served, door = _served(), _contract_door()
    spec = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    parameter = spec["components"]["parameters"]["DemoResetToken"]

    assert door["parameters"] == [{"$ref": "#/components/parameters/DemoResetToken"}], door[
        "parameters"
    ]
    assert parameter["name"] == DEMO_RESET_HEADER, parameter
    assert parameter["in"] == "header", parameter
    assert parameter["required"] is False, parameter

    declared = [item for item in served.get("parameters", []) if item["name"] == DEMO_RESET_HEADER]
    assert len(declared) == 1, served.get("parameters")
    assert declared[0]["in"] == "header", declared
    assert declared[0]["required"] is False, declared
