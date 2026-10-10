"""Fetch two specific bus comments by id (cheap + precise, no giant page fetch)."""
import json,sys,time,urllib.request,urllib.error
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
BUS="Canshu-King/CityNexus-Workspace"
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
def get(url,tries=3):
    for k in range(tries):
        r=urllib.request.Request(url)
        for a,b in H.items(): r.add_header(a,b)
        try:
            with urllib.request.urlopen(r,timeout=60) as x: return x.status,json.loads(x.read().decode())
        except Exception as e:
            last=f"{type(e).__name__}: {e}"; time.sleep(2*(k+1))
    return "ERR",last
for cid in (5764104730, 5764162935):
    st,c=get(f"https://api.github.com/repos/{BUS}/issues/comments/{cid}")
    if not isinstance(c,dict):
        print(cid,"->",st,c); continue
    b=(c.get("body") or "")
    print("="*78)
    print(f"id={cid} at={c.get('created_at')} len={len(b)}")
    print(b[:2600])
