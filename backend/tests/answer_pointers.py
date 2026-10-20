"""One shared check for every answer that hands a URL back to a caller.

The static ruler `test_qoder_pointers_are_served_r1.py` reads source text and can only see a verb when
it sits in the same literal as the path. Most of these doors assemble the pointer at run time -- "close
the evidence gap with POST " + FREEZE_PATH.format(...) -- so what a traveller or Codex actually receives
is only visible from a real answer, and it arrives with the ids already substituted.

This helper therefore does not compare strings: it asks Starlette's own router whether it would route
that request, with that verb, to an endpoint. Re-implementing matching here would be a second router to
keep in sync -- the mistake this file exists to stop making.

Deliberately narrow: a pointer with no verb in the sentence is not accepted silently. A caller that is
told a path and not a method has to guess, which is how `.../places/{id}/identity` lived this long.
"""
from __future__ import annotations

import re
from typing import Any

VERB_AND_PATH = re.compile(r"(GET|POST|PUT|DELETE) (/api/v1/[^\s\"]+)")


def _scope(method: str, url: str) -> dict[str, Any]:
    path, _, query = url.partition("?")
    return {"type": "http", "http_version": "1.1", "method": method, "scheme": "http",
            "path": path, "raw_path": path.encode("utf-8"), "query_string": query.encode("utf-8"),
            "root_path": "", "headers": [], "client": ("127.0.0.1", 0), "server": ("127.0.0.1", 80)}


def routed(method: str, url: str) -> bool:
    """Would the shipped router send this request somewhere? Uses Starlette's own match."""
    from app.main import app as real_app

    scope = _scope(method, url)
    for route in real_app.router.routes:
        match, _child = route.matches(scope)
        if match.name == "FULL":
            return True
    return False


def served_methods(url: str) -> set[str]:
    """Which verbs the shipped router would actually answer for this URL.

    For a pointer handed over as a bare path -- the identity read's `media_path` is one -- there is no
    verb in the sentence to check, so this is the honest form of the same question: the path must be
    routed, and the caller must not have to guess which verb it answers.
    """
    from app.main import app as real_app

    path = url.partition("?")[0]
    answers: set[str] = set()
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        for route in real_app.router.routes:
            match, _child = route.matches(_scope(method, path))
            if match.name == "FULL":
                answers.add(method)
                break
    return answers


def assert_pointers_are_served(lines: list[str], *, expect: int | None = None) -> None:
    """Every pointer in `lines` names a verb and a URL the shipped router would route."""
    found: list[tuple[str, str]] = []
    for line in lines:
        match = VERB_AND_PATH.search(line)
        assert match, f"a pointer was handed to a caller with no verb in it: {line}"
        verb, url = match.group(1), match.group(2)
        # These sentences keep talking after the URL -- ".../mobility-freeze, or this round stays
        # gate.judged false with X" -- so clause-closing punctuation is trimmed rather than the
        # compare loosened, which would let a genuine typo through.
        url = url.rstrip(",.;:")
        found.append((verb, url))
        assert routed(verb, url), f"{verb} {url} is pointed at but the router sends it nowhere"
    if expect is not None:
        assert len(found) == expect, (found, lines)
