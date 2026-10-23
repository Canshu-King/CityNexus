"""Read back the newest comments on Issue #42 and PR #43 and answer one question with bytes, not memory:
do the receipts I publish on THIS channel end with CLOSING_LINE.txt verbatim?  Read-only GET."""
import io
import json
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
CLOSING = io.open(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\CLOSING_LINE.txt", encoding="utf-8").read().strip()
# Direct, not through the local proxy: 7892 is u1s1cloud here and it drops these sockets mid-request.
PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "token " + TOK)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cmdr-readback")
    with PROXY.open(req, timeout=180) as resp:
        return json.loads(resp.read().decode("utf-8"))


for label, url in (
    ("issue-42", "https://api.github.com/repos/Canshu-King/CityNexus/issues/42/comments?per_page=100"),
    ("pr-43", "https://api.github.com/repos/Canshu-King/CityNexus/issues/43/comments?per_page=100"),
):
    try:
        rows = get(url)
    except Exception as exc:
        print(label, "FETCH_FAILED", type(exc).__name__, str(exc)[:120])
        continue
    rows = sorted(rows, key=lambda r: r.get("created_at") or "")[-3:]
    print("%s newest=%d" % (label, len(rows)))
    for row in rows:
        body = (row.get("body") or "").strip()
        print("  id=%s created=%s ends_with_closing=%s tail=%r"
              % (row.get("id"), row.get("created_at"), body.endswith(CLOSING), body[-60:]))
print("CLOSING_BYTES=%d" % len(CLOSING.encode("utf-8")))
