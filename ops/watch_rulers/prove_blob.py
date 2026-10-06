"""Prove my own published artifacts exist at the readable coordinate (blob sha1 + size from the API)."""
import json
import sys
import urllib.error
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander"}
paths = sys.argv[1:] or ["evidence/ord0239/city_matrix.json"]
for p in paths:
    url = f"https://api.github.com/repos/Canshu-King/CityNexus/contents/{p}?ref=commander/control"
    req = urllib.request.Request(url)
    for k, v in HDRS.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
            print(f"200 {p} blob={str(d.get('sha'))[:16]} size={d.get('size')}")
    except urllib.error.HTTPError as e:
        print(f"{e.code} {p} {e.read().decode('utf-8','replace')[:120]}")
    except Exception as e:  # noqa: BLE001
        print(f"ERR {p} {type(e).__name__} {str(e)[:120]}")
