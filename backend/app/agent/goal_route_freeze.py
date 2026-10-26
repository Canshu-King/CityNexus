"""Turn the hops a saved candidate actually walks into frozen provider evidence.

Why this door exists: selecting a plan reads two things the Agent's draft never wrote --
`backend/app/main.py:18120` refuses any candidate whose `mobility_evidence_json` has no snapshot id, and
`backend/app/services.py:584` marks exactly those candidates stale with the sentence
"STALE_RECOMPOSE_REQUIRED: no frozen provider evidence". Measured on the walked database
(trial/results/20261022_v3_human_chrome/departure-price-evidence-probe-1.txt) every candidate saved from
an Agent draft hit both, so the traveller could save eight real places and still be given no button.
The preparation door states this itself: `backend/app/agent/goal_preparation.py:76` declares
`mobility_frozen: Literal[False]`, and `:322` writes that literal into every prepared answer.

What this adds is a bridge, not a second source of truth:

* Only the edges the candidate really walks are enumerated -- same-day adjacent activities that both
  carry a canonical place row. Cross-day pairs are skipped because nobody walks them, and the draft's
  own to-do already names any item with no place.
* The measurement is the one the Agent already uses: a stored `research_routes` row from a real
  `goal_amap_walking` provider call is reused, and a missing edge is asked of the same client through
  the same receipt writer, so every number in the snapshot has a `ProviderCall` behind it.
* The snapshot is written by the product's existing capture door
  (`backend/app/integrations/mobility/snapshot_capture.py:95`) with no fallback provider: if any edge
  has no live measurement the capture raises and nothing is frozen. A fixture number, a straight line
  between two coordinates, or a model guess never enters a hard decision here (V4 #4, T2).
* Freezing is not selecting. Selection still runs the server's own authority and feasibility gates
  (`backend/app/services.py:744` onward, `backend/app/replanning/feasibility.py:965` onward); this only
  stops the candidate from being evidence-free.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.goal_amap import _client, _receipt
from app.agent.goal_mobility import StoredAmapRoutes, route_geometry_wgs84
from app.agent.goal_tasks import _require_task
from app.commerce.idempotency import canonical_request_signature
from app.concurrency_guards import journey_write_lock
from app.core.audit import record_audit
from app.capabilities import extract_capabilities_from_text
from app.core.config import settings
from app.db.models import Activity, IdempotencyKey, Journey, JourneyIntent, Place, PlanVersion
from app.db.session import get_session
from app.integrations.china.amap import wgs84_to_gcj02
from app.integrations.mobility.snapshot_capture import MobilitySnapshotCaptureError, capture_mobility_snapshot
from app.traveler_principal import member_has_capability, resolve_journey_member_principal

router = APIRouter()
PATH = "/api/v1/journeys/{journey_id}/agent/goal-tasks/{task_id}/plans/{plan_version_id}/freeze-routes"

REUSED = "REUSED_PROVIDER_RECEIPT"
MEASURED = "MEASURED_NOW"
UNAVAILABLE = "ROUTE_UNAVAILABLE"


class RouteEdge(BaseModel):
    from_place_id: str
    to_place_id: str
    from_name: str
    to_name: str
    status: str
    minutes: int | None
    distance_m: int | None
    spans_night: bool = False
    # Which door answered this hop.  WALK is what this door ever asked for until the public-transport
    # leg landed; a TRANSIT hop is named as such so the card never presents a bus ride as a walk.
    mode: str | None = None
    lines: list[str] = []
    # A hop the traveller's own walking limit replaced with public transport carries the walk it
    # replaces; a hop that stayed a walk beyond the limit carries `over_cap_m` instead.
    replaced_walk_m: int | None = None
    walking_cap_m: int | None = None
    over_cap_m: int | None = None
    provider: str | None
    source_url: str | None
    captured_at: str | None
    reason_code: str | None


class FreezeRoutesResult(BaseModel):
    journey_id: str
    task_id: str
    plan_version_id: str
    edges: list[RouteEdge]
    verified: int
    total: int
    # Hops that carry the traveller across a night, counted so the card can name them separately
    # instead of presenting an overnight link as a walk the traveller takes that afternoon.
    overnight: int = 0
    # Hops answered by the public-transport door rather than the walking one.
    transit: int = 0
    # Hops the traveller's own per-hop walking limit moved off the walking door, the hops that stayed
    # over the limit because the transport door had no answer, and the limit itself (None = never stated).
    replaced_long_walks: int = 0
    over_cap_walks: int = 0
    walking_cap_m: int | None = None
    frozen: bool
    mobility_snapshot_id: str | None
    reason_code: str | None
    idempotency_replay: bool = False


def _candidate_id(activity: Activity) -> str:
    """The provider key this row was researched under, from the row itself -- never a name match."""
    try:
        metadata = json.loads(activity.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return str(metadata.get("source_candidate_id") or "")


def _same_day(previous: Activity, current: Activity) -> bool:
    return str(previous.start_at)[:10] == str(current.start_at)[:10]


def used_edges(session: Session, plan: PlanVersion) -> list[tuple[Activity, Activity]]:
    """Every hop the selection gate will ask about, in the order the traveller meets them.

    Two rules, both read off the consumer rather than invented here:

    * the plan is one chain -- `app/replanning/feasibility.py:966` pairs consecutive activities whatever
      date they fall on, so the first stop of the morning is checked against the last stop of the day
      before it.  A hop that spans a night is still a hop the gate demands, so it is measured and then
      labelled as such for the screen;
    * a place is not a hop from itself.  Consecutive stops at the same venue need no route, and the
      two capture doors in the product already refuse to route such a pair
      (`app/main.py:22876`, `app/integrations/mobility/runtime.py:121`).
    """
    rows = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id)
                               .order_by(Activity.sequence_no)))
    placed = [row for row in rows if row.place_id]
    return [(previous, current) for previous, current in zip(placed, placed[1:])
            if previous.place_id != current.place_id]


def _stored_route(task: dict, origin_key: str, destination_key: str) -> dict | None:
    for row in task.get("research_routes") or []:
        if not isinstance(row, dict):
            continue
        pair = {str(row.get("from_place_id") or ""), str(row.get("to_place_id") or "")}
        if pair == {origin_key, destination_key} and row.get("duration_seconds") is not None:
            return row
    return None


def _orient_reused_route(route: dict, origin_key: str, destination_key: str,
                         origin: Place, destination: Place) -> dict:
    """Reverse stored geometry for a reverse reuse while retaining the original provider receipt."""
    measured_from = str(route.get("from_place_id") or "")
    measured_to = str(route.get("to_place_id") or "")
    if measured_from != destination_key or measured_to != origin_key:
        return route

    oriented = dict(route)
    oriented["measurement_from_place_id"] = route.get("measurement_from_place_id") or measured_from
    oriented["measurement_to_place_id"] = route.get("measurement_to_place_id") or measured_to
    oriented["from_place_id"] = origin_key
    oriented["to_place_id"] = destination_key
    oriented["from_name"] = origin.name
    oriented["to_name"] = destination.name
    oriented["lookup_reused_in_reverse"] = True

    path = route.get("path")
    if isinstance(path, dict) and path.get("type") == "LineString":
        coordinates = path.get("coordinates")
        oriented["path"] = {
            **path,
            "coordinates": [list(point) for point in reversed(coordinates)] if isinstance(coordinates, list) else [],
        }

    geometry = route.get("route_geometry")
    if isinstance(geometry, dict):
        raw_geometry = geometry.get("geometry") if geometry.get("type") == "Feature" else geometry
        if isinstance(raw_geometry, dict) and raw_geometry.get("type") == "LineString":
            coordinates = raw_geometry.get("coordinates")
            reversed_geometry = {
                **raw_geometry,
                "coordinates": [list(point) for point in reversed(coordinates)] if isinstance(coordinates, list) else [],
            }
            if geometry.get("type") == "Feature":
                properties = dict(geometry.get("properties") or {})
                properties["lookup_direction"] = "REVERSED_STORED_MEASUREMENT"
                oriented["route_geometry"] = {**geometry, "properties": properties, "geometry": reversed_geometry}
            else:
                oriented["route_geometry"] = reversed_geometry

    segments = route.get("geometry_segments")
    if isinstance(segments, list):
        reversed_segments: list[dict] = []
        for item in reversed(segments):
            if not isinstance(item, dict):
                continue
            segment = dict(item)
            coordinates = item.get("coordinates")
            if isinstance(coordinates, list):
                segment["coordinates"] = [list(point) for point in reversed(coordinates)]
            reversed_segments.append(segment)
        oriented["geometry_segments"] = reversed_segments

    provenance = route.get("geometry_provenance")
    provenance = dict(provenance) if isinstance(provenance, dict) else {}
    provenance.update(
        {
            "lookup_direction": "REVERSED_STORED_MEASUREMENT",
            "measurement_from_place_id": oriented["measurement_from_place_id"],
            "measurement_to_place_id": oriented["measurement_to_place_id"],
        }
    )
    oriented["geometry_provenance"] = provenance
    return oriented


# Two refusals look the same on the traveller's screen and are not the same thing at all.
#
# A *content* refusal means the provider took the question and answered that it has no walking route for
# that pair -- measured live: 八达岭长城 -> 故宫 and 雁栖湖 -> 故宫 both come back rejected at http 200
# (trial/results/20261022_v3_human_chrome/amap-transit-within-city-1.txt:3 and :5) while the
# public-transport door answers those same hops: 78,050 m in 180 min naming 919路 and 5路, and 73,750 m in
# 192 min naming H1路, 916路快车 and 604路 (同文件 :6 and :7).  That is the hop this second door exists
# for.
#
# An *access* refusal -- no key, a key the service rejects, a denied permission, an exhausted quota, a
# transport failure -- says nothing about the hop.  Asking the second door after it cannot produce a
# route, and it spends a request against the very limit that just refused the first one (this session's
# own walk hit AMAP_QUOTA_EXCEEDED at 00:16 and needed a minute to recover).  So the transit arm opens
# for the refusals below and for nothing else.

_TRANSIT_ANSWERABLE_REFUSALS = frozenset({"AMAP_NO_ROUTE", "AMAP_PROVIDER_REJECTED",
                                          # "This pair is outside the range I route" -- the provider's own
                                          # infocode 20803, measured on 王府井步行街 -> 八达岭长城 while
                                          # the transit door answered it with five routes
                                          # (trial/results/20261022_v3_human_chrome/amap-quota-vs-qps-1.txt:2
                                          # against :4).  It names the hop, so it belongs with the content
                                          # refusals, not with the access ones.
                                          "AMAP_OUT_OF_PROVIDER_RANGE"})

# One pause before a rate-limited hop is asked a second time, in seconds.  The provider's own recovery
# was measured at one second (trial/results/20261022_v3_human_chrome/amap-burst-infocode-2.txt:3).
_RATE_LIMITED_RETRY_AFTER_S = 1.0


def _refusal_key(origin: Place, destination: Place) -> str:
    return f"{origin.id}->{destination.id}"


def _record_refusal(task: dict, origin: Place, destination: Place, reason: str) -> None:
    """Keep which door refused, and why, beside the task that asked it."""
    refusals = task.setdefault("route_refusals", {})
    if not isinstance(refusals, dict):
        refusals = {}
        task["route_refusals"] = refusals
    refusals[_refusal_key(origin, destination)] = reason
    for stale in list(refusals)[: max(0, len(refusals) - 32)]:
        refusals.pop(stale, None)


def _refusal_reason(task: dict, origin: Place, destination: Place) -> str | None:
    """The reason the provider itself gave for this hop, when it gave one.

    Why this matters for the traveller: until now every unanswered hop read PROVIDER_ROUTE_UNAVAILABLE,
    which makes "this city has no route between these two places" and "the map service is out of quota"
    the same sentence.  The provider distinguishes them, so the product can too.
    """
    refusals = task.get("route_refusals")
    if not isinstance(refusals, dict):
        return None
    value = refusals.get(_refusal_key(origin, destination))
    return str(value) if value else None


def _arrival_moment(value: datetime | str | None) -> datetime | None:
    """Read the hour the plan stores, whatever shape the caller handed over.

    Why this exists at all: `Activity.start_at` is a text column (`app/db/models.py`), and this door is
    called with exactly that value (`freeze_routes` passes `destination_row.start_at`).  The first version
    of the public-transport arm called `arrival.strftime` on it, so the traveller's own button answered
    `500` with `AttributeError: 'str' object has no attribute 'strftime'` the moment a hop reached that
    arm -- `trial/results/20261022_v3_human_chrome/walk-78-log.txt:41`, traceback at
    `trial/results/20261022_v3_human_chrome/walk-78-freeze-traceback-1.txt:98`.  My unit arms did not catch
    it because they handed in a real datetime: a friendlier fixture than the product.

    An unreadable hour is asked as *no* hour rather than invented: the provider then answers for whatever
    it defaults to, and the row says so, instead of the plan claiming a departure time nobody wrote down.
    """
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _transit_leg(session: Session, task: dict, origin: Place, destination: Place,
                 start: tuple[float, float], end: tuple[float, float],
                 arrival: datetime | str | None) -> dict | None:
    """The hop nobody walks: asked of the public-transport door, at the hour the traveller arrives.

    Why this exists: `client.walking` is the only measurement this door ever made, so a hop that is too
    far to walk -- or the link that closes one day and opens the next -- came back with no answer at all,
    and a candidate holding such a hop could never freeze, never be selected and never be departed.  The
    live readings behind this are in trial/results/20261022_v3_human_chrome/amap-transit-capability-1.txt
    (the same 前门大街 to 天坛公园 pair: 32 walking minutes, and a public-transport answer of about 41
    minutes naming 地铁8号线 with a 3.00 fare).

    What is deliberately not claimed here: the provider's own `nightflag` came back 0 even on a night
    line (amap-transit-night-3.txt:8), and asking for a night hour produced the night lines once and the
    daytime answer on a re-run (amap-transit-method-live-1.txt:6), so the hour is sent as the traveller's
    plan states it and the answer is stored as what the provider said to that request -- not as a promise
    that the line runs at that hour.

    Why one city code is sent for both ends, and why that is not a bug to come back and "fix": a hop that
    really crosses cities answers the same way either way -- 北京南站 -> 天津站 measures 117,275 m with
    city1=city2=010 (trial/results/20261022_v3_human_chrome/amap-transit-crosscity-1.txt:3) and 117,275 m
    again with city1=010 city2=022 (同文件 :4).  And a V3 plan cannot contain such a hop today: every
    researched place is stamped with the journey's own city (app/agent/goal_place_identity.py:101) and the
    gateway refuses a place from another city (app/agent/gateway.py:1594).  The hops this arm actually
    serves are the within-city ones nobody walks -- 八达岭长城 back to 故宫, say.
    """
    city_code = str((task.get("amap_region") or {}).get("citycode") or "").strip()
    if not city_code:
        return None
    moment = _arrival_moment(arrival)
    date_text = moment.strftime("%Y-%m-%d") if moment is not None else None
    time_text = moment.strftime("%H:%M") if moment is not None else None
    with _client() as transit_client:
        receipt = _receipt(session, "goal_amap_transit",
                           {"from_place_id": origin.id, "to_place_id": destination.id,
                            "coordinate_system": "GCJ02", "city_code": city_code,
                            "departure_date": date_text, "departure_time": time_text},
                           transit_client.transit(start, end, city_code,
                                                  departure_date=date_text, departure_time=time_text))
    if receipt.get("status") != "ROUTE_READY" or not isinstance(receipt.get("route"), dict):
        return None
    route = dict(receipt["route"])
    route["provider_call_id"] = receipt.get("provider_call_id")
    return route


def _route_geometry_fields(route: dict, *, provider_call_id: str | None = None) -> dict:
    geometry = route_geometry_wgs84(route, provider_call_id=provider_call_id)
    provider_status = str(route.get("geometry_status") or "")
    if geometry is not None:
        status = provider_status or "AVAILABLE"
    elif provider_status and provider_status != "AVAILABLE":
        status = provider_status
    elif isinstance(route.get("path"), dict) or isinstance(route.get("route_geometry"), dict):
        status = "BLOCKED_GEOMETRY_CONVERSION_FAILED"
    else:
        status = "BLOCKED_GEOMETRY_UNAVAILABLE"
    provenance = route.get("geometry_provenance")
    provenance = dict(provenance) if isinstance(provenance, dict) else {}
    if geometry is not None:
        provenance.update(geometry["properties"])
    else:
        path = route.get("path")
        source_crs = path.get("coordinate_system") if isinstance(path, dict) else route.get("coordinate_system")
        provenance.update(
            {
                "source_provider": route.get("provider_key") or route.get("provider") or "amap-web-service",
                "provider_call_id": provider_call_id or route.get("provider_call_id") or route.get("id"),
                "source_coordinate_system": source_crs or "UNKNOWN",
                "domain_crs": "WGS84",
                "conversion": "FAILED" if status == "BLOCKED_GEOMETRY_CONVERSION_FAILED" else None,
                "geometry_status": status,
            }
        )
    segments = route.get("geometry_segments")
    return {
        "path": route.get("path"),
        "geometry_segments": list(segments) if isinstance(segments, list) else [],
        "geometry_status": status,
        "route_geometry": geometry,
        "geometry_provenance": provenance,
    }


def _measure_now(session: Session, task: dict, origin: Place, destination: Place,
                 arrival: datetime | str | None = None) -> dict | None:
    """Ask the same AMap client the Agent uses, through the same receipt writer.

    GCJ-02 is what the provider speaks and WGS-84 is what the row stores
    (`app/db/models.py`, Arbitration R4): the stored point is converted on the way out and the returned
    row keeps both the provider coordinate claim and the public source url, so the frozen fact is
    traceable to a call rather than to a string.

    A walking answer wins when there is one.  When the walking door answers that it has no walking route,
    the same hop is asked of the public-transport door once (`_transit_leg`), because "no answer" and "not
    a walking trip" used to be the same screen state and only one of them is the traveller's problem.  A
    walking refusal that is about *access* rather than about the map -- no key, a rejected key, a denied
    permission, an exhausted quota, a transport failure -- does not open that second door: see
    `_TRANSIT_ANSWERABLE_REFUSALS` above for the measurements that separate the two.
    """
    if not settings.amap_web_key:
        return None
    start = wgs84_to_gcj02(float(origin.latitude), float(origin.longitude))
    end = wgs84_to_gcj02(float(destination.latitude), float(destination.longitude))
    with _client() as client:
        receipt = _receipt(session, "goal_amap_walking",
                           {"from_place_id": origin.id, "to_place_id": destination.id,
                            "coordinate_system": "GCJ02"}, client.walking(start, end))
    if str(receipt.get("reason_code") or "") == "AMAP_RATE_LIMITED":
        # "Too many at once" is a moment, not a verdict, and this freeze asks every hop in one go.
        # Measured: six back-to-back walking calls on one city pair refused three of them with infocode
        # 10021 CUQPS_HAS_EXCEEDED_THE_LIMIT, and the same hop answered a route one second later
        # (trial/results/20261022_v3_human_chrome/amap-burst-infocode-2.txt:2 against :3).  So the hop is
        # asked again after that pause -- once.  A retry loop would spend the traveller's daily allowance
        # on our own burst, and a hop that refuses twice is reported as refused.
        time.sleep(_RATE_LIMITED_RETRY_AFTER_S)
        with _client() as client:
            receipt = _receipt(session, "goal_amap_walking",
                               {"from_place_id": origin.id, "to_place_id": destination.id,
                                "coordinate_system": "GCJ02"}, client.walking(start, end))
    route = receipt.get("route")
    mode = "WALK"
    call_id = receipt.get("provider_call_id")
    if receipt.get("status") != "ROUTE_READY" or not isinstance(route, dict):
        walking_reason = str(receipt.get("reason_code") or "AMAP_PROVIDER_REJECTED")
        if walking_reason not in _TRANSIT_ANSWERABLE_REFUSALS:
            _record_refusal(task, origin, destination, walking_reason)
            return None
        route = _transit_leg(session, task, origin, destination, start, end, arrival)
        mode = "TRANSIT"
        if route is None:
            # Both doors answered this hop and neither of them had a route.  That is the provider's own
            # statement, so it is what the traveller is told -- not the blanket code that used to cover
            # "the map service is out of quota" too.
            _record_refusal(task, origin, destination, walking_reason)
            return None
        # The row's identity is the call that produced it.  Carrying the walking call's id onto a
        # transit answer would point the traceable receipt at a request that never answered.
        call_id = route.get("provider_call_id")
    row = {"id": call_id or str(uuid4()),
           "from_place_id": _candidate_id_for(task, origin), "to_place_id": _candidate_id_for(task, destination),
           "from_name": origin.name, "to_name": destination.name, "provider": "amap",
           "coordinate_system": "GCJ02", "distance_m": route.get("distance_m"),
           "duration_seconds": route.get("duration_seconds"), "captured_at": datetime.now(timezone.utc).isoformat(),
           "mode": mode, "lines": list(route.get("lines") or []),
           # The footsteps inside a transport answer are what let a walking limit be judged from the
           # frozen fact rather than from a re-measurement (app/replanning/feasibility.py:497).
           "walking_distance_m": route.get("walking_distance_m"),
           "source_url": "https://uri.amap.com/navigation?" + urlencode(
               {"from": f"{start[1]},{start[0]},{origin.name}", "to": f"{end[1]},{end[0]},{destination.name}",
                "mode": "walk" if mode == "WALK" else "bus", "coordinate": "gaode", "callnative": "0"})}
    row.update(_route_geometry_fields({**route, **row}, provider_call_id=call_id))
    task.setdefault("research_routes", []).append(row)
    task["research_routes"] = task["research_routes"][-16:]
    return row


def _candidate_id_for(task: dict, place: Place) -> str:
    for lead in task.get("research_places") or []:
        if isinstance(lead, dict) and str(lead.get("canonical_place_id") or "") == place.id:
            return str(lead.get("id") or "")
    provider, separator, tail = str(place.external_id or "").partition(":")
    return f"{provider}:{tail}" if separator else str(place.external_id or "")


WALKING_CAP_CODE = "MAX_WALKING_PER_LEG_M"


def _walking_cap_m(session: Session, journey: Journey, task: dict) -> int | None:
    """The traveller's own per-hop walking limit, read from where their words are kept.

    Two places, in this order, because both are real and they are not the same one:

    * a journey intent that already carries the structured row (`journey_intents.capabilities_json`) --
      the product parsed it at intake and this door must not re-guess what is recorded;
    * otherwise the words themselves: that intent's `source_text` plus what the traveller typed into
      this task, run through the one extractor the mission path also uses
      (`app/capabilities.py:605`, called from `app/agent/mission.py:294`).

    Measured on the walked database: the first-screen goal sentence lives in `journey_intents.source_text`
    while `capabilities_json` is still `[]`, and the goal task carries no goal key at all -- so a reader
    that only looked at the task finds nothing, which is the difference between a limit that exists and
    one that ever reaches the map door. 「每段步行不超过1公里」 yields `HARD {'max_m': 1000}` while
    「少走路」 yields a clarification with no number
    (trial/results/20261022_v3_human_chrome/caps_walk_extract-1.txt); a clause without a number is not
    a cap, so nothing here invents one.
    """

    def _limit(params) -> int | None:
        try:
            value = int((params or {})["max_m"])
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        return value if value > 0 else None

    words = [str(row.get("text") or "") for row in (task.get("conversation") or [])[-12:]
             if isinstance(row, dict) and row.get("role") == "user"]
    for intent in session.scalars(select(JourneyIntent).where(
            JourneyIntent.journey_id == journey.id, JourneyIntent.superseded_at.is_(None))):
        for item in json.loads(intent.capabilities_json or "[]"):
            if isinstance(item, dict) and str(item.get("code")) == WALKING_CAP_CODE:
                limit = _limit(item.get("params"))
                if limit is not None:
                    return limit
        if str(intent.source_text or "").strip():
            words.append(str(intent.source_text))
    for row in extract_capabilities_from_text(" ".join(words), scope="JOURNEY"):
        if str(row.get("code")) != WALKING_CAP_CODE:
            continue
        limit = _limit(row.get("params"))
        if limit is not None:
            return limit
    return None

def _mark_frozen_hop(task: dict, origin: Place, destination: Place, route: dict, cap_m: int) -> None:
    """Say on the researched row what this version of the plan actually froze for that hop.

    The drawer under 「高德转场路线」 lists what the Agent measured, so when the traveller's own walking
    limit moves a hop onto a bus, that list goes on saying 步行 · 3.4 公里 while the band above it says 已换成
    公共交通核实 -- measured on walk-113, where the drawer rows read WALK 3385 m / WALK 3512 m
    (trial/results/20261022_v3_human_chrome/walk-113-log.txt:68) against a stored attempt of
    `transit=4, replaced_long_walks=2, walking_cap_m=1000`.  A change the traveller asked for has to be
    visible where they can still open the thing it changed.  Nothing is invented here: every field is read
    off the row this press froze, and a hop with no researched row is left alone rather than given one.
    """
    origin_key = _candidate_id_for(task, origin)
    destination_key = _candidate_id_for(task, destination)
    seconds = route.get("duration_seconds")
    fields = {"walking_cap_m": int(cap_m), "frozen_mode": route.get("mode") or "WALK",
              "frozen_distance_m": route.get("distance_m"),
              "frozen_minutes": None if seconds is None else max(1, int(round(float(seconds) / 60.0))),
              "frozen_lines": list(route.get("lines") or [])}
    for row in task.get("research_routes") or []:
        if isinstance(row, dict) and str(row.get("from_place_id")) == origin_key \
                and str(row.get("to_place_id")) == destination_key:
            row.update(fields)


def _over_cap_walk(row: dict | None, cap_m: int | None) -> bool:
    """A walking answer the traveller said they would not take. An absent mode is WALK here, and that is
    a fact about this code (only the walking door ever wrote these rows before the transit leg landed)."""
    if row is None or cap_m is None:
        return False
    if str(row.get("mode") or "WALK").upper() != "WALK":
        return False
    try:
        return int(row.get("distance_m") or 0) > cap_m
    except (TypeError, ValueError):
        return False


def _replace_long_walk(session: Session, task: dict, origin: Place, destination: Place,
                       walked: dict, cap_m: int, arrival: datetime | str | None) -> dict | None:
    """Ask the public-transport door for that hop, once, and keep whichever answer the provider gives.

    If transit has no answer the walking fact stays -- evidence the provider gave is not discarded to
    please a limit -- and the hop is marked `over_cap_m` so the card can say the limit was exceeded
    instead of letting the traveller discover a 16-kilometre walk at the bus stop.
    """
    start = wgs84_to_gcj02(float(origin.latitude), float(origin.longitude))
    end = wgs84_to_gcj02(float(destination.latitude), float(destination.longitude))
    transit = _transit_leg(session, task, origin, destination, start, end, arrival)
    if transit is None:
        return {**walked, "over_cap_m": int(walked.get("distance_m") or 0)}
    walk_m = int(walked.get("distance_m") or 0)
    row = {"id": transit.get("provider_call_id") or str(uuid4()),
           "from_place_id": walked.get("from_place_id"), "to_place_id": walked.get("to_place_id"),
           "from_name": origin.name, "to_name": destination.name, "provider": "amap",
           "coordinate_system": "GCJ02", "distance_m": transit.get("distance_m"),
           "duration_seconds": transit.get("duration_seconds"),
           "captured_at": datetime.now(timezone.utc).isoformat(), "mode": "TRANSIT",
           "lines": list(transit.get("lines") or []), "replaced_walk_m": walk_m, "walking_cap_m": cap_m,
           "walking_distance_m": transit.get("walking_distance_m"),
           "source_url": "https://uri.amap.com/navigation?" + urlencode(
               {"from": f"{start[1]},{start[0]},{origin.name}", "to": f"{end[1]},{end[0]},{destination.name}",
                "mode": "bus", "coordinate": "gaode", "callnative": "0"})}
    row.update(
        _route_geometry_fields(
            {**transit, **row}, provider_call_id=transit.get("provider_call_id")
        )
    )
    return row


def freeze_routes(session: Session, journey: Journey, task: dict, plan: PlanVersion, task_id: str) -> dict:
    """Verify every walked edge, then freeze the whole set or nothing."""
    edges: list[dict] = []
    facts: list[tuple[str, str, dict]] = []
    cap_m = _walking_cap_m(session, journey, task)
    for origin_row, destination_row in used_edges(session, plan):
        origin = session.get(Place, str(origin_row.place_id))
        destination = session.get(Place, str(destination_row.place_id))
        if origin is None or destination is None:
            continue
        origin_key = _candidate_id(origin_row) or _candidate_id_for(task, origin)
        destination_key = _candidate_id(destination_row) or _candidate_id_for(task, destination)
        route = _stored_route(task, origin_key, destination_key)
        status = REUSED
        if route is None:
            route = _measure_now(session, task, origin, destination, arrival=destination_row.start_at)
            status = MEASURED if route is not None else UNAVAILABLE
        if route is not None:
            route = _orient_reused_route(route, origin_key, destination_key, origin, destination)
            route = {**route, **_route_geometry_fields(route, provider_call_id=route.get("id"))}
        if _over_cap_walk(route, cap_m):
            # Whether the number came from the Agent's own research row or from a call this press made,
            # the traveller's limit is read the same way, so a reused long walk is replaced too.
            route = _replace_long_walk(session, task, origin, destination, route, cap_m,
                                       destination_row.start_at)
            status = MEASURED
            _mark_frozen_hop(task, origin, destination, route, cap_m)
        minutes = None if route is None else max(1, int(round(float(route["duration_seconds"]) / 60.0)))
        if route is not None:
            facts.append((origin.id, destination.id, route))
        edges.append({"from_place_id": origin.id, "to_place_id": destination.id,
                      "from_name": origin.name, "to_name": destination.name, "status": status,
                      "minutes": minutes, "spans_night": not _same_day(origin_row, destination_row),
                      # A row written by the Agent's own research leg carries no mode, and the only thing
                      # that ever wrote one there is the walking door -- so an absent mode means WALK,
                      # which is a fact about this code, not a guess about the provider.
                      "mode": (route.get("mode") or "WALK") if route is not None else None,
                      # Set when this hop was walked further than the traveller's own limit and the
                      # transport door answered: the walk it replaces, and the limit it replaced for.
                      "replaced_walk_m": route.get("replaced_walk_m") if route else None,
                      "walking_cap_m": route.get("walking_cap_m") if route else None,
                      "over_cap_m": route.get("over_cap_m") if route else None,
                      "lines": list(route.get("lines") or []) if route is not None else [],
                      "distance_m": route.get("distance_m") if route else None,
                      "provider": route.get("provider") if route else None,
                      "source_url": route.get("source_url") if route else None,
                      "captured_at": route.get("captured_at") if route else None,
                       "geometry_status": route.get("geometry_status") if route else None,
                       "route_geometry": route.get("route_geometry") if route else None,
                       "geometry_provenance": route.get("geometry_provenance") if route else None,
                      "reason_code": None if route else (_refusal_reason(task, origin, destination)
                                                         or ("AMAP_NOT_CONFIGURED" if not settings.amap_web_key
                                                             else "PROVIDER_ROUTE_UNAVAILABLE"))})
    verified = len([row for row in edges if row["status"] != UNAVAILABLE])
    overnight = len([row for row in edges if row["spans_night"]])
    replaced = len([row for row in edges if row.get("replaced_walk_m")])
    over_cap = len([row for row in edges if row.get("over_cap_m")])
    frozen = bool(edges) and verified == len(edges)
    snapshot_id: str | None = None
    reason: str | None = None
    if not edges:
        rows_of_plan = list(session.scalars(select(Activity).where(Activity.plan_version_id == plan.id)))
        placed_rows = [row for row in rows_of_plan if row.place_id]
        # "Nothing to route" and "nothing is a place yet" reach the same empty edge list, and only one of
        # them is the traveller's planning problem.  Measured on a phone walk where six saved arrangements
        # carried no canonical place at all (`places` had no rows and all six `Activity.place_id` were null,
        # trial/results/20261022_v3_human_chrome/replan-probe-2-log.txt:14-22 read with
        # trial/human_walk/candidate_place_binding_probe_r1.py) while the card said
        # 「这版方案里没有相邻两站之间的转场要核实」 -- a sentence that sent the traveller to look for a
        # missing hop instead of the missing places.
        reason = "NO_PLACED_STOPS" if len(rows_of_plan) > 1 and len(placed_rows) < 2 else "NO_ROUTED_EDGES"
    elif frozen:
        try:
            capture = capture_mobility_snapshot(
                [(row[0], row[1]) for row in facts],
                primary=StoredAmapRoutes(facts),
                operation_key=f"goal-freeze:{plan.id}",
                captured_at=datetime.now(timezone.utc).isoformat(),
            )
        except MobilitySnapshotCaptureError:
            # The capture door refuses a pair it cannot serve; that is the answer, not a reason to
            # freeze a partial snapshot.
            frozen, reason = False, "MOBILITY_CAPTURE_REFUSED"
        else:
            snapshot = capture.snapshot
            plan.mobility_snapshot_id = snapshot.snapshot_id
            plan.mobility_evidence_json = json.dumps(snapshot.to_evidence(), ensure_ascii=False, sort_keys=True)
            snapshot_id = snapshot.snapshot_id
            # The to-do line for a hop was written when nobody had measured it.  Now every walked hop
            # has a provider fact frozen onto this plan, so leaving 转场路线 on the traveller's list
            # would ask them for something that already exists.  Only TRANSFER_ROUTE rows are dropped;
            # identity, opening and price rows stay, because freezing a walk proves none of those.
            explanation = json.loads(plan.explanation_json or "{}")
            kept = [row for row in (explanation.get("unresolved_facts") or [])
                    if not (isinstance(row, dict) and row.get("kind") == "TRANSFER_ROUTE")]
            if len(kept) != len(explanation.get("unresolved_facts") or []):
                explanation["unresolved_facts"] = kept
                plan.explanation_json = json.dumps(explanation, ensure_ascii=False)
            stored = (task.get("prepared_plan") or {}).get("result")
            if isinstance(stored, dict):
                stored["gaps"] = [row for row in (stored.get("gaps") or []) if row.get("kind") != "TRANSFER_ROUTE"]
                # The saved answer is what the card re-reads after a refresh.  Leaving
                # mobility_frozen=false there once the hops are frozen would make the screen lie.
                stored["mobility_frozen"] = True
                stored["mobility_snapshot_id"] = snapshot.snapshot_id
    elif verified:
        reason = "ROUTE_PARTIALLY_VERIFIED"
    else:
        reason = "ROUTE_UNAVAILABLE"
    # What this door just answered is also what the card has to say after the traveller reloads the page.
    # The frozen case already rewrites the stored answer above; a partial one used to write nothing, so
    # someone who pressed 核实并冻结今天的转场, watched three hops get measured, and refreshed came back to
    # 「当天的转场还没有向高德核实过」 with the refusal list empty -- measured on walk-83, where the band
    # read 转场已核实 3/4 at trial/results/20261022_v3_human_chrome/walk-83-log.txt:34 and the same card
    # after the reload read nothing at :54 (:55 for the emptied list).  This records the attempt: the
    # counts and the hops nobody answered.  `mobility_frozen` is untouched, so a half-measured plan still
    # cannot be described as frozen, and no new number is invented -- every field here came from `edges`.
    if edges:
        stored = (task.get("prepared_plan") or {}).get("result")
        if isinstance(stored, dict):
            stored["route_attempt"] = {
                "verified": verified, "total": len(edges), "overnight": overnight,
                "transit": len([row for row in edges if row.get("mode") == "TRANSIT"]),
                "replaced_long_walks": replaced, "over_cap_walks": over_cap, "walking_cap_m": cap_m,
                "frozen": frozen, "reason_code": reason,
                "unanswered": [{"from_name": row["from_name"], "to_name": row["to_name"],
                                "reason_code": row.get("reason_code")}
                               for row in edges if row["status"] == UNAVAILABLE][:32],
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }
    return {"journey_id": journey.id, "task_id": task_id, "plan_version_id": plan.id,
            "edges": edges, "verified": verified, "total": len(edges), "overnight": overnight,
            "transit": len([row for row in edges if row.get("mode") == "TRANSIT"]),
            "replaced_long_walks": replaced, "over_cap_walks": over_cap,
            "walking_cap_m": cap_m,
            "frozen": frozen, "mobility_snapshot_id": snapshot_id, "reason_code": reason}


@router.post(PATH, response_model=FreezeRoutesResult)
def freeze_plan_routes(journey_id: UUID, task_id: UUID, plan_version_id: UUID, request: Request,
                       response: Response,
                       idempotency_key: str = Header(alias="Idempotency-Key", min_length=1, max_length=160),
                       session: Session = Depends(get_session)):
    with journey_write_lock(str(journey_id)):
        _principal, member = resolve_journey_member_principal(request, session, journey_id=str(journey_id))
        journey = session.get(Journey, str(journey_id))
        if journey is None:
            raise HTTPException(404, "Journey not found")
        if member.traveler_id != journey.traveler_id or not member_has_capability(session, member, "JOURNEY_UPDATE"):
            raise HTTPException(403, "Journey owner update required")
        signature = canonical_request_signature({"task_id": str(task_id), "plan_version_id": str(plan_version_id),
                                                "actor": member.id})
        key = f"goal.freeze:{journey.id}:{idempotency_key}"
        existing = session.get(IdempotencyKey, key)
        if existing:
            if existing.request_hash != signature:
                raise HTTPException(409, "FREEZE_KEY_REUSE_CONFLICT")
            response.headers["Cache-Control"] = "private, no-store"
            return {**json.loads(existing.response_json), "idempotency_replay": True}
        journey, member, mission, intent, task = _require_task(session, journey, member, task_id, require_draft=False)
        plan = session.get(PlanVersion, str(plan_version_id))
        if plan is None or plan.journey_id != journey.id:
            raise HTTPException(404, "PLAN_NOT_IN_JOURNEY")
        explanation = json.loads(plan.explanation_json or "{}")
        if explanation.get("compose_source") != "SELECTED_GOAL_DRAFT" or \
                str(explanation.get("goal_task_id") or "") != str(mission.id):
            # This door only serves the candidate this task saved; it must not be able to freeze
            # evidence onto somebody else's plan version.
            raise HTTPException(403, "PLAN_NOT_FROM_GOAL_TASK_DRAFT")
        now = datetime.now(timezone.utc)
        answer = freeze_routes(session, journey, task, plan, str(mission.id))
        # The research step may have measured a hop just now, so the task owns the new rows.
        mission.intent_json = json.dumps(intent, ensure_ascii=False)
        session.add(IdempotencyKey(key=key, operation="goal.freeze-routes", request_hash=signature,
                                   response_status=200, response_json=json.dumps(answer, ensure_ascii=False),
                                   created_at=now.isoformat(), expires_at=(now + timedelta(days=7)).isoformat()))
        record_audit(session, action="goal.routes.frozen", entity_type="PlanVersion", entity_id=plan.id,
                     journey_id=journey.id, actor_type="traveler", actor_id=member.traveler_id,
                     after={"task_id": mission.id, "plan_version_id": plan.id, "frozen": answer["frozen"],
                            "verified": answer["verified"], "total": answer["total"],
                            "mobility_snapshot_id": answer["mobility_snapshot_id"]})
        session.commit()
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"
        return answer
