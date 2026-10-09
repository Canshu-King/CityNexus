"""Commander's GitHub patrol: read new instructions from the bus and the product repo, print nothing secret.

Rules honoured here: REST API only (no git fetch/clone/push), the token is read from a local file and
never printed, and every answer carries its endpoint + record count so a "nothing new" is provable.
"""

import json
import urllib.error
import urllib.request

TOKEN = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
API = "https://api.github.com"
HDRS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "citynexus-commander",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get(path, pages=None):
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url)
    for k, v in HDRS.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:200]


# 1) repo + issue inventory, so "no new instructions" is a count, not a feeling
for repo in ("Canshu-King/CityNexus-Workspace", "Canshu-King/CityNexus"):
    st, issues = get(f"/repos/{repo}/issues?state=all&per_page=100&sort=updated")
    if not isinstance(issues, list):
        print(f"[{repo}] issues -> {st} {issues}")
        continue
    print(f"[{repo}] issues visible={len(issues)}")
    for it in issues[:6]:
        print(f"   #{it['number']} {it['title'][:60]!r} state={it['state']} "
              f"updated={it['updated_at']} comments={it['comments']}")

# 2) the bus: Issue #1 of the WORKSPACE repo — newest comments
BUS = "Canshu-King/CityNexus-Workspace"
st, meta = get(f"/repos/{BUS}/issues/1")
if isinstance(meta, dict):
    print(f"\n[bus] issue#1 comments={meta.get('comments')} updated={meta.get('updated_at')}")
    total = int(meta.get("comments") or 0)
    per = 30
    last_page = max(1, (total + per - 1) // per)
    st, comments = get(f"/repos/{BUS}/issues/1/comments?per_page={per}&page={last_page}")
    if isinstance(comments, list):
        print(f"[bus] fetched {len(comments)} comments from page {last_page}")
        for c in comments[-6:]:
            body = c.get("body") or ""
            print("\n" + "=" * 78)
            print(f"comment id={c['id']} by={c['user']['login']} at={c['created_at']} "
                  f"len={len(body)}")
            print(body[:6000])
    else:
        print("[bus] comments fetch failed", st, comments)
else:
    print("[bus] issue fetch failed", st, meta)

# 3) branches: did the arbiter push code for me to read?
st, branches = get(f"/repos/Canshu-King/CityNexus/branches?per_page=100")
if isinstance(branches, list):
    print(f"\n[product repo] branches={len(branches)}")
    for b in branches:
        print(f"   {b['name']:<38} {b['commit']['sha'][:9]}")
