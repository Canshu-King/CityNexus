"""Which comment is actually newest on the bus, and did my 23:xx posts land?"""
import json, urllib.request, urllib.error
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
def get(p):
    r=urllib.request.Request("https://api.github.com"+p)
    for k,v in H.items(): r.add_header(k,v)
    try:
        with urllib.request.urlopen(r,timeout=60) as x: return x.status, json.loads(x.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]
for repo in ("Canshu-King/CityNexus-Workspace","Canshu-King/CityNexus"):
    st,m=get(f"/repos/{repo}/issues/1")
    if st!=200: print(repo,"issue ->",st,m); continue
    n=m["comments"]; print(f"{repo}#1 comments={n} updated={m['updated_at']}")
    st,cs=get(f"/repos/{repo}/issues/1/comments?per_page=100&page={max(1,(n+99)//100)}")
    if isinstance(cs,list) and cs:
        print("  newest ids:", [(c["id"], c["created_at"]) for c in cs[-4:]])
