"""Pull the three contract docs the arbiter added on arbiter/anywhere-contract (REST contents only, no git network)."""
import base64, io, json, os, urllib.request, urllib.error

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander", "X-GitHub-Api-Version": "2022-11-28"}
OUT = r"D:\moodle\_qoder_cmdr_ref_20260921\arbiter_docs"
os.makedirs(OUT, exist_ok=True)


def get(path):
    req = urllib.request.Request(API + path)
    for k, v in HDRS.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"_raw": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, {"_err": str(e)[:300]}


refs = get(f"/repos/{REPO}/git/ref/heads/arbiter/anywhere-contract")
print("ref ->", refs[0], (refs[1].get("object", {}) or {}).get("sha", "")[:40] if isinstance(refs[1], dict) else refs[1])
tip = refs[1]["object"]["sha"] if isinstance(refs[1], dict) and "object" in refs[1] else None
print("tip", tip)

want = {
    "docs/accessibility_evidence_mapping_policy.md": "fdda90d2327797fc57590bce4f68856eaf89614a",
    "docs/planning_constraint_input_truth_policy.md": "52d7ccb63f291c8fd05f436b7594e591a406e04a",
    "docs/anywhere_capability.md": "5238911f0618417e4dd59be79accce4ed415d5f1",
}
for path, sha in want.items():
    for ref in (sha, tip or "HEAD"):
        st, blob = get(f"/repos/{REPO}/contents/{path}?ref={ref}")
        if st == 200 and isinstance(blob, dict) and blob.get("content"):
            data = base64.b64decode(blob["content"])
            name = os.path.join(OUT, os.path.basename(path))
            io.open(name, "wb").write(data)
            print(f"OK  {path}  ref={ref[:9]}  sha256len={len(data)}  bytes -> {name}")
            break
    else:
        print(f"FAIL {path} -> {st} {str(blob)[:200]}")

# what else moved on that branch: compare tree of the 3 named commits
for sha in list(want.values()):
    st, c = get(f"/repos/{REPO}/commits/{sha}")
    if st == 200:
        print(f"\ncommit {sha[:9]} at={c['commit']['committer']['date']} msg={c['commit']['message'][:100]!r}")
        for f in c.get("files", []):
            print(f"   {f['status']:<8} {f['filename']:<70} +{f['additions']}/-{f['deletions']}")
    else:
        print("commit fetch failed", sha[:9], st, str(c)[:150])
