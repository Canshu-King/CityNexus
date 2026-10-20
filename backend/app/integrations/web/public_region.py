"""The one public-region contract shared by source research.

A Journey's `city_code` is a CityNexus identifier, not a place name: V8 mints
`CN-XIAMEN`, Revolution's FirstLook mints random `CN-RV-...` codes, and the demo
mints `CNX-DEMO`.  Sending any of those to a public provider asks it for a
string no traveller ever typed.  This module mirrors Codex's
`goal_artifacts.public_city_label` contract exactly:

  * `CN-RV-*` carries the user's explicit region in the FirstLook title format
    (`厦门 · 2日行程`); a title that does not match is *unknown*, never guessed;
  * other codes go through the existing resolver-label guard, which refuses a
    label that still carries an internal prefix;
  * known non-geographic codes (`CNX-DEMO`, `TEST`, ...) are unknown.

An unknown region is a named state the caller reports; it is not permission to
send a made-up query.
"""

from __future__ import annotations

import re

from app.integrations.discovery.real_city import _resolver_city_label

REGION_CONFIRMED = "JOURNEY_PUBLIC_REGION"
REGION_PENDING = "PUBLIC_REGION_UNCONFIRMED"

_FIRSTLOOK_TITLE = re.compile(r"(.{1,60}?)\s*·\s*\d{1,2}日行程")
_NON_PUBLIC_CODES = frozenset({"CNX-DEMO", "DEMO", "TEST", "UNKNOWN", "NONE"})
_INTERNAL_CODE = re.compile(r"\b(?:CN|CNX|JP|SG|TH)-[A-Z0-9][A-Z0-9-]{1,}\b", re.IGNORECASE)
_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)


def public_city_label(journey) -> str:
    """Return the public region a signed Journey may send to a provider, or "".

    Mirrors Codex PR #23 `goal_artifacts.public_city_label`.  Keep the two in
    step: a divergence here is a query one branch sends and the other refuses.
    """

    code = str(getattr(journey, "city_code", "") or "").strip()
    normalized_code = code.upper().replace("_", "-")
    if normalized_code in _NON_PUBLIC_CODES:
        return ""
    if normalized_code.startswith("CN-RV-"):
        # FirstLook persists the explicit region intake in this title shape.  A
        # free-form custom title or personal goal is never a geocoder query.
        match = _FIRSTLOOK_TITLE.fullmatch(str(getattr(journey, "title", "") or "").strip())
        return match.group(1).strip() if match else ""
    try:
        return _resolver_city_label(code)
    except ValueError:
        return ""


def sanitize_public_topic(value: str) -> str:
    """Reject a topic that carries an internal identifier or control characters.

    The model may name a public subject ("古村落", "当地小吃"); it may not smuggle
    a Journey UUID, an internal city code, or a member preference into a public
    search.  The caller turns a refusal into a named 422.
    """

    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not 2 <= len(text) <= 120:
        raise ValueError("PUBLIC_TOPIC_INVALID")
    if _INTERNAL_CODE.search(text) or _UUID.search(text):
        raise ValueError("PUBLIC_TOPIC_CARRIES_INTERNAL_ID")
    if any(ord(character) < 32 for character in text):
        raise ValueError("PUBLIC_TOPIC_INVALID")
    return text


def build_public_topic_query(topic: str, region: str) -> str:
    """One source-lead query: public region + cleaned subject, nothing private."""

    if not region:
        raise ValueError(REGION_PENDING)
    return f'"{topic}" {region} official site opening hours source'.strip()
