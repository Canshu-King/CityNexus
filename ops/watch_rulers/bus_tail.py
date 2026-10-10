"""Bus tail with retry: IncompleteRead happens on the big comment pages."""
import json, sys, time, urllib.request, urllib.error
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
def get(p, tries=4):
    for k in range(tries):
        r=urllib.request.Request("https://api.github.com"+p)
        for a,b in H.items(): r.add_header(a,b)
        try:
            with urllib.request.urlopen(r,timeout=90) as x:
                return x.status, json.loads(x.read().decode())
        except Exception as e:
            last=f"{type(e).__name__}: {e}"
            time.sleep(1.5*(k+1))
    return "ERR", last
BUS="Canshu-King/CityNexus-Workspace"
st,m=get(f"/repos/{BUS}/issues/1")
print("issue ->",st,"comments",m.get("comments") if isinstance(m,dict) else m)
n=int(m["comments"]); per=100
st,cs=get(f"/repos/{BUS}/issues/1/comments?per_page={per}&page={(n+per-1)//per}")
if not isinstance(cs,list): print("comments fail",st,cs); sys.exit(1)
print("page returns",len(cs))
MINE=5760677307
for c in cs:
    if c["id"]<=MINE: continue
    b=c.get("body") or ""
    print("\n"+"="*78)
    print(f"id={c['id']} by={c['user']['login']} at={c['created_at']} len={len(b)}")
    print(b[:5000])
