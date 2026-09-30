"""ORD-0528 lane -- does `env -u HTTP_PROXY -u HTTPS_PROXY` actually clear the proxy layer?

The commander says it does not: on Windows, `urllib` falls back to the *registry* proxy when the
environment carries no proxy name, and a registry proxy sitting on the path has been seen to rewrite
`Authorization` and hand back `http_status=401`. This file records what this box answers today, in the
three shapes that matter, so the claim is a reading rather than a rumour:

  * `registry`   -- what Internet Settings says (ProxyEnable / ProxyServer);
  * `env_only_two_unset` / `all_proxy_names_unset` -- what `getproxies()` returns in each case, which
    is where the "unsetting two is not enough" mechanism lives: CPython consults the registry ONLY
    when the environment yields nothing at all;
  * `auth_probe` -- the same deliberately invalid `Authorization` sent down each path, compared by the
    message the server gives back. `Bad credentials` means the header arrived and was rejected on its
    merits; a different sentence (e.g. one about authentication being required) is the shape that
    would mean the header never arrived intact.

Nothing here sends a real credential. `api.github.com/meta` is an unauthenticated read.
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

OUT = sys.argv[1]
REPO = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt"


def registry():
    script = (
        "$k='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings'; "
        "$p=Get-ItemProperty $k; "
        "[pscustomobject]@{ProxyEnable=$p.ProxyEnable; ProxyServer=[string]$p.ProxyServer; "
        "AutoConfigURL=[string]$p.AutoConfigURL} | ConvertTo-Json -Compress"
    )
    done = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    try:
        return json.loads(done.stdout.strip())
    except Exception:  # noqa: BLE001
        return {"raw": done.stdout[:200], "err": done.stderr[:200]}


def listening(port):
    done = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    for line in done.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(":%s" % port) and parts[3] == "LISTENING":
            return parts[4]
    return None


def child(env_extra, code):
    env = dict(os.environ)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(name, None)
    env.update(env_extra)
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=180, env=env)
    return done.stdout.strip(), done.stderr.strip()


PROBE = """
import json, urllib.error, urllib.request as u
out = {"getproxies": u.getproxies()}
hdr = {"Authorization": "Bearer invalid-token-for-path-test", "User-Agent": "cnx-lane-probe",
       "Accept": "application/vnd.github+json"}
def go(opener, label):
    try:
        r = opener.open(u.Request("https://api.github.com/user", headers=hdr), timeout=20)
        out[label] = {"http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        body = e.read()
        try:
            message = json.loads(body).get("message")
        except Exception:
            message = None
        out[label] = {"http_status": e.code, "message": message, "bytes": len(body)}
    except Exception as e:
        out[label] = {"error": type(e).__name__, "note": str(e)[:120]}
go(u.build_opener(), "via_getproxies")
go(u.build_opener(u.ProxyHandler({})), "forced_direct")
go(u.build_opener(u.ProxyHandler({"https": "http://127.0.0.1:7892"})), "via_registry_port")
print(json.dumps(out, ensure_ascii=False))
"""


def main():
    report = {
        "registry": registry(),
        "listening": {port: listening(port) for port in ("7892", "7897")},
        "two_names_only_unset": child({"NO_PROXY": "api.github.com"}, PROBE),
        "every_proxy_name_removed": child({}, PROBE),
        "command_note": (
            "the lane's own git remote is git@github.com:... (SSH), so no HTTP proxy applies to "
            "`git ls-remote`/`git push` on this branch; this probe is about the HTTP side lanes use"
        ),
    }
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, ensure_ascii=False)
    print(json.dumps(report, indent=1, ensure_ascii=False)[:2400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
