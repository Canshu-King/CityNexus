"""bw245: when plan_authority_blocker refuses from the sealed-envelope arm,
record the live local state that made that arm fire.

Observation only.  The plugin never mutates product state.  It re-reads the
product's own predicates (_place_has_unresolved_opening / _cost) on the Place
rows it is already holding, and dumps the raw field values beside them so the
two can be cross-checked by a reader.
"""

import io
import json
import os
import sys
import threading
from collections import Counter

TARGET_FILE = "app\\services.py"
TARGET_FUNC = "plan_authority_blocker"
SEALED_ARM_LINE = 799

_here = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_here))
# Two arms of this probe run against the same ruler, so each arm needs its own
# file.  Without the tag the second run silently overwrote the first reading.
TAG = os.getenv("CITYNEXUS_PROBE_RECEIPT_TAG", "v13")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw245-sealed-arm-state-%s.txt" % TAG)

_records = []
_current = {"nodeid": None}


def _place_rows(places):
    from app import services

    rows = []
    for place in places:
        meta = {}
        try:
            meta = json.loads(place.metadata_json or "{}") if place.metadata_json else {}
        except Exception:
            meta = {"__metadata_parse_error__": True}
        opening = {}
        try:
            opening = (json.loads(place.opening_hours_json or "{}")
                       if place.opening_hours_json else {})
        except Exception:
            opening = {"__opening_parse_error__": True}
        cost_evidence = meta.get("cost_evidence")
        rows.append({
            "provider_key": str(place.provider_key),
            "name": str(place.name)[:40],
            "meta_authority_envelope": str(meta.get("authority_envelope") or ""),
            "opening_status": str(opening.get("status") or "UNKNOWN").upper(),
            "opening_has_key": "status" in opening,
            "cost_evidence_present": isinstance(cost_evidence, dict),
            "cost_status": (str(cost_evidence.get("status") or "UNKNOWN").upper()
                            if isinstance(cost_evidence, dict) else ""),
            "cost_amount_minor_none": (cost_evidence.get("amount_minor") is None
                                       if isinstance(cost_evidence, dict) else None),
            "product_opening_unresolved": bool(
                services._place_has_unresolved_opening(place)),
            "product_cost_unresolved": bool(
                services._place_has_unresolved_cost(place)),
        })
    return rows


def _snapshot(frame):
    local = frame.f_locals
    places = list(local.get("used_content_places") or [])
    return {
        "nodeid": _current["nodeid"],
        "line": frame.f_lineno,
        "used_place_id_count": len(list(local.get("used_unique") or [])),
        "content_place_count": len(places),
        "sealed": bool(local.get("sealed")),
        "coursework_estimate": bool(local.get("coursework_estimate")),
        "cost_unknown_mode": bool(local.get("cost_unknown_mode")),
        "authority_state": str((local.get("explanation") or {}).get("authority_state") or ""),
        "authority_envelope": str((local.get("explanation") or {}).get("authority_envelope") or ""),
        "places": _place_rows(places),
    }


def _trace_inner(frame, event, arg):
    if event == "return":
        result = arg[0] if isinstance(arg, tuple) else arg
        if isinstance(result, str):
            if frame.f_lineno == SEALED_ARM_LINE:
                _records.append(_snapshot(frame))
            else:
                _records.append({"nodeid": _current["nodeid"],
                                 "line": frame.f_lineno, "places": None})
    return _trace_inner


def _trace(frame, event, arg):
    code = frame.f_code
    if code.co_name != TARGET_FUNC or not code.co_filename.endswith(TARGET_FILE):
        return None
    if event == "call":
        return _trace_inner
    return None


def pytest_runtest_logreport(report):
    if report.when == "setup":
        _current["nodeid"] = report.nodeid


def pytest_configure(config):
    threading.settrace(_trace)
    if hasattr(threading, "settrace_all_threads"):
        threading.settrace_all_threads(_trace)
    sys.settrace(_trace)


def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None)
    threading.settrace_all_threads(None)
    sealed = [row for row in _records if row.get("places") is not None]
    other = [row for row in _records if row.get("places") is None]
    lines = [
        "SEALED-ARM STATE PROBE bw245",
        "TARGET %s :: %s  return line %d" % (TARGET_FILE, TARGET_FUNC, SEALED_ARM_LINE),
        "REFUSALS_RECORDED %d (sealed arm %d, other arms %d)"
        % (len(_records), len(sealed), len(other)),
    ]
    if not sealed:
        lines.append("NO_SEALED_ARM_REFUSAL recorded - nothing to attribute")
        _write(lines)
        return

    shape = Counter()
    for row in sealed:
        dims = []
        for place in row["places"]:
            opening = "O?" if place["product_opening_unresolved"] else "O"
            cost = "C?" if place["product_cost_unresolved"] else "C"
            dims.append("%s%s" % (opening, cost))
        shape[(row["sealed"], row["coursework_estimate"], row["cost_unknown_mode"],
               tuple(sorted(set(dims))))] += 1
    lines.append("ARM_STATE SHAPE (sealed, coursework, cost_unknown, per-place dims) -> refusals")
    for key, count in shape.most_common():
        lines.append("  sealed=%s coursework=%s cost_unknown=%s %s  <- %d"
                     % (key[0], key[1], key[2], " ".join(key[3]), count))

    env_names = Counter()
    opening_status = Counter()
    opening_has_key = Counter()
    cost_present = Counter()
    cost_status = Counter()
    cost_amount_none = Counter()
    seen = set()
    for row in sealed:
        for place in row["places"]:
            ref = (row["nodeid"], place["provider_key"], place["name"])
            if ref in seen:
                continue
            seen.add(ref)
            env_names[place["meta_authority_envelope"] or "<absent>"] += 1
            opening_status[place["opening_status"]] += 1
            opening_has_key["status key present" if place["opening_has_key"]
                            else "status key absent"] += 1
            cost_present["cost_evidence present" if place["cost_evidence_present"]
                         else "cost_evidence absent"] += 1
            cost_status[place["cost_status"] or "<none>"] += 1
            cost_amount_none[str(place["cost_amount_minor_none"])] += 1
    lines.append("DISTINCT PLACE ROWS READ %d" % len(seen))
    for label, counter in (
        ("metadata authority_envelope", env_names),
        ("opening_hours_json status", opening_status),
        ("opening status key", opening_has_key),
        ("cost_evidence", cost_present),
        ("cost_evidence status", cost_status),
        ("cost amount_minor is None", cost_amount_none),
    ):
        lines.append("%s: %s" % (label, json.dumps(
            dict(counter.most_common()), sort_keys=False, ensure_ascii=False)))

    lines.append("AUTHORITY_STATE ON THE PLAN")
    states = Counter(row["authority_state"] or "<absent>" for row in sealed)
    for key, count in states.most_common():
        lines.append("  %-32s %d" % (key, count))
    envelopes = Counter(row["authority_envelope"] or "<absent>" for row in sealed)
    lines.append("PLAN authority_envelope: %s" % json.dumps(
        dict(envelopes.most_common()), sort_keys=False, ensure_ascii=False))

    lines.append("FIRST THREE REFUSALS IN FULL")
    for row in sealed[:3]:
        lines.append("  %s used=%d content=%d sealed=%s" % (
            row["nodeid"], row["used_place_id_count"], row["content_place_count"],
            row["sealed"]))
        for place in row["places"]:
            lines.append("    %s | %s | envelope=%s | opening=%s | cost_present=%s "
                         "cost=%s | amount_minor_none=%s | product says O?=%s C?=%s"
                         % (place["provider_key"][:28], place["name"],
                            place["meta_authority_envelope"] or "<absent>",
                            place["opening_status"], place["cost_evidence_present"],
                            place["cost_status"] or "<none>",
                            place["cost_amount_minor_none"],
                            place["product_opening_unresolved"],
                            place["product_cost_unresolved"]))
    lines.append("BY_TEST distinct tests that refused from the sealed arm: %d"
                 % len(set(row["nodeid"] for row in sealed)))
    for nodeid in sorted(set(row["nodeid"] for row in sealed)):
        lines.append("  %s" % nodeid)
    _write(lines)


def _write(lines):
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines[:26]:
        print(line)
    print("WROTE %s" % RECEIPT)
