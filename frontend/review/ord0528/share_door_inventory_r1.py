"""ORD-0528 cell 1 -- what is connected to what, read door by door off the running server.

The question this answers is the one the order opens with: does the poster's download outlet have any
connection to the share family? "No connection" is a claim about specific addresses, so each one is
asked and its real status printed, and the claim is made from the printed numbers:

  * every address a poster-download door *could* live at, plus the two names this order did not use;
  * the four share-family doors, in the order a share actually travels (create -> list -> present ->
    revoke), so the statuses are read as a walk and not as four isolated 2xx;
  * one negative control that must not answer 404 for the wrong reason: a door that exists and is
    asked with a token it has never seen. If that one also came back 404, "404 means no such door"
    would be a reading about nothing.

Nothing here is a predicted status: every cell is the number the socket answered, in this run.
"""
import json
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:%s/api/v1"
JOURNEY = "22222222-2222-4222-8222-222222222222"
TRAVELER = "11111111-1111-4111-8111-111111111111"
PORT = sys.argv[1] if len(sys.argv) > 1 else "8768"
OUT = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/share_door_inventory_%s.json" % PORT


def ask(port, method, path, body=None):
    request = urllib.request.Request(API % port + path, method=method)
    request.add_header("Content-Type", "application/json")
    data = None if body is None else json.dumps(body).encode("utf-8")
    try:
        with urllib.request.urlopen(request, data, timeout=20) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        payload = error.read()
        parsed = None
        try:
            parsed = json.loads(payload)
        except Exception:  # noqa: BLE001 - a non-JSON error body is still a status
            pass
        return {
            "http_status": error.code,
            "bytes": len(payload),
            "reason_code": (parsed or {}).get("error", {}).get("reason_code") if parsed else None,
        }
    except Exception as error:  # noqa: BLE001
        return {"http_status": "UNREACHABLE", "error": repr(error)[:160]}
    parsed = None
    try:
        parsed = json.loads(payload)
    except Exception:  # noqa: BLE001
        parsed = None
    return {
        "http_status": response.status,
        "bytes": len(payload),
        "token_chars": len(parsed["token"]) if isinstance(parsed, dict) and isinstance(parsed.get("token"), str) else None,
        "rows": len(parsed) if isinstance(parsed, list) else None,
    }


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "8768"
    report = {"api_port": port, "journey_id": JOURNEY, "poster_side": {}, "share_side": {}, "controls": {}}

    # ---- the poster's own side: is there any door a long picture could be pushed through?
    for name, method, path in [
        ("POST /journeys/{id}/poster", "POST", "/journeys/%s/poster" % JOURNEY),
        ("POST /journeys/{id}/poster-shares", "POST", "/journeys/%s/poster-shares" % JOURNEY),
        ("POST /journeys/{id}/poster/share", "POST", "/journeys/%s/poster/share" % JOURNEY),
        ("GET /posters", "GET", "/posters"),
    ]:
        report["poster_side"][name] = ask(port, method, path, body={})

    # ---- the contract, read live rather than from a file: does the word appear at all?
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%s/openapi.json" % port, timeout=30
        ) as spec_response:
            spec = json.loads(spec_response.read())
            spec_status = spec_response.status
        paths = spec.get("paths", {})
        report["controls"]["openapi_http_status"] = spec_status
        report["controls"]["openapi_path_count"] = len(paths)
        report["controls"]["openapi_paths_holding_poster"] = sorted(p for p in paths if "poster" in p.lower())
        report["controls"]["openapi_paths_holding_share"] = sorted(p for p in paths if "share" in p.lower())
    except Exception as error:  # noqa: BLE001
        report["controls"]["openapi"] = "UNREADABLE %s" % repr(error)[:160]

    # ---- the share family, walked
    created = ask(port, "POST", "/journeys/%s/share-grants" % JOURNEY,
                  body={"visibility": "LINK_READ", "created_by": TRAVELER, "expires_at": None})
    report["share_side"]["POST share-grants"] = created
    token = None
    grant_id = None
    if created.get("http_status") == 200 or created.get("http_status") == 201:
        with urllib.request.urlopen(
            urllib.request.Request(API % port + "/journeys/%s/share-grants" % JOURNEY,
                                   headers={"Content-Type": "application/json"}),
            timeout=20,
        ) as response:
            payload = json.loads(response.read())
        newest = payload[-1]
        token = newest["token"]
        grant_id = newest["id"]
    report["share_side"]["GET share-grants"] = ask(port, "GET", "/journeys/%s/share-grants" % JOURNEY)
    report["share_side"]["GET /shared/journeys/{token}"] = (
        ask(port, "GET", "/shared/journeys/%s" % token) if token else {"http_status": "NOT_REACHED_BY_LANE",
                                                                       "why": "no grant was created to present"}
    )
    report["controls"]["unknown_token"] = ask(port, "GET", "/shared/journeys/%s" % ("z" * 32))
    if token and grant_id:
        report["share_side"]["POST share-grants/{id}/revoke"] = ask(
            port, "POST", "/journeys/%s/share-grants/%s/revoke" % (JOURNEY, grant_id), body={}
        )
        report["controls"]["revoked_token_presented"] = ask(port, "GET", "/shared/journeys/%s" % token)
    else:
        report["controls"]["revoked_token_presented"] = {"http_status": "NOT_REACHED_BY_LANE",
                                                        "why": "no grant to revoke"}
    # the poster's download outlet on the client sends nothing: proved in the browser arm, and here the
    # address a "poster share" would have had to live at is asked so the absence is a status, not a guess
    report["poster_side"]["GET /shared/journeys/{token}/poster"] = (
        ask(port, "GET", "/shared/journeys/%s/poster" % token) if token else {"http_status": "NOT_REACHED_BY_LANE",
                                                                             "why": "no token in this run"}
    )
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
