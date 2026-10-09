"""Fetch one bus comment reliably: small pages + retries, because big comment pages link-reset mid-body."""
import json, sys, time, urllib.request, urllib.error
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # 09-25: this file crashed twice on a lane's U+2713 under a GBK console
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
WANT = int(sys.argv[1])
def get(p):
    r = urllib.request.Request("https://api.github.com" + p)
    for k, v in {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github.raw+json",
                 "User-Agent": "citynexus-commander"}.items():
        r.add_header(k, v)
    with urllib.request.urlopen(r, timeout=120) as x:
        return json.loads(x.read().decode())
for per in (3, 5, 10):
    try:
        meta = get("/repos/Canshu-King/CityNexus-Workspace/issues/1")
        total = int(meta["comments"])
        last_page = max(1, (total + per - 1) // per)
        for page in range(last_page, max(0, last_page - 3), -1):
            cs = get(f"/repos/Canshu-King/CityNexus-Workspace/issues/1/comments?per_page={per}&page={page}")
            for c in cs:
                if c["id"] == WANT:
                    print(f"# per_page={per} page={page} total={total} len={len(c['body'])} at={c['created_at']}")
                    print(c["body"])
                    raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"  per_page={per} failed: {type(e).__name__} {str(e)[:90]}", file=sys.stderr)
        time.sleep(3)
print("NOT FOUND after retries", file=sys.stderr)
raise SystemExit(1)
