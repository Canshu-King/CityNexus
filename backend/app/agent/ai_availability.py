"""One place that says why the AI is or is not answering, one word per cause.

`app.main.health` used to fold three unrelated facts into the single string `disabled`: the operator
turned the feature off, nobody installed a credential, and the configured provider actually
refused a call.  A traveller shown one word for three causes gets whichever sentence the screen
had lying around, and the screen's spare sentence was "网络或后端没有响应" - a network excuse for a
server-side setting, and the same class of scapegoat ORD-0355 removed for lodging budgets.

The names are produced here and nowhere else.  Precedence is fixed and stated because several of
these facts can be true at once, and a status endpoint that picked by accident would let two
doors disagree:

1. `PROVIDER_REFUSED` - the provider was reached and refused.  Only a caller that watched the
   refusal can pass this; nothing here infers it from configuration, because "a key exists" says
   nothing about whether the provider answered.
2. `DISABLED_BY_OPS` - `CITYNEXUS_AI_ENABLED` is off.  This describes the operator's switch.  It
   is deliberately not a claim that no call was attempted: the journey path today reaches the
   provider on the strength of a key alone (`agent/runtime.py` and the `main.py` door both test
   the credential, not the flag), so naming the switch is a disclosure about the setting, not a
   cause of a failed run.
3. `NOT_CONFIGURED` - the operator left the feature on but no credential is present for either
   the Responses endpoint or the Hermes gateway.
4. `CONFIGURED_UNVERIFIED` - a credential is present and nothing has contradicted it.  The word
   says exactly that much: ORD-0359 r2 measured a deliberately fake key string being reported as
   `READY`, which is why "a string is present" may never become "it works".
5. `PROVIDER_ANSWERED` - ORD-0697.  A caller that watched the upstream return a 2xx said so.  It
   is the same epistemic rule as `PROVIDER_REFUSED`, one side further: the vocabulary had a word
   for "refused" and no word for "answered", so a server that had just served nine real answers
   still had to say `CONFIGURED_UNVERIFIED`.  Nothing here infers it from configuration either -
   only the arm that made the call can record it, through `record_provider_answer`.

A no-argument call to `ai_availability_state` can therefore never return either witnessed word.
That is a invariant, not an accident: `runtime.unavailable_run_payload` writes
`reason_sentence(ai_availability_state())` into a run's `failure_reason`, and a run that never
reached the provider must not be able to store "the provider answered".  The doors that are
allowed to name a witnessed fact call `witnessed_ai_state` instead.

Nothing in this module reads, returns or logs a credential value: it reports whether one exists,
which model the last real call used, and what that call returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.config import settings

# r2 called this READY. Measured on a private backend at the tip 4ef864cfa49b805e3d41b7f079f5fb4184ccec3d,
# a deliberately fake key string produced `ai=enabled, ai_state=READY` - the word promised "it works" on
# the strength of "a string is present". The name now says exactly what is known and nothing more.
AI_CONFIGURED_UNVERIFIED = "CONFIGURED_UNVERIFIED"
AI_NOT_CONFIGURED = "NOT_CONFIGURED"
AI_DISABLED_BY_OPS = "DISABLED_BY_OPS"
AI_PROVIDER_REFUSED = "PROVIDER_REFUSED"
# ORD-0697: the other half of `PROVIDER_REFUSED`.  Reachable only through a witness, never inferred.
AI_PROVIDER_ANSWERED = "PROVIDER_ANSWERED"

AI_STATES = (
    AI_CONFIGURED_UNVERIFIED,
    AI_NOT_CONFIGURED,
    AI_DISABLED_BY_OPS,
    AI_PROVIDER_REFUSED,
    AI_PROVIDER_ANSWERED,
)

# The two outcomes a caller can witness, kept as their own names so `provider_witness()` can be
# compared against them without spelling the availability words twice.
OUTCOME_ANSWERED = "ANSWERED"
OUTCOME_REFUSED = "REFUSED"


def ai_availability_state(
    *, provider_refused: bool = False, provider_answered: bool = False
) -> str:
    """The one word for why the AI is or is not usable right now.

    Both keywords are statements the *caller* witnessed.  Leaving them out is the honest default:
    a door that did not watch a call cannot report what the provider did.
    """

    if provider_refused:
        return AI_PROVIDER_REFUSED
    if not settings.ai_enabled:
        return AI_DISABLED_BY_OPS
    if not settings.ai_api_key and not (settings.hermes_api_url and settings.hermes_api_key):
        return AI_NOT_CONFIGURED
    if provider_answered:
        return AI_PROVIDER_ANSWERED
    return AI_CONFIGURED_UNVERIFIED


@dataclass(frozen=True)
class ProviderWitness:
    """What this process last watched the configured AI provider do.

    Carries the provider key, the model identifier actually sent, the HTTP status and counters.
    Never carries a credential value or the request body - ORD-0697's leak arm reads this object's
    fields and asserts no key material is anywhere in it.
    """

    provider_key: str
    model_key: str | None
    outcome: str
    status_code: int | None
    observed_at: str
    answers: int
    refusals: int


_witness: ProviderWitness | None = None


def _record(
    outcome: str,
    *,
    provider_key: str,
    model_key: str | None,
    status_code: int | None,
) -> ProviderWitness:
    """The one place the slot moves, so both arms update it identically."""

    global _witness
    previous = _witness
    _witness = ProviderWitness(
        provider_key=provider_key,
        model_key=model_key,
        outcome=outcome,
        status_code=status_code,
        observed_at=datetime.now(timezone.utc).isoformat(),
        answers=(previous.answers if previous else 0) + (1 if outcome == OUTCOME_ANSWERED else 0),
        refusals=(previous.refusals if previous else 0) + (1 if outcome == OUTCOME_REFUSED else 0),
    )
    return _witness


def record_provider_answer(
    *, provider_key: str, model_key: str | None, status_code: int | None = None
) -> ProviderWitness:
    """Called by the arm that just read a 2xx off the wire.  Nothing else may call it."""

    return _record(
        OUTCOME_ANSWERED, provider_key=provider_key, model_key=model_key, status_code=status_code
    )


def record_provider_refusal(
    *, provider_key: str, model_key: str | None, status_code: int | None = None
) -> ProviderWitness:
    """Called by the arm that just read a refusal off the wire."""

    return _record(
        OUTCOME_REFUSED, provider_key=provider_key, model_key=model_key, status_code=status_code
    )


def provider_witness() -> ProviderWitness | None:
    """The last thing watched, or None when this process has never watched a provider call."""

    return _witness


def reset_provider_witness() -> None:
    """Clear the slot.  Tests use it so one module's simulated answer cannot colour the next."""

    global _witness
    _witness = None


def witnessed_ai_state() -> str:
    """The word for a status door that is allowed to quote what this server has watched.

    A refusal seen most recently outranks an earlier answer, because the traveller is asking about
    now; the counters stay visible through `provider_witness()` so the ordering is never a deletion.
    """

    seen = _witness
    return ai_availability_state(
        provider_refused=bool(seen and seen.outcome == OUTCOME_REFUSED),
        provider_answered=bool(seen and seen.answers),
    )



# The sentences this product writes into `AgentRun.failure_reason` / `JourneyMission.failure_reason`.
# They are the server's own words, so mapping them back is quoting, not guessing - which is why an
# unrecognised reason yields None instead of the nearest of the three.
_CONFIGURED_SENTENCES = (
    "DeepSeek API key is not configured",
    "Hermes runtime endpoint is not configured",
)
_OPS_SENTENCE = "AI is switched off by the operator"
_REFUSED_SENTENCES = (
    "DeepSeek Agent completion failed",
    "Hermes Agent completion failed",
)


# One table, so a run's stored sentence and the health endpoint's word cannot drift apart: the
# sentence is written FROM the state and read BACK into the same state.
# `PROVIDER_ANSWERED` is in the table so a screen can quote it, and deliberately has no marker in
# the sentence lists above: no success sentence ever belongs in a `failure_reason`, so reading it
# back from a stored failure stays None rather than inventing a success.
STATE_SENTENCES = {
    AI_NOT_CONFIGURED: "No AI credential is configured on this server",
    AI_DISABLED_BY_OPS: "AI is switched off by the operator",
    AI_PROVIDER_REFUSED: "The configured AI provider refused this request",
    AI_PROVIDER_ANSWERED: "The configured AI provider answered a request",
    AI_CONFIGURED_UNVERIFIED: "An AI credential is configured but has not been verified",
}


def reason_sentence(state: str) -> str:
    """The server's own words for a state, from the same table the parser reads."""

    if state not in STATE_SENTENCES:
        raise ValueError(f"unknown AI availability state: {state}")
    return STATE_SENTENCES[state]


def ai_state_from_failure_reason(reason: str | None) -> str | None:
    """Name the cause of an already-recorded failure, or None when this run did not say."""

    text = (reason or "").strip()
    if not text:
        return None
    if any(marker in text for marker in _REFUSED_SENTENCES):
        return AI_PROVIDER_REFUSED
    if any(marker in text for marker in _CONFIGURED_SENTENCES):
        return AI_NOT_CONFIGURED
    if _OPS_SENTENCE in text:
        return AI_DISABLED_BY_OPS
    return None
