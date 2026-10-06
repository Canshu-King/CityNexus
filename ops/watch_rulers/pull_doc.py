import base64, io, json, os, sys, urllib.request, urllib.error
TOK=open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920",encoding="utf-8").read().strip()
H={"Authorization":f"Bearer {TOK}","Accept":"application/vnd.github+json","User-Agent":"cnx-cmdr","X-GitHub-Api-Version":"2022-11-28"}
def get(p):
    r=urllib.request.Request("https://api.github.com"+p)
    for k,v in H.items(): r.add_header(k,v)
    try:
        with urllib.request.urlopen(r,timeout=60) as x: return x.status, json.loads(x.read().decode())
    except urllib.error.HTTPError as e: return e.code, e.read().decode()[:200]
OUT=r"D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs"
os.makedirs(OUT,exist_ok=True)
REPO="Canshu-King/CityNexus"
for path,ref in (("docs/pending_destination_identity_policy.md","e4b7faa315d37a2912afb455dcca479c62c00dd0"),
                 ("docs/test_execution_truth_policy.md","65f1934f95a37c06812484c48ed50d7e5a87ff3f")):
    st,b=get(f"/repos/{REPO}/contents/{path}?ref={ref}")
    if st==200 and isinstance(b,dict) and b.get("content"):
        data=base64.b64decode(b["content"])
        io.open(os.path.join(OUT,os.path.basename(path)),"wb").write(data)
        print("OK",path,"bytes",len(data))
    else:
        print("FAIL",path,st,str(b)[:150])
for sha in ("e4b7faa315d37a2912afb455dcca479c62c00dd0","65f1934f95a37c06812484c48ed50d7e5a87ff3f"):
    st,c=get(f"/repos/{REPO}/commits/{sha}")
    if st==200:
        print(f"\n{sha[:9]} {c['commit']['committer']['date']} {c['commit']['message'][:90]!r}")
        for f in c.get("files",[]): print("   ",f["status"],f["filename"],f"+{f['additions']}/-{f['deletions']}")
