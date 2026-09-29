"""ORD-0459 arm ownership proof -- two receipts per static port, taken in one batch.

vite preview gives a lane only two of the three proofs a backend gives, and the missing one is named
in the output rather than fudged:
  (1) the entry asset name is read out of the index.html THIS port serves and must equal the disk
      copy of the dist I built;
  (2) sha1 over the served bytes of that entry must equal sha1 over the disk bytes;
  (3) NOT AVAILABLE on vite preview -- there is no access log to point at a request. Stated, not skipped.
Proxies are cleared because a stale HTTP_PROXY on this box answers 10061 and reads as unreachable.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0448_20260929")
ARMS = {
    "before": {"base": "http://127.0.0.1:49162/",
               "dist": pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_build_o459before2/frontend/dist")},
    "after": {"base": "http://127.0.0.1:49163/",
              "dist": ROOT / "dist_after5"},
}
PIDS = {"before": "33356", "after": "53172"}


def curl_bytes(url):
    p = subprocess.run(["curl", "-s", "--noproxy", "*", "--max-time", "20", url],
                       capture_output=True, timeout=40)
    return p.returncode, p.stdout


def curl_status(url):
    p = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{content_type} %{size_download}",
                        "--noproxy", "*", "--max-time", "20", url],
                       capture_output=True, text=True, timeout=40)
    return p.stdout.strip()


def cmdline(pid):
    q = ("Get-CimInstance Win32_Process -Filter 'ProcessId=%s' | Select-Object -ExpandProperty CommandLine" % pid)
    p = subprocess.run(["powershell", "-NoProfile", "-Command", q], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60)
    return " ".join(p.stdout.split())


out = []


def entry_name(raw):
    m = re.search(rb'src="(/assets/index-[^"]+\.js)"', raw)
    return m.group(1).decode() if m else None


for arm, a in ARMS.items():
    rc, idx_bytes = curl_bytes(a["base"])
    idx_disk = (a["dist"] / "index.html").read_bytes()
    served_idx = hashlib.sha1(idx_bytes).hexdigest()
    disk_idx = hashlib.sha1(idx_disk).hexdigest()
    rec = {"arm": arm, "base": a["base"], "http_root": curl_status(a["base"]),
           "listener_pid": PIDS[arm], "listener_cmdline": cmdline(PIDS[arm]),
           "entry_named_by_served_index": entry_name(idx_bytes),
           "entry_named_by_disk_index": entry_name(idx_disk),
           "index_served_sha1": served_idx, "index_disk_sha1": disk_idx,
           "index_bytes_served": len(idx_bytes), "index_bytes_disk": len(idx_disk)}
    asset = "/" + (rec["entry_named_by_served_index"] or "").lstrip("/")
    if rec["entry_named_by_served_index"]:
        disk_asset = a["dist"] / rec["entry_named_by_served_index"].lstrip("/")
        served_sha = hashlib.sha1(curl_bytes(a["base"] + asset.lstrip("/"))[1]).hexdigest()
        rec.update({"entry_http": curl_status(a["base"] + asset.lstrip("/")),
                    "entry_served_sha1": served_sha,
                    "entry_disk_sha1": hashlib.sha1(disk_asset.read_bytes()).hexdigest(),
                    "entry_bytes_served": len(curl_bytes(a["base"] + asset.lstrip("/"))[1]),
                    "entry_bytes_disk": disk_asset.stat().st_size})
    rec["proof_1_entry_name_from_my_index"] = (rec["entry_named_by_served_index"] is not None
                                               and rec["entry_named_by_served_index"] == rec["entry_named_by_disk_index"])
    rec["proof_2_served_equals_disk"] = (rec.get("entry_served_sha1") == rec.get("entry_disk_sha1")
                                         and served_idx == disk_idx)
    rec["proof_3_access_log"] = "NOT_AVAILABLE_on_vite_preview"
    out.append(rec)

css = []
for arm, a in ARMS.items():
    names = sorted((a["dist"] / "assets").glob("index-*.css"))
    for n in names:
        served = curl_bytes(a["base"] + "assets/" + n.name)[1]
        css.append({"arm": arm, "file": n.name, "disk_bytes": n.stat().st_size,
                    "served_bytes": len(served),
                    "disk_sha1": hashlib.sha1(n.read_bytes()).hexdigest(),
                    "served_sha1": hashlib.sha1(served).hexdigest()})
text = json.dumps({"arms": out, "css_assets": css}, ensure_ascii=False, indent=1) + "\n"
(ROOT / "arm_ownership_r1.json").write_text(text, encoding="utf-8", newline="\n")
print(text)
