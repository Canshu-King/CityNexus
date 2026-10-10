"""Post one comment to the bus (Issue #1 of CityNexus-Workspace) via REST, then read back its id."""
import json, sys, time, urllib.request, urllib.error
import ghnet   # 09-26 17:08：环境代理指向死掉的 127.0.0.1:7892 时自动直连重试
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
BUS="Canshu-King/CityNexus-Workspace"
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
body=open(sys.argv[1],encoding="utf-8").read()
def call(method,url,payload=None,tries=3):
    for k in range(tries):
        r=urllib.request.Request(url,method=method,
            data=json.dumps(payload).encode() if payload else None)
        for a,b in H.items(): r.add_header(a,b)
        if payload: r.add_header("Content-Type","application/json")
        try:
            st, body = ghnet.urlopen(r, timeout=90)
            return st, (json.loads(body.decode()) if body.strip()[:1] in b'{[' else body.decode()[:400])
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()[:400]
        except Exception as e:
            last=f"{type(e).__name__}: {e}"; time.sleep(2*(k+1))
    return "ERR", last
st,res=call("POST",f"https://api.github.com/repos/{BUS}/issues/1/comments",{"body":body})
print("POST ->",st, (res.get("id") if isinstance(res,dict) else res))
if isinstance(res,dict) and res.get("id"):
    cid=res["id"]
    st2,back=call("GET",f"https://api.github.com/repos/{BUS}/issues/comments/{cid}")
    b=(back.get("body") if isinstance(back,dict) else "")
    if not b:
        print("readback id:",cid,"INCONCLUSIVE (empty/non-dict response; not a mismatch) -",str(back)[:120])
        print("  fallback: python bus_read_one.py",cid)
    else:
        print("readback id:",cid,"len:",len(b),"matches:",b.strip()==body.strip())
    st3,meta=call("GET",f"https://api.github.com/repos/{BUS}/issues/1")
    print("issue comments now:",meta.get("comments") if isinstance(meta,dict) else meta)
