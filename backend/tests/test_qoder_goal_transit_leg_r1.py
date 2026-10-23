"""A hop nobody can walk is asked of the public-transport door -- and named for what answered it.

Why this file exists: until tonight the departure door measured every hop with `client.walking` and
nothing else (backend/app/agent/goal_route_freeze.py, the leg this covers), so a link too far to walk --
or the one that closes a day and opens the next -- came back as "no source answered", the candidate
could never freeze, and the traveller could never depart.  The provider does answer those hops when
asked as transit: measured live on 前门大街 -> 天坛公园, 32 walking minutes against about 41 minutes by
public transport naming 地铁8号线 with a 3.00 fare
(trial/results/20261022_v3_human_chrome/amap-transit-capability-1.txt).

These arms pin the door itself, not the network: a walking answer must still win, the transit row must
carry the transit call's own receipt id (not the walking call's that refused), the lines the provider
named must survive, the hour asked must be the hour the traveller arrives, and no city code must mean no
transit request is invented.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.agent import goal_route_freeze as module

TZ = timezone(timedelta(hours=8))
ARRIVAL = datetime(2026, 12, 4, 3, 20, tzinfo=TZ)

WALK_OK = {"status": "ok", "route": {"distance_m": 640, "duration_seconds": 510, "mode": "WALK", "lines": []}}
WALK_REFUSED = {"status": "error", "reason_code": "AMAP_NO_ROUTE", "route": None}
TRANSIT_OK = {"status": "ok", "route": {"distance_m": 3852, "duration_seconds": 2481, "mode": "TRANSIT",
                                        "lines": ["地铁8号线(朱辛庄--瀛海)"], "walking_distance_m": 1892}}
TRANSIT_REFUSED = {"status": "error", "reason_code": "AMAP_NO_ROUTE", "route": None}


class _Session:
    """Collects the ProviderCall rows the real receipt writer builds; touches no database."""

    def __init__(self) -> None:
        self.rows: list = []

    def add(self, row) -> None:
        self.rows.append(row)


class _Client:
    def __init__(self, *, walk: dict, transit: dict, calls: list) -> None:
        self._walk, self._transit, self._calls = walk, transit, calls

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def close(self) -> None:
        return None

    def walking(self, origin, destination, adcode=None) -> dict:
        self._calls.append(("walking", adcode))
        return dict(self._walk)

    def transit(self, origin, destination, city_code, *, departure_date=None, departure_time=None) -> dict:
        self._calls.append(("transit", city_code, departure_date, departure_time))
        return dict(self._transit)


def _run(monkeypatch, *, walk: dict, transit: dict, task: dict, arrival=ARRIVAL):
    calls: list = []
    session = _Session()
    monkeypatch.setattr(module, "settings", SimpleNamespace(amap_web_key="loopback-test-key"))
    client = _Client(walk=walk, transit=transit, calls=calls)
    monkeypatch.setattr(module, "_client", lambda: client)
    origin = SimpleNamespace(id="place-origin", name="前门大街", external_id="amap:B001",
                             latitude=39.896152, longitude=116.403895)
    destination = SimpleNamespace(id="place-destination", name="天坛公园", external_id="amap:B002",
                                  latitude=39.881913, longitude=116.410829)
    row = module._measure_now(session, task, origin, destination, arrival=arrival)
    return row, calls, session


def test_a_walking_answer_still_wins_and_no_transit_is_asked(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_OK, transit=TRANSIT_OK,
                                task={"amap_region": {"citycode": "010"}})
    assert [entry[0] for entry in calls] == ["walking"]
    assert row is not None and row["mode"] == "WALK" and row["lines"] == []
    assert "mode=walk" in row["source_url"]


def test_a_hop_nobody_walks_is_asked_of_the_transport_door_and_named_for_it(monkeypatch) -> None:
    row, calls, session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK,
                               task={"amap_region": {"citycode": "010"}})
    assert [entry[0] for entry in calls] == ["walking", "transit"]
    assert row is not None
    assert row["mode"] == "TRANSIT"
    assert row["lines"] == ["地铁8号线(朱辛庄--瀛海)"]
    assert row["duration_seconds"] == 2481
    assert "mode=bus" in row["source_url"]
    # The row's identity is the call that answered it.  The walking call is still recorded, but a row
    # pointing at it would trace a bus minute back to a request that refused.
    assert session.rows[0].status == "FAILURE" and session.rows[1].status == "SUCCESS"
    assert row["id"] == str(session.rows[1].id) != str(session.rows[0].id)


def test_the_provider_says_a_far_hop_is_out_of_its_range_and_the_transport_door_answers(monkeypatch) -> None:
    # 20803 OVER_DIRECTION_RANGE, measured on 王府井步行街 -> 八达岭长城 while the transit door gave five
    # routes for the same pair (trial/results/20261022_v3_human_chrome/amap-quota-vs-qps-1.txt:2 and :4).
    # It refused the hop, not the caller, so it opens the second door.
    row, calls, _session = _run(monkeypatch, walk=_refusal_walk("AMAP_OUT_OF_PROVIDER_RANGE"),
                                transit=TRANSIT_OK, task={"amap_region": {"citycode": "010"}})
    assert [entry[0] for entry in calls] == ["walking", "transit"]
    assert row is not None and row["mode"] == "TRANSIT"


def test_the_hour_asked_is_the_hour_the_traveller_arrives(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK,
                                task={"amap_region": {"citycode": "010"}})
    assert row is not None
    assert calls[1] == ("transit", "010", "2026-12-04", "03:20")


# The plan does not store a datetime: `Activity.start_at` is a text column, and `freeze_routes` hands this
# arm exactly that string (backend/app/agent/goal_route_freeze.py:339).  The first version of the
# public-transport arm called `.strftime` on it and the traveller's own button answered 500 --
# trial/results/20261022_v3_human_chrome/walk-78-log.txt:41 with the traceback at
# trial/results/20261022_v3_human_chrome/walk-78-freeze-traceback-1.txt:98.  These two arms are the
# regression: the shape that arrived over the wire, not the shape a fixture would like.
def test_the_hour_the_plan_stores_is_text_and_still_asks_at_that_hour(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK,
                                task={"amap_region": {"citycode": "010"}},
                                arrival="2026-12-04T11:00:00+08:00")
    assert row is not None
    assert calls[1] == ("transit", "010", "2026-12-04", "11:00")


def test_unreadable_arrival_text_asks_without_inventing_an_hour(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK,
                                task={"amap_region": {"citycode": "010"}}, arrival="昨天下午")
    assert row is not None
    assert calls[1] == ("transit", "010", None, None)


def test_a_hop_with_no_arrival_hour_is_asked_without_inventing_one(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK,
                                task={"amap_region": {"citycode": "010"}}, arrival=None)
    assert row is not None
    assert calls[1] == ("transit", "010", None, None)


def test_no_city_code_means_no_transport_request_is_invented(monkeypatch) -> None:
    row, calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_OK, task={})
    assert row is None
    assert [entry[0] for entry in calls] == ["walking"]


def test_when_neither_door_answers_the_hop_stays_unanswered(monkeypatch) -> None:
    row, calls, session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_REFUSED,
                               task={"amap_region": {"citycode": "010"}})
    assert row is None
    assert [entry[0] for entry in calls] == ["walking", "transit"]
    assert [recorded.status for recorded in session.rows] == ["FAILURE", "FAILURE"]


# The refusals below are the ones a second door cannot fix.  Measured on the live service, the walking
# engine refuses 八达岭长城 -> 故宫 and 雁栖湖 -> 故宫 with a content refusal at http 200 and the transport
# engine answers both (trial/results/20261022_v3_human_chrome/amap-transit-within-city-1.txt:3, :5, :6,
# :7), while a spent quota or a rejected key answers nothing about any hop at all.
ACCESS_REFUSALS = ["AMAP_QUOTA_EXCEEDED", "AMAP_INVALID_KEY", "AMAP_SERVICE_PERMISSION_DENIED",
                   "AMAP_HTTP_ERROR", "AMAP_INVALID_COORDINATE",
                   # Asked too often at once: the second door is the same door a moment later, and
                   # reaching for it spends the very limit that just refused.  Measured with a burst of
                   # eight walking calls (trial/results/20261022_v3_human_chrome/amap-burst-infocode-1.txt:2).
                   "AMAP_RATE_LIMITED"]


def _refusal_walk(reason: str) -> dict:
    return {"status": "error", "reason_code": reason, "route": None}


def test_an_access_refusal_does_not_open_the_transport_door(monkeypatch) -> None:
    for reason in ACCESS_REFUSALS:
        row, calls, _session = _run(monkeypatch, walk=_refusal_walk(reason), transit=TRANSIT_OK,
                                    task={"amap_region": {"citycode": "010"}})
        assert row is None, reason
        # A momentary "too many at once" is asked again after one pause -- measured to recover in a second
        # (trial/results/20261022_v3_human_chrome/amap-burst-infocode-2.txt:3).  Every other access
        # refusal is asked once.  Neither kind reaches the transport door.
        expected_asks = 2 if reason == "AMAP_RATE_LIMITED" else 1
        assert [entry[0] for entry in calls] == ["walking"] * expected_asks, reason
        assert calls[0][0] == "walking"


def test_a_refused_hop_keeps_the_reason_the_provider_gave(monkeypatch) -> None:
    task = {"amap_region": {"citycode": "010"}}
    row, _calls, _session = _run(monkeypatch, walk=_refusal_walk("AMAP_QUOTA_EXCEEDED"),
                                 transit=TRANSIT_OK, task=task)
    assert row is None
    # The pair is keyed by the two place rows, so the freeze can name this hop without asking again.
    assert module._refusal_reason(task, SimpleNamespace(id="place-origin"),
                                  SimpleNamespace(id="place-destination")) == "AMAP_QUOTA_EXCEEDED"
    assert module._refusal_reason(task, SimpleNamespace(id="place-origin"),
                                  SimpleNamespace(id="place-somewhere-else")) is None


def test_a_hop_both_doors_refused_is_not_blamed_on_the_travellers_map(monkeypatch) -> None:
    task = {"amap_region": {"citycode": "010"}}
    row, _calls, _session = _run(monkeypatch, walk=WALK_REFUSED, transit=TRANSIT_REFUSED, task=task)
    assert row is None
    assert module._refusal_reason(task, SimpleNamespace(id="place-origin"),
                                  SimpleNamespace(id="place-destination")) == "AMAP_NO_ROUTE"


def test_the_refusal_bookkeeping_stays_bounded(monkeypatch) -> None:
    task: dict = {"amap_region": {"citycode": "010"}}
    origin = SimpleNamespace(id="place-origin", name="前门大街", external_id="amap:B001",
                             latitude=39.896152, longitude=116.403895)
    for index in range(40):
        destination = SimpleNamespace(id=f"place-{index}", name="天坛公园", external_id=f"amap:B{index:03d}",
                                      latitude=39.88, longitude=116.41)
        module._record_refusal(task, origin, destination, "AMAP_QUOTA_EXCEEDED")
    assert len(task["route_refusals"]) <= 32
