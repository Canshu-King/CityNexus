"""Which handler actually answers each of the two media doors -- a path can be registered and wrong.

`tests/test_qoder_ord0478_route_ownership.py` states the reason this file exists in this repo: a door
that exists, answers, and answers with somebody else's body is invisible to an existence check. The
same hazard is live on this branch, and here it is *my* code: both doors are registered by a loop over
`place_media_routes.router.routes` in `app/main.py`, which takes the path and the endpoint from the
same route object. A swapped decorator, a duplicated path, or a filtered loop leaves the served OpenAPI
document looking fine while the wrong handler answers -- and my own contract checks read that document.

So this file judges the other half of the pair, on the product app's own route table:

* each path resolves to exactly one route, and that route names the handler it is supposed to name;
* the two doors do not share a handler, and neither answers the other's path;
* both are GET-only, and neither is registered twice.

Nothing here opens a socket or writes a row. Two mutations make the assertions worth something: re-point
the identity decorator at the media path, and drop the media route out of the router -- each turns a
different格 red (`_media_route_ownership_mutation_1019bl.py` holds the readings).
"""

from __future__ import annotations

from fastapi.routing import APIRoute

from app import place_media_routes
from app.main import app

MEDIA_PATH = "/api/v1/journeys/{journey_id}/places/{place_id}/media"
IDENTITY_PATH = "/api/v1/journeys/{journey_id}/place-identity"

OWNERSHIP = {
    MEDIA_PATH: "journey_place_media",
    IDENTITY_PATH: "journey_place_identity",
}


def routes_for(path: str) -> list[APIRoute]:
    return [route for route in app.routes
            if isinstance(route, APIRoute) and route.path == path]


def test_each_door_is_registered_exactly_once_and_by_get():
    for path in OWNERSHIP:
        found = routes_for(path)
        assert len(found) == 1, f"{path} is registered {len(found)} times, expected one door"
        assert found[0].methods == {"GET"}, f"{path} answers {sorted(found[0].methods)}, expected GET only"


def test_each_path_resolves_to_the_handler_that_owns_it():
    for path, handler in OWNERSHIP.items():
        found = routes_for(path)
        assert found, f"{path} is not in app.routes at all"
        name = found[0].endpoint.__name__
        assert name == handler, f"{path} is answered by {name}, which is the wrong owner"


def test_the_two_doors_do_not_answer_for_each_other():
    handlers = {routes_for(path)[0].endpoint for path in OWNERSHIP}
    assert len(handlers) == 2, "both doors resolve to one handler -- one of them is a duplicate"
    names = {route.endpoint.__name__ for route in app.routes
             if isinstance(route, APIRoute) and route.path in OWNERSHIP}
    assert names == set(OWNERSHIP.values()), names


def test_the_registration_loop_in_main_is_what_brought_them():
    """`app/main.py` registers plain routes rather than including the router, so prove the copy is real."""
    mounted = {route.path: route.endpoint for route in app.routes if isinstance(route, APIRoute)}
    for route in place_media_routes.router.routes:
        assert isinstance(route, APIRoute)
        assert mounted.get(route.path) is route.endpoint, (
            f"{route.path} is in the router but the app answers it with another handler")
