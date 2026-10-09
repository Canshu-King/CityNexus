"""Commander phone-chain end-to-end probe (through the public tunnel, Basic auth from the auth file).

Prints ONLY status codes, byte counts and content-type prefixes -- never the credential.
Read-only against the product: GETs only, no POST, no demo/reset, no _live/_preview writes.
"""
import sys, os, re, json, urllib.request, urllib.error, time

AUTH_FILE = r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt"
BASE = os.environ.get("CNX_PROBE_BASE", "https://obligation-plain-arcade-bean.trycloudflare.com")


def secret():
    raw = open(AUTH_FILE, "rb").read().decode("utf-8").strip()
    if "\t" in raw:
        user, pw = raw.split("\t", 1)
    else:
        user, pw = raw.split(":", 1)
    import base64
    return base64.b64encode(("%s:%s" % (user, pw)).encode("utf-8")).decode()


def get(path, auth=False, timeout=45):
    req = urllib.request.Request(BASE + path, method="GET",
                                 headers={"User-Agent": "cnx-commander-chain-probe"})
    if auth:
        req.add_header("Authorization", "Basic " + secret())
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, dict(r.headers).get("Content-Type", "?"), len(body), body, round((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        body = e.read()
        return e.code, dict(e.headers).get("Content-Type", "?"), len(body), body, round((time.time() - t0) * 1000)
    except Exception as e:
        return "ERR", type(e).__name__, 0, b"", round((time.time() - t0) * 1000)


def main():
    print("BASE", BASE)
    s, ct, n, _, ms = get("/")
    print("1 no-auth  /                      ->", s, ct[:24], n, "B", ms, "ms  (expect 401)")
    s, ct, n, body, ms = get("/", auth=True)
    print("2 auth     /                      ->", s, ct[:24], n, "B", ms, "ms")
    html = body.decode("utf-8", "replace") if isinstance(body, bytes) else ""
    assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
    print("  index refs", len(assets), "asset(s); first:", assets[0] if assets else "NONE")
    ok = 0
    for a in assets[:6]:
        s2, ct2, n2, _, ms2 = get(a, auth=True)
        looks_js = ("javascript" in ct2.lower()) or ct2.lower().startswith("text/javascript")
        looks_css = "css" in ct2.lower()
        good = (s2 == 200) and (looks_js or looks_css)
        ok += good
        print("   asset", a[:34], "->", s2, ct2[:22], n2, "B", ms2, "ms", "OK" if good else "!! NOT THE TYPE IT SHOULD BE")
    for api in ("/api/v1/health", "/api/v1/today", "/api/v1/journeys"):
        s3, ct3, n3, body3, ms3 = get(api, auth=True)
        print("3 api", api, "->", s3, ct3[:22], n3, "B", ms3, "ms")
        if s3 == 200:
            try:
                d = json.loads(body3.decode("utf-8"))
                keys = sorted(d.keys())[:8] if isinstance(d, dict) else type(d).__name__
                print("    payload keys:", keys)
            except Exception as e:
                print("    not json:", type(e).__name__)
    print("ASSETS_OK", ok, "/", min(len(assets), 6))


main()
