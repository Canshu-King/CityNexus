"""每扇门交回给调用者的 URL，必须是真有人接的路由 —— 一条尺罩住整族，不再靠一枚一枚手动对。

起因：第一百零七笔之前，`from-slots` 被拒时交回的「先去按身份读」指到一枚没有任何路由接的路径
（`.../places/{place_id}/identity`），而当时那格的断言只读「identity」这个字样，所以假指路能绿。
那格现在自己盯住了身份读；这一支把同一条规矩推到整族：凡是我这几枚模块里当指针交出去的路径模板，
都必须 ① 是 `app.main.app` 真注册的路由（含方法），② 出现在契约 `paths` 里。

它不测行为，只测「我说的话能不能被按下去」——这正是 Codex 接入时唯一必须先成立的事实。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

BACKEND = Path(__file__).resolve().parents[1]
APP = BACKEND / "app"
CONTRACT = BACKEND.parent / "contracts" / "openapi.yaml"

#: The modules whose answers hand URLs back to a caller. Anything named here is held to the rule.
MODULES = ["plan_from_slots.py", "plan_submission.py", "plan_evidence.py", "plan_delta.py",
           "departure_commit.py", "collective_consent.py", "place_media_routes.py"]

#: A pointer can sit inside a sentence ("read GET /api/v1/...") or be the whole literal, so the scan
#: is over the source text, not over quoted-string boundaries.
TEMPLATE = re.compile(r"/api/v1/[A-Za-z0-9_/.\-]*\{[a-z_]+\}[A-Za-z0-9_/.\{}\-]*")


def _templates() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for name in MODULES:
        source = (APP / name).read_text(encoding="utf-8")
        found[name] = set(TEMPLATE.findall(source))
    return found


@pytest.fixture(scope="module")
def served() -> set[tuple[str, str]]:
    from app import main as main_module

    pairs: set[tuple[str, str]] = set()
    for route in getattr(main_module.app, "routes", []):
        path = getattr(route, "path", None)
        if path is None:
            continue
        for method in (getattr(route, "methods", None) or set()):
            pairs.add((method.upper(), path))
    return pairs


@pytest.fixture(scope="module")
def documented() -> set[str]:
    document = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    return {"/api/v1" + path for path in document["paths"]}


def _shape(path: str) -> tuple[str, ...]:
    """The path with every `{...}` segment replaced by one marker.

    A pointer is pressable when the segments line up: FastAPI does not care what a path parameter is
    *called*, so a literal string compare would go red over a name and stay silent over a genuinely
    missing door. Both mistakes are the one this ruler exists to prevent.
    """
    return tuple("{param}" if segment.startswith("{") else segment for segment in path.split("/"))


def test_the_pointers_this_family_hands_back_are_all_real(served, documented):
    """Every pointer is gathered and checked; an empty denominator itself is a failure."""
    total = {path for paths in _templates().values() for path in paths}
    assert total, "no URL template found in the named modules -- the ruler stopped covering anything"
    assert len(total) >= 6, sorted(total)
    served_shapes = {_shape(path) for _method, path in served}
    missing_in_app = sorted(path for path in total if _shape(path) not in served_shapes)
    assert not missing_in_app, (
        "these pointers are handed to callers but no route serves them: " + ", ".join(missing_in_app))
    documented_shapes = {_shape(path) for path in documented}
    missing_in_contract = sorted(path for path in total if _shape(path) not in documented_shapes)
    assert not missing_in_contract, (
        "these pointers are served but the contract does not carry them: "
        + ", ".join(missing_in_contract))


@pytest.mark.parametrize("module_name", MODULES)
def test_each_pointer_a_module_hands_back_is_served_and_documented(module_name, served, documented):
    paths = _templates()[module_name]
    assert paths, f"{module_name} hands back no URL -- check the template regex still matches it"
    served_shapes = {_shape(path) for _method, path in served}
    documented_shapes = {_shape(path) for path in documented}
    for path in sorted(paths):
        assert _shape(path) in served_shapes, (module_name, path)
        assert _shape(path) in documented_shapes, (module_name, path, sorted(documented)[:3])


def _method_pointers() -> dict[str, set[tuple[str, str]]]:
    """Pointers that name the verb too -- "read GET ...", "select POST ...".

    Same path template as above, so a line-wrapped literal cannot be mistaken for a dead link (the
    shape rule, not a stricter one, is what this file checks).
    """
    pattern = re.compile(r"(GET|POST|PUT|DELETE)\s+(" + TEMPLATE.pattern + ")")
    found: dict[str, set[tuple[str, str]]] = {}
    for name in MODULES:
        source = (APP / name).read_text(encoding="utf-8")
        found[name] = set(pattern.findall(source))
    return found


def test_a_pointer_that_names_a_verb_names_one_that_route_answers(served):
    """The method dimension, added because without it a GET pointer onto a POST-only door is green.

    Denominator first: the arm would pass vacuously if no module spelled out a verb.
    """
    pairs = {pair for found in _method_pointers().values() for pair in found}
    assert len(pairs) >= 5, sorted(pairs)
    answered = {(method, _shape(path)) for method, path in served}
    wrong = sorted((method, path) for method, path in pairs
                   if (method, _shape(path)) not in answered)
    assert not wrong, "these verbs are named at callers but the route does not answer them: " + repr(wrong)


def test_the_method_arm_can_bite(served):
    """A named control: flip the verb on a real GET pointer and the served set must not carry it.

    Without this, "0 wrong" above could mean the arm is blind rather than the code clean.
    """
    answered = {(method, _shape(path)) for method, path in served}
    identity = "/api/v1/journeys/{journey_id}/place-identity"
    assert ("GET", _shape(identity)) in answered, sorted(answered)[:5]
    assert ("POST", _shape(identity)) not in answered, "this door answers POST too -- pick another control"


def test_the_identity_pointer_this_family_used_to_get_wrong_is_now_a_served_route(served):
    """The named negative control: the dead path must not be what any module hands out.

    Pinned because the old constant was plausible-looking and only a press would have shown it: the
    dead form carried `places/{place_id}/identity`, the live one is `place-identity?lead=`.
    """
    dead = "/api/v1/journeys/{journey_id}/places/{place_id}/identity"
    assert dead not in {path for _method, path in served}, dead
    for name in MODULES:
        assert dead not in _templates()[name], (name, dead)
    live = "/api/v1/journeys/{journey_id}/place-identity"
    assert live in {path for _method, path in served}, sorted(served)[:3]
