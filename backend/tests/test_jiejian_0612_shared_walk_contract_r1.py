# -*- coding: utf-8 -*-
"""ORD-0612: before/after contract test for the untrusted shared-walk parser.

The order asks for the shape "remove the rule and this file goes red", so every rule the module
carries gets exactly one test of its own and each test names the rule it locks.  Nothing here
refuses an invention the parser already made: the module ships with zero callers on the line, so
the only thing worth pinning is that it never trusts sender-supplied text, never echoes it back,
and never lets a browser relabel a public OSM identity.
"""
from __future__ import annotations

import pytest

from app.execution.shared_walk import (
    MAX_SHARED_WALK_TEXT,
    SharedWalkObject,
    SharedWalkParseError,
    canonical_osm_object_url,
    normalize_osm_object_url,
    parse_shared_walk_text,
    validate_shared_walk_objects,
)

NODE = "https://www.openstreetmap.org/node/1234567"
WAY = "https://www.openstreetmap.org/way/7654321"
PASTE = f"meet at {NODE} then {WAY}"


def _code(run):
    with pytest.raises(SharedWalkParseError) as caught:
        run()
    return caught.value


# ---- the identity half ---------------------------------------------------------------

def test_canonical_url_accepts_the_three_public_kinds() -> None:
    assert canonical_osm_object_url("Node", "42") == "https://www.openstreetmap.org/node/42"
    assert canonical_osm_object_url("way", "42") == "https://www.openstreetmap.org/way/42"
    assert canonical_osm_object_url("relation", "42") == "https://www.openstreetmap.org/relation/42"


def test_leading_zero_identity_is_refused_not_repaired() -> None:
    # OSM ids are unsigned integers written without a leading zero; accepting "042" would let two
    # spellings name one object and then be treated as two different stops. Both doors must refuse:
    # the identity builder and the URL path parser, which carry separate patterns.
    assert _code(lambda: canonical_osm_object_url("node", "042")).code == "INVALID_OSM_IDENTITY"
    assert _code(lambda: canonical_osm_object_url("node", "0")).code == "INVALID_OSM_IDENTITY"
    assert _code(lambda: canonical_osm_object_url("building", "42")).code == "INVALID_OSM_IDENTITY"
    assert _code(lambda: normalize_osm_object_url(
        "https://www.openstreetmap.org/node/042")).code == "INVALID_OSM_IDENTITY"
    assert _code(lambda: parse_shared_walk_text(
        "https://www.openstreetmap.org/node/042 https://www.openstreetmap.org/way/7")).code == "INVALID_OSM_IDENTITY"


def test_non_https_and_delegated_hosts_are_refused() -> None:
    assert _code(lambda: normalize_osm_object_url("http://www.openstreetmap.org/node/42")).code == "INVALID_SHARED_URL"
    assert _code(lambda: normalize_osm_object_url("https://evil.example/node/42")).code == "INVALID_SHARED_URL"
    assert _code(lambda: normalize_osm_object_url("https://openstreetmap.org.evil.example/node/42")).code == "INVALID_SHARED_URL"


def test_port_credentials_query_and_fragment_cannot_ride_the_link() -> None:
    for url in (
        "https://www.openstreetmap.org:8443/node/42",
        "https://traveller@www.openstreetmap.org/node/42",
        "https://www.openstreetmap.org/node/42?token=x",
        "https://www.openstreetmap.org/node/42#map=17/1/2",
    ):
        assert _code(lambda u=url: normalize_osm_object_url(u)).code == "INVALID_SHARED_URL"


def test_sentence_punctuation_after_a_link_is_not_part_of_the_url() -> None:
    objects = parse_shared_walk_text(f"walk: {NODE}. Then {WAY}.")
    assert [(o.osm_type, o.osm_id) for o in objects] == [("node", "1234567"), ("way", "7654321")]


# ---- the "exactly two" half ----------------------------------------------------------

def test_one_link_is_not_a_walk() -> None:
    assert _code(lambda: parse_shared_walk_text(f"just {NODE}")).code == "EXACTLY_TWO_OSM_LINKS_REQUIRED"


def test_three_links_are_not_a_walk_either() -> None:
    three = PASTE + f" and https://www.openstreetmap.org/relation/99"
    assert _code(lambda: parse_shared_walk_text(three)).code == "EXACTLY_TWO_OSM_LINKS_REQUIRED"


def test_the_validated_list_must_hold_exactly_two_objects() -> None:
    # "at least two" is not the rule: a three-stop paste is a different promise than a walk, and
    # accepting it would silently drop or duplicate a leg downstream.
    one = [{"osm_type": "node", "osm_id": "42", "source_url": "https://www.openstreetmap.org/node/42"}]
    three = one + [
        {"osm_type": "way", "osm_id": "7", "source_url": WAY},
        {"osm_type": "relation", "osm_id": "9", "source_url": "https://www.openstreetmap.org/relation/9"},
    ]
    assert _code(lambda: validate_shared_walk_objects(one)).code == "EXACTLY_TWO_OBJECTS_REQUIRED"
    assert _code(lambda: validate_shared_walk_objects(three)).code == "EXACTLY_TWO_OBJECTS_REQUIRED"


def test_two_identical_objects_are_refused_as_not_a_walk() -> None:
    pair = [
        {"osm_type": "node", "osm_id": "42", "source_url": "https://www.openstreetmap.org/node/42"},
        {"osm_type": "node", "osm_id": "42", "source_url": "https://www.openstreetmap.org/node/42"},
    ]
    assert _code(lambda: validate_shared_walk_objects(pair)).code == "DUPLICATE_OSM_OBJECT"


# ---- the sender-must-not-relabel half ------------------------------------------------

def test_a_browser_relabelled_identity_is_refused() -> None:
    # The link is public and canonical, but the sender swapped which identity it claims. Trusting
    # that pair would let one place be recorded as another traveller's stop.
    pair = [
        {"osm_type": "way", "osm_id": "999", "source_url": "https://www.openstreetmap.org/node/42"},
        {"osm_type": "way", "osm_id": "7", "source_url": WAY},
    ]
    assert _code(lambda: validate_shared_walk_objects(pair)).code == "OSM_IDENTITY_MISMATCH"


def test_a_non_object_name_in_an_otherwise_clean_url_is_refused() -> None:
    assert _code(lambda: normalize_osm_object_url("https://www.openstreetmap.org/node")).code == "INVALID_OSM_IDENTITY"


# ---- the never-import-private-data half ----------------------------------------------

def test_credential_shaped_text_is_refused_before_parsing() -> None:
    for marker in ("Bearer abcdef", "journey_id: 7", "foreground_gps on", "cookie: a=b", "password=hunter2"):
        text = f"{NODE} {marker} {WAY}"
        assert _code(lambda t=text: parse_shared_walk_text(t)).code == "PRIVATE_DATA_IN_SHARED_TEXT"


def test_a_token_shaped_run_is_refused_even_without_a_keyword() -> None:
    jwt_like = "eyJ" + "a" * 30 + "." + "b" * 15
    text = f"{NODE} {jwt_like} {WAY}"
    assert _code(lambda t=text: parse_shared_walk_text(t)).code == "PRIVATE_DATA_IN_SHARED_TEXT"


def test_control_characters_and_angle_brackets_are_refused() -> None:
    for text in (f"{NODE}\x07 x {WAY}", f"<b>{NODE}</b> {WAY}", f"{NODE}\x00 {WAY}"):
        assert _code(lambda t=text: parse_shared_walk_text(t)).code == "UNSAFE_SHARED_TEXT"


def test_empty_and_oversized_pastes_are_refused_without_scan() -> None:
    assert _code(lambda: parse_shared_walk_text("")).code == "SHARED_TEXT_TOO_LARGE"
    big = PASTE + (" " * MAX_SHARED_WALK_TEXT)
    assert _code(lambda: parse_shared_walk_text(big)).code == "SHARED_TEXT_TOO_LARGE"


# ---- the refusal must not repeat what was pasted --------------------------------------

def test_a_refusal_never_reflects_the_pasted_text_back() -> None:
    secret = "https://www.openstreetmap.org/node/abc SECRET-BEARING-TEXT"
    err = _code(lambda: parse_shared_walk_text(f"{secret} {WAY}"))
    assert "SECRET-BEARING-TEXT" not in str(err)
    assert "abc" not in str(err)
    assert err.code in {
        "INVALID_SHARED_URL", "INVALID_OSM_IDENTITY", "EXACTLY_TWO_OSM_LINKS_REQUIRED",
        "SHARED_TEXT_TOO_LARGE", "UNSAFE_SHARED_TEXT", "PRIVATE_DATA_IN_SHARED_TEXT",
    }


def test_the_happy_path_returns_public_identities_and_canonical_sources() -> None:
    objects = parse_shared_walk_text(PASTE)
    assert objects == [
        SharedWalkObject(osm_type="node", osm_id="1234567", source_url=NODE),
        SharedWalkObject(osm_type="way", osm_id="7654321", source_url=WAY),
    ]
    assert {o.source_url for o in objects} == {NODE, WAY}
