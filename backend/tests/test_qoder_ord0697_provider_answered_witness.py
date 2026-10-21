"""ORD-0697 - the product gains a word for "the provider answered", and the hand that can say it.

Measured on the authoritative tip this branch starts from: nine real calls went out through the
configured gateway and every one came back 2xx (`cmdr_payload_sweep_1021ck.txt:1` onward), while the
server's own `/api/v1/agent/runtime-status` still answered `ai_state=CONFIGURED_UNVERIFIED` and named
no model (`cmdr_ai_state_proof_1021dd.txt:1`, `cmdr_ai_state_proof_1021dd.txt:2`).  The reason was in
the vocabulary, not in the configuration: `ai_availability.py` had a name for "refused" and none for
"answered" (`cmdr_ord0697_writeset_1021dt.txt:2`), and no production call site could pass either one
(`cmdr_ord0697_writeset_1021dt.txt:6`).

These arms are written so the shortcuts cannot pass:

* a witnessed answer moves the word, and "witnessed" means an arm that made the call - a key being
  present stays insufficient, so the ORD-0359 r2 mistake keeps its own negative control;
* precedence is pinned, including "answered once, credential since removed", where having no key now
  outranks having worked before;
* a refusal seen most recently outranks an earlier answer and the counters still disclose the answer,
  so ordering never deletes a fact;
* a no-argument call - the shape `runtime.unavailable_run_payload` uses when it writes a stored
  `failure_reason` - can never produce either witnessed word;
* the witness reaches the wire through the real doors (`/health`, `/agent/runtime-status`) driven by
  a mocked provider, so the wiring is under test and not only the table;
* and no credential string appears anywhere in any of it.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from app.agent import ai_availability as mod
from app.agent.ai_availability import (
    AI_CONFIGURED_UNVERIFIED,
    AI_DISABLED_BY_OPS,
    AI_NOT_CONFIGURED,
    AI_PROVIDER_ANSWERED,
    AI_PROVIDER_REFUSED,
    AI_STATES,
    OUTCOME_ANSWERED,
    OUTCOME_REFUSED,
    ai_availability_state,
    provider_witness,
    record_provider_answer,
    record_provider_refusal,
    witnessed_ai_state,
)
from app.agent.runtime_identity import runtime_status
from app.integrations.ai.responses import DeepSeekResponsesClient, DeepSeekResponsesError
from app.main import app

# A sentinel, deliberately not credential-shaped: the repo's own credential-literal gate
# (`test_qoder_ord0479_dictionary_key_shape.py`) reads an `sk-` string anywhere in the tree as a
# literal credential, and this arm's point is that the value never reaches an answer, not that a
# key-shaped string can hide in a test.
FAKE_KEY = "ord0697-sentinel-value-never-echoed"
ANSWER_ENVELOPE = {
    "id": "resp_ord0697",
    "output": [{"type": "message", "content": [{"type": "output_text", "text": "好的，方案已更新"}]}],
}

client = TestClient(app)


def _configure(monkeypatch, *, enabled: bool = True, key: str | None = FAKE_KEY) -> None:
    """Replace the settings object the producer reads, as the ORD-0359 arms do.

    `settings` is a frozen dataclass built from the environment at import time, so a single field
    cannot be patched; the producer keeps the object in its own namespace and every door reaches the
    word through that one module, which is what makes this replacement enough.
    """

    monkeypatch.setattr(
        mod,
        "settings",
        SimpleNamespace(
            ai_enabled=enabled, ai_api_key=key, hermes_api_url=None, hermes_api_key=None
        ),
        raising=False,
    )


def _provider(status_code: int, payload: dict) -> DeepSeekResponsesClient:
    """A Responses client answered by a mock, so no arm below leaves the machine."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return DeepSeekResponsesClient(
        api_key=FAKE_KEY, client=httpx.Client(transport=httpx.MockTransport(handler))
    )


# ------------------------------------------------------ R1 the word exists and only a witness can say it


def test_the_vocabulary_has_a_word_for_answered(monkeypatch) -> None:
    assert len(AI_STATES) == 5, AI_STATES
    assert len(set(AI_STATES)) == 5, AI_STATES
    assert AI_PROVIDER_ANSWERED in AI_STATES, AI_STATES

    _configure(monkeypatch)
    assert witnessed_ai_state() == AI_CONFIGURED_UNVERIFIED, witnessed_ai_state()

    record_provider_answer(
        provider_key="deepseek_responses", model_key="deepseek-v4-flash", status_code=200
    )
    assert witnessed_ai_state() == AI_PROVIDER_ANSWERED, witnessed_ai_state()


# ------------------------------ R2 a door that did not watch cannot name a witnessed fact


def test_a_door_that_did_not_watch_cannot_name_either_witnessed_word(monkeypatch) -> None:
    """`runtime.unavailable_run_payload` writes `reason_sentence(ai_availability_state())` into a run's
    `failure_reason`, so a run that never reached the provider must not be able to store "the
    provider answered" - or "the provider refused".  Both words stay unreachable without an
    argument, which is the difference this arm draws against the witnessed door.
    """

    _configure(monkeypatch)
    record_provider_answer(provider_key="deepseek_responses", model_key="m", status_code=200)

    assert ai_availability_state() == AI_CONFIGURED_UNVERIFIED, ai_availability_state()
    assert ai_availability_state() != AI_PROVIDER_ANSWERED
    assert ai_availability_state() != AI_PROVIDER_REFUSED
    assert witnessed_ai_state() == AI_PROVIDER_ANSWERED


# ------------------------------------- R3 precedence: a missing key outranks a past answer


def test_a_past_answer_never_outranks_a_credential_that_is_gone(monkeypatch) -> None:
    record_provider_answer(provider_key="deepseek_responses", model_key="m", status_code=200)

    _configure(monkeypatch, enabled=True, key=None)
    assert witnessed_ai_state() == AI_NOT_CONFIGURED, witnessed_ai_state()

    _configure(monkeypatch, enabled=False, key=FAKE_KEY)
    assert witnessed_ai_state() == AI_DISABLED_BY_OPS, witnessed_ai_state()


# ------------------------- R4 a later refusal wins, and the counters still disclose the answer


def test_a_refusal_after_an_answer_wins_and_still_discloses_the_answer(monkeypatch) -> None:
    _configure(monkeypatch)
    record_provider_answer(provider_key="deepseek_responses", model_key="m", status_code=200)
    record_provider_refusal(provider_key="deepseek_responses", model_key="m", status_code=429)

    assert witnessed_ai_state() == AI_PROVIDER_REFUSED, witnessed_ai_state()
    seen = provider_witness()
    assert seen is not None and seen.outcome == OUTCOME_REFUSED, seen
    assert seen.answers == 1 and seen.refusals == 1, seen


def test_the_counter_moves_on_every_witnessed_call(monkeypatch) -> None:
    _configure(monkeypatch)
    for _ in range(3):
        record_provider_answer(
            provider_key="deepseek_responses", model_key="m", status_code=200
        )
    seen = provider_witness()
    assert seen is not None and seen.answers == 3 and seen.refusals == 0, seen
    assert seen.outcome == OUTCOME_ANSWERED, seen


# ------------------------------------- R5 negative control: the r2 mistake stays impossible


def test_a_key_string_alone_still_proves_nothing(monkeypatch) -> None:
    """ORD-0359 r2 measured a deliberately fake key reported as `READY`.

    The new word must not become a second route to that mistake: key present, no witness, so the
    answer stays `CONFIGURED_UNVERIFIED` even though the sentence table now carries a success word.
    """

    _configure(monkeypatch, enabled=True, key="definitely-not-a-real-key")
    assert provider_witness() is None, provider_witness()
    assert witnessed_ai_state() == AI_CONFIGURED_UNVERIFIED, witnessed_ai_state()


# ------------------------------------------- R6 the wiring: a real call through the real door


def test_the_responses_door_witnesses_its_own_success(monkeypatch) -> None:
    """The arm that makes this a wiring change rather than a vocabulary edit.

    Driving `DeepSeekResponsesClient.complete()` with a mocked 2xx is what has to move the word,
    because that client is one of the two production doors that actually talk to the provider
    (`cmdr_ord0697_writeset_1021dt.txt:12`).  Before this order no production site could even report
    a refusal, so a name could sit in the table and never be said.
    """

    _configure(monkeypatch)
    provider = _provider(200, ANSWER_ENVELOPE)
    result = provider.complete([{"role": "user", "content": "北京三天怎么排"}])

    assert result.text.strip(), result
    seen = provider_witness()
    assert seen is not None and seen.outcome == OUTCOME_ANSWERED, seen
    assert seen.model_key == provider.model, (seen.model_key, provider.model)
    assert seen.status_code == 200, seen
    assert witnessed_ai_state() == AI_PROVIDER_ANSWERED


def test_the_responses_door_witnesses_a_refusal_and_names_no_secret(monkeypatch) -> None:
    _configure(monkeypatch)
    provider = _provider(402, {"error": {"code": "insufficient_balance"}})
    try:
        provider.complete([{"role": "user", "content": "北京三天怎么排"}])
    except DeepSeekResponsesError as exc:
        assert exc.status_code == 402, exc
        assert FAKE_KEY not in str(exc), "the credential reached the exception text"
    else:  # pragma: no cover - the mocked provider always declines
        raise AssertionError("expected the refusal to reach the caller")

    seen = provider_witness()
    assert seen is not None and seen.outcome == OUTCOME_REFUSED, seen
    assert seen.refusals == 1 and seen.answers == 0, seen
    assert witnessed_ai_state() == AI_PROVIDER_REFUSED


def test_a_transport_failure_is_reported_as_neither_an_answer_nor_a_refusal(monkeypatch) -> None:
    """A connection that never completed sent no HTTP status, so the witness stays empty.

    This keeps `PROVIDER_ANSWERED` honest: "the wire broke" is not an answer, and claiming either
    witnessed word here would be the same class of mistake as r2's.
    """

    _configure(monkeypatch)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to the provider")

    provider = DeepSeekResponsesClient(
        api_key=FAKE_KEY, client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    try:
        provider.complete([{"role": "user", "content": "北京三天怎么排"}])
    except DeepSeekResponsesError:
        pass
    else:  # pragma: no cover - the mocked transport always fails
        raise AssertionError("expected the transport error to reach the caller")

    assert provider_witness() is None, provider_witness()
    assert witnessed_ai_state() == AI_CONFIGURED_UNVERIFIED


# ----------------------------- R7 both doors on the wire, the model named, and the leak control


def test_both_status_doors_answer_with_the_witnessed_word_and_the_model(monkeypatch) -> None:
    """`/health` and `/agent/runtime-status` must agree, and the model that answered must be named.

    The old shape reported no model at all (`cmdr_ai_state_proof_1021dd.txt:2`), so an operator could
    not tell which model the server had actually used.  ORD-0387's contract-sync arm pins the two
    doors equal; this pins what the new field carries and that it carries no secret.
    """

    _configure(monkeypatch)
    _provider(200, ANSWER_ENVELOPE).complete([{"role": "user", "content": "北京三天怎么排"}])

    health = client.get("/api/v1/health").json()
    status = runtime_status()

    assert health["ai_state"] == AI_PROVIDER_ANSWERED, health
    assert status["ai_state"] == health["ai_state"], (status["ai_state"], health["ai_state"])
    last = status["ai_last_call"]
    assert last is not None, status
    assert last["outcome"] == OUTCOME_ANSWERED, last
    assert last["model_key"], "runtime-status still answered with no model"
    assert last["answers"] == 1 and last["refusals"] == 0, last
    assert FAKE_KEY not in json.dumps(status, ensure_ascii=False), status
    assert FAKE_KEY not in json.dumps(health, ensure_ascii=False), health


def test_the_field_stays_absent_rather_than_invented_before_the_first_call(monkeypatch) -> None:
    """A server that has never watched a call answers `ai_last_call: null`, not a fabricated record.

    The witness is process state, so this arm only holds because the conftest fixture returns the
    slot to empty - which is also the proof that fixture earns its place: without it, the simulated
    answer above would leak into every later health assertion in the same run.
    """

    _configure(monkeypatch)
    assert provider_witness() is None, provider_witness()

    status = runtime_status()
    assert status["ai_last_call"] is None, status
    assert status["ai_state"] == AI_CONFIGURED_UNVERIFIED, status
