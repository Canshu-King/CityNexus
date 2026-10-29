"""Measure what an unsigned GET /experience actually answers, while the suite runs.

Two reds in tests/test_r64_member_side_quest.py die with KeyError: 'active_plan' while reading a
projection whose builder always emits that key (app/stay_mobility.py:2052).  The only way the key can
be absent is that the answer is not a projection at all, so the question is the HTTP status and body
shape of the unsigned read.  This plugin observes every TestClient.get inside the running suite and
writes the recorded statuses to a receipt; it never edits a request, a response, or a product byte.

Run:  PYTHONPATH=trial/human_walk python -m pytest -q backend/tests/test_r64_member_side_quest.py \
        -p _cmdr_unsigned_experience_probe_r155 --tb=no
"""

import io
import json
import os

RECEIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..",
    "results",
    "20261026_gozero",
    "bu155-unsigned-experience-probe.txt",
)

_records = []
_installed_on = []
_state = {"in_control": False}
_current = {"nodeid": None}
_WATCH = ("/experience", "/events")


def pytest_runtest_setup(item):
    _current["nodeid"] = item.nodeid


def _install():
    from starlette.testclient import TestClient

    # starlette 1.6.0 keeps get() on TestClient itself and the cookie-aware get() again on its
    # httpx Client base, so every class in the MRO that actually defines get() gets wrapped.
    seen = []
    for base in TestClient.__mro__:
        if "get" in base.__dict__:
            seen.append(base)
    if not seen:
        raise RuntimeError("no class in the TestClient MRO defines get()")
    for base in seen:
        setattr(base, "get", _make_wrapper(base, base.__dict__["get"]))
        _installed_on.append(base.__name__)
    return _installed_on


def _make_wrapper(owner, original):
    def patched(self, url, *args, **kwargs):
        response = original(self, url, *args, **kwargs)
        if any(part in str(url) for part in _WATCH) and not getattr(response, "_cmdr_r155_seen", False):
            # TestClient.get() delegates to the httpx Client.get() underneath, so both wrappers
            # would otherwise log one HTTP call twice.  Mark the response the first time through.
            response._cmdr_r155_seen = True
            headers = kwargs.get("headers") or {}
            signed = "authorization" in {k.lower() for k in headers}
            detail = None
            body_text = None
            keys = []
            try:
                body = response.json()
                if isinstance(body, dict):
                    keys = sorted(body.keys())
                    detail = body.get("detail") or body.get("error")
                    if isinstance(detail, dict):
                        detail = sorted(detail.keys())
                else:
                    keys = ["<not-an-object>"]
                body_text = json.dumps(body, ensure_ascii=False, default=str)[:400]
            except Exception as exc:  # noqa: BLE001 - a probe must never break the run
                keys = ["<unparseable: %s>" % type(exc).__name__]
            _records.append(
                {
                    "owner": owner.__name__,
                    "nodeid": _current["nodeid"],
                    "door": next(part for part in _WATCH if part in str(url)),
                    "from_control": _state["in_control"],
                    "signed": signed,
                    "status": response.status_code,
                    "keys": keys,
                    "detail": detail,
                    "body": body_text,
                }
            )
        return response

    return patched


_control_lines = []


def _events_control():
    """The stateful arm's AttributeError, discriminated at the door it reads.

    tests/stateful/test_journey_truth_state_machine.py:267 iterates whatever /events answers, so a
    refusal body becomes a list of key strings and the run dies with 'str' object has no attribute
    'get'.  This arm shows which of the two it actually got, signed and unsigned, in one go.
    """
    module = None
    for name in (
        "tests.stateful.test_journey_truth_state_machine",
        "stateful.test_journey_truth_state_machine",
    ):
        try:
            module = __import__(name, fromlist=["client"])
            break
        except Exception as exc:  # noqa: BLE001
            yield "EVENTS CONTROL IMPORT %s -> %r" % (name, exc)
    if module is None:
        return
    try:
        from app.traveler_principal import issue_traveler_token

        reset = module.client.post("/api/v1/demo/reset", headers=module.demo_reset_headers())
        payload = reset.json()
        journey_id = payload["journey_id"]
        traveler_id = payload.get("traveler_id")
        url = "/api/v1/journeys/%s/events" % journey_id
        _state["in_control"] = True
        try:
            unsigned = module.client.get(url)
            signed = module.client.get(
                url, headers={"Authorization": "Bearer %s" % issue_traveler_token(str(traveler_id))}
            )
        finally:
            _state["in_control"] = False
        unsigned_body = unsigned.json()
        signed_body = signed.json()
        yield "EVENTS CONTROL UNSIGNED status=%d body_type=%s first_item_type=%s" % (
            unsigned.status_code,
            type(unsigned_body).__name__,
            type(list(unsigned_body)[0]).__name__ if isinstance(unsigned_body, dict) and unsigned_body else "<no items>",
        )
        yield "EVENTS CONTROL SIGNED status=%d body_is_list=%s item_count=%d traveler_id_known=%s" % (
            signed.status_code,
            isinstance(signed_body, list),
            len(signed_body) if isinstance(signed_body, list) else -1,
            bool(traveler_id),
        )
    except Exception as exc:  # noqa: BLE001
        yield "EVENTS CONTROL FAILED %r" % (exc,)


def pytest_runtest_teardown(item, nextitem):
    # The traveler token issuer only works while the session fixture that configures the principal
    # verifier is still alive, so the control has to run inside a test, not at sessionfinish.
    if _control_lines or "test_r69_meetup_handshake_requires_peer_and_ends_only_the_owners_split" not in item.nodeid:
        return
    before = len(_records)
    _control_lines.extend(_discriminated_control())
    _control_lines.extend(_events_control())
    _control_lines.append("CONTROL ADDED RECORDS %d (probe saw %d suite records before it)" % (len(_records) - before, before))


def _discriminated_control():
    """Same journey, same door: once without the bearer, once with it.

    Without this arm "0 signed reads" could not be told apart from a probe that cannot see a signed
    read at all, and a 401 could be blamed on the door instead of on the missing header.
    """
    module = None
    for name in ("tests.test_r64_member_side_quest", "test_r64_member_side_quest"):
        try:
            module = __import__(name, fromlist=["client"])
            break
        except Exception as exc:  # noqa: BLE001
            yield "CONTROL IMPORT %s -> %r" % (name, exc)
    if module is None:
        return
    try:
        journey_id, owner_id, _other = module._active_shared_journey()
        url = "/api/v1/journeys/%s/experience" % journey_id
        _state["in_control"] = True
        try:
            unsigned = module.client.get(url)
            signed = module.client.get(url, headers=module._auth(str(owner_id)))
        finally:
            _state["in_control"] = False
        yield "CONTROL UNSIGNED status=%d body_keys=%s" % (
            unsigned.status_code,
            sorted(unsigned.json().keys()) if isinstance(unsigned.json(), dict) else "<not-object>",
        )
        payload = signed.json()
        yield "CONTROL SIGNED status=%d has_active_plan_key=%s active_plan_id=%s" % (
            signed.status_code,
            "active_plan" in payload,
            (payload.get("active_plan") or {}).get("id") if isinstance(payload.get("active_plan"), dict) else None,
        )
    except Exception as exc:  # noqa: BLE001
        yield "CONTROL FAILED %r" % (exc,)


def pytest_configure(config):
    try:
        wrapped = _install()
        print("PROBE WRAPPED get() ON %s" % ",".join(wrapped))
    except Exception as exc:  # noqa: BLE001
        print("PROBE INSTALL FAILED: %r" % (exc,))


def pytest_sessionfinish(session, exitstatus):
    suite = [r for r in _records if not r["from_control"]]
    control = [r for r in _records if r["from_control"]]
    signed_counts = {}
    unsigned_counts = {}
    for record in suite:
        bucket = signed_counts if record["signed"] else unsigned_counts
        bucket[record["status"]] = bucket.get(record["status"], 0) + 1
    lines = [
        "PROBE starlette TestClient.get, observation only, suite=%s" % session.config.args,
        "PROBE WRAPPED ON %s" % (",".join(_installed_on) or "NOTHING"),
        "TOTAL /experience READS %d" % len(suite),
        "CONTROL /experience READS %d" % len(control),
        "SIGNED STATUS COUNTS %s" % json.dumps(signed_counts, sort_keys=True),
        "UNSIGNED STATUS COUNTS %s" % json.dumps(unsigned_counts, sort_keys=True),
        "READS PER DOOR %s" % json.dumps(
            {
                door: sum(1 for r in suite if r["door"] == door)
                for door in sorted({r["door"] for r in suite})
            },
            sort_keys=True,
        ),
        "UNSIGNED READS PER DOOR %s" % json.dumps(
            {
                door: sum(1 for r in suite if r["door"] == door and not r["signed"])
                for door in sorted({r["door"] for r in suite})
            },
            sort_keys=True,
        ),
        "FIRST UNSIGNED RECORD %s" % json.dumps(
            next((r for r in suite if not r["signed"]), None), ensure_ascii=False
        ),
        "FIRST SIGNED RECORD %s" % json.dumps(
            next((r for r in suite if r["signed"]), None), ensure_ascii=False
        ),
    ]
    for index, record in enumerate(r for r in suite if not r["signed"] and r["status"] != 200):
        lines.append("UNSIGNED NON-200 %d %s" % (index + 1, json.dumps(record, ensure_ascii=False)))
    lines.extend(_control_lines)
    destination = os.path.abspath(RECEIPT)
    io.open(destination, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % destination)
