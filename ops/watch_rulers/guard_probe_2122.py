"""Is the R13 guard still up on the live preview?  Credentials are read from the file and never printed.

The file is `user<TAB>password` (one line), not `user:password` - my first parser assumed a colon and
reported "shape changed".  The value is used only to build a Basic header inside this process.
"""

import base64
import urllib.error
import urllib.request

raw = open(r"D:\moodle\_qoder_preview_20260920\run\preview_auth.txt", encoding="utf-8").read()
line = next((l for l in raw.splitlines() if l.strip()), "")
parts = line.replace(":", "\t").split("\t")
if len(parts) < 2:
    raise SystemExit(f"unexpected auth-file shape: {len(parts)} field(s) - not probing")
user, passwd = parts[0].strip(), parts[1].strip()
tok = base64.b64encode(f"{user}:{passwd}".encode()).decode()


def call(method, url):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Basic {tok}")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(400).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(400).decode("utf-8", "replace")


print("auth file parsed: 2 fields, values withheld")
for m, u in (("GET", "http://127.0.0.1:4782/"),
             ("POST", "http://127.0.0.1:4782/api/v1/demo/reset"),
             ("GET", "http://127.0.0.1:4782/api/v1/health")):
    st, body = call(m, u)
    print(f"{m} {u} -> {st} :: {body[:140]!r}")
