import json,sys,time,urllib.request,urllib.error
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
BUS="Canshu-King/CityNexus-Workspace"
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
def get(url,tries=4):
    for k in range(tries):
        r=urllib.request.Request(url)
        for a,b in H.items(): r.add_header(a,b)
        try:
            with urllib.request.urlopen(r,timeout=90) as x: return x.status,json.loads(x.read().decode())
        except Exception as e: last=f"{type(e).__name__}: {e}"; time.sleep(2*(k+1))
    return "ERR",last
cid=5763777551
st,c=get(f"https://api.github.com/repos/{BUS}/issues/comments/{cid}")
if isinstance(c,dict):
    b=c.get("body") or ""
    local=open(sys.argv[1],encoding="utf-8").read()
    print("status",st,"id",c.get("id"),"created",c.get("created_at"),"len",len(b))
    print("matches local file:", b.strip()==local.strip())
    print("first 90:", b[:90].replace("\n"," | "))
    print("last 90:", b[-90:].replace("\n"," | "))
else:
    print(st,c)
st2,m=get(f"https://api.github.com/repos/{BUS}/issues/1")
print("issue comments:",m.get("comments"),"updated",m.get("updated_at"))
