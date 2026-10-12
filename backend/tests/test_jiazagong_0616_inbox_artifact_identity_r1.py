"""ORD-0616 (加闸工): the inbox import door has to be able to say "this is the same artefact".

Before this wiring the audit trail recorded a status, the unresolved fields and an extraction mode,
and nothing identified *what* the traveller handed in.  Importing the same confirmation twice - the
case every traveller lives through when a paste goes wrong - produced two rows with no way to tell
they carry one statement.  The identity now comes from `app.journey_inbox`, which derives it from
the artefact's own content and never from a run id or a timestamp.

Every scenario walks the product's own endpoints: `POST /inbox/import` in, `GET /history` out, and
the assertion reads the value the traveller can actually fetch back.
"""

from __future__ import annotations

import os

for _key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "CITYNEXUS_AI_API_KEY"):
    os.environ.pop(_key, None)
os.environ.setdefault("CITYNEXUS_AI_ENABLED", "false")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.journey_inbox import inbox_artifact_fingerprint  # noqa: E402
from app.main import app  # noqa: E402
from demo_stage import demo_reset_headers  # noqa: E402

MESSAGE = (
    "RAIL confirmation code JZ0616-RAIL-77 \n"
    " departs 2026-10-10T08:00:00+08:00   arrives 2026-10-10T09:15:00+08:00"
)
OTHER_MESSAGE = MESSAGE.replace("JZ0616-RAIL-77", "JZ0616-RAIL-78")
RESERVATION = {
    "reservation_type": "RAIL",
    "confirmation_ref": "JZ0616-STRUCT-77",
    "origin": {"name": "Tianjin West Station"},
    "destination": {"name": "Tianjin Binhai Station"},
    "scheduled_departure_at": "2026-10-10T08:00:00+08:00",
    "scheduled_arrival_at": "2026-10-10T09:15:00+08:00",
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _journey(client: TestClient) -> str:
    answer = client.post("/api/v1/demo/reset", headers=demo_reset_headers())
    assert answer.status_code == 200, answer.text
    return answer.json()["journey_id"]


def _import(client: TestClient, journey_id: str, body: dict) -> dict:
    answer = client.post(
        f"/api/v1/journeys/{journey_id}/inbox/import", json=body
    )
    assert answer.status_code == 201, answer.text
    return answer.json()


def _imported_facts(client: TestClient, journey_id: str) -> list[dict]:
    """Every artefact the traveller has handed in, as the history door answers it."""
    answer = client.get(f"/api/v1/journeys/{journey_id}/history")
    assert answer.status_code == 200, answer.text
    rows = [
        item
        for item in answer.json()
        if item.get("entity_type") == "ExternalReservationDraft"
    ]
    assert rows, "the import left no artefact row in the traveller's history"
    return [item.get("facts") or {} for item in rows]


def test_0616_the_history_door_answers_with_the_modules_identity(client):
    """The value on the read path is the module's, computed from the text the traveller pasted."""
    journey_id = _journey(client)
    _import(client, journey_id, {"artifact_type": "TEXT", "payload": {"text": MESSAGE}})

    facts = _imported_facts(client, journey_id)[0]
    expected = inbox_artifact_fingerprint(source_kind="TEXT", normalized_text=MESSAGE)
    assert facts.get("artifact_fingerprint") == expected, (
        "history answered %r, the module computes %r for the same artefact"
        % (facts.get("artifact_fingerprint"), expected)
    )


def test_0616_a_second_paste_of_the_same_message_is_one_artefact(client):
    """Two imports of one statement share an identity even when the whitespace differs."""
    journey_id = _journey(client)
    _import(client, journey_id, {"artifact_type": "TEXT", "payload": {"text": MESSAGE}})
    _import(
        client,
        journey_id,
        {"artifact_type": "TEXT", "payload": {"text": "  ".join(MESSAGE.split())}},
    )

    facts = _imported_facts(client, journey_id)
    assert len(facts) == 2, "both imports have to stay visible as their own rows: %r" % facts
    first, second = facts[0]["artifact_fingerprint"], facts[1]["artifact_fingerprint"]
    assert first == second, (
        "the same message produced two identities: %s vs %s" % (first, second)
    )


def test_0616_a_different_message_is_a_different_artefact(client):
    """Replay-safety must not collapse into one constant hash."""
    journey_id = _journey(client)
    _import(client, journey_id, {"artifact_type": "TEXT", "payload": {"text": MESSAGE}})
    _import(client, journey_id, {"artifact_type": "TEXT", "payload": {"text": OTHER_MESSAGE}})

    facts = _imported_facts(client, journey_id)
    first, second = facts[0]["artifact_fingerprint"], facts[1]["artifact_fingerprint"]
    assert first != second, "two different messages shared one identity: %s" % first


def test_0616_structured_import_identity_covers_the_payload_not_the_run(client):
    """The structured door gets the same replay-safe identity from the same module."""
    journey_id = _journey(client)
    body = {"artifact_type": "STRUCTURED_JSON", "payload": {"reservation": RESERVATION}}
    _import(client, journey_id, body)
    _import(client, journey_id, body)

    facts = _imported_facts(client, journey_id)
    assert len(facts) == 2, facts
    assert facts[0]["artifact_fingerprint"] == facts[1]["artifact_fingerprint"], (
        "re-importing one structured reservation changed its identity: %s vs %s"
        % (facts[0]["artifact_fingerprint"], facts[1]["artifact_fingerprint"])
    )
