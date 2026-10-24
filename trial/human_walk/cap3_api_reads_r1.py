"""Read the two membership questions on the isolated cap3 stack, by status code only.

Why: the recovery leg used bootstrap-shortlist as its membership proof, and that endpoint
answers 409 once a PlanVersion exists.  This records, in one file, that (a) the owner's
bootstrap read is 409, (b) the owner's operator read is 200, and (c) a different signed
traveller's operator read is 403 while /journeys/<id> is 200 for them too -- so the bare
journey read can never be the membership proof.  Tokens stay in _cap3_tokens.json.
"""
import io
import json
import urllib.request

TOKENS = r"D:/moodle/_cmdr_v3_port_1022/_cap3_tokens.json"
OUT = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome/cap3-api-reads-1.txt"
BASE = "http://127.0.0.1:60532"
JOURNEY = "cb4b3e56-ab40-4408-93b5-3f078222c995"
OWNER = "ac7c8c87-3f10-49e5-a86e-71728e6afecd"
OTHER = "0c63fa67-e50c-4d7c-b3b6-635108336904"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def read(path, token):
    request = urllib.request.Request(BASE + path)
    request.add_header("Authorization", "Bearer " + token)
    try:
        with opener.open(request, timeout=20) as response:
            body = response.read(400)
            return response.status, body
    except Exception as error:  # noqa: BLE001
        body = getattr(error, "read", lambda: b"")()
        return getattr(error, "code", 0), body


def key_of(body):
    try:
        payload = json.loads(body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return ""
    if isinstance(payload, dict):
        error = payload.get("error") or {}
        return str(error.get("message_key") or error.get("code") or payload.get("code") or "")
    return ""


tokens = json.load(io.open(TOKENS, encoding="utf-8"))
lines = ["cap3 membership reads (isolated copy; status + code only)"]
for label, token, path in [
    ("owner", OWNER, "/api/v1/travelers/session"),
    ("owner", OWNER, "/api/v1/journeys/%s" % JOURNEY),
    ("owner", OWNER, "/api/v1/journeys/%s/bootstrap-shortlist" % JOURNEY),
    ("owner", OWNER, "/api/v1/journeys/%s/operator" % JOURNEY),
    ("other", OTHER, "/api/v1/journeys/%s" % JOURNEY),
    ("other", OTHER, "/api/v1/journeys/%s/operator" % JOURNEY),
]:
    status, body = read(path, tokens[token])
    lines.append("%s %s http_status=%s code=%s" % (label, path, status, key_of(body) or "-"))
io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
print("\n".join(lines))
