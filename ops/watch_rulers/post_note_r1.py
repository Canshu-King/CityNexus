"""Post an arbitrary commander note with the standing safety rails.

Usage: post_note_r1.py <body_file> [--send]
Rails: every `{{LEDGER}}` placeholder is filled with the ledger blob re-read from GitHub in this run;
the assembled text must pass the Q43 r4b gate with claims > 0; the closing line is appended from
CLOSING_LINE.txt and verified byte-for-byte (length + code sum) before anything is sent.
"""
import datetime
import io
import json
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cnx-cmdr-note"}


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


body_file = sys.argv[1]
LEDGER = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander%2Fcontrol")["sha"]
TIP = get("/repos/Canshu-King/CityNexus/branches/mirror%2Fintegration-frontend-apple-pass1")["commit"]["sha"]
text = io.open(body_file, encoding="utf-8").read().replace("{{LEDGER}}", LEDGER).replace("{{TIP}}", TIP)
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
body = text.strip("\n") + "\n\n" + cl + "\n"

io.open("_note_out.txt", "w", encoding="utf-8", newline="\n").write(body)
p = subprocess.run([sys.executable, "claim_coordinate_check_r4c.py", "--text", "_note_out.txt", "--expect-clean"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
print((p.stdout or "").strip().splitlines()[-3:])
if p.returncode:
    print((p.stdout or "")[-2000:])
    raise SystemExit("REFUSED by the Q43 gate")
if len(cl) != 35 or sum(ord(c) for c in cl) != 765852 or not body.rstrip().endswith(cl):
    raise SystemExit("REFUSED: closing line problem")
print("ledger", LEDGER, "| tip", TIP, "| at", now + "+08", "| body", len(body), "chars")
if "--send" not in sys.argv:
    print("DRY RUN")
    raise SystemExit(0)
req = urllib.request.Request("https://api.github.com/repos/Canshu-King/CityNexus-Workspace/issues/1/comments")
for k, v in H.items():
    req.add_header(k, v)
data = json.dumps({"body": body}).encode()
req.add_header("Content-Length", str(len(data)))
req.method = "POST"
with urllib.request.urlopen(req, data, timeout=180) as r:
    out = json.loads(r.read().decode())
print("POSTED", out["id"], out["html_url"])
