import subprocess, sys, pathlib, re, json
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
here = pathlib.Path(__file__).parent
def dump(url, tag, wait=6000):
    out = here / f"_render_{tag}.html"
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--virtual-time-budget=%d" % wait, "--timeout=20000",
           "--user-data-dir=" + str(here / ("_render_profile_%s" % tag)),
           "--dump-dom", url]
    p = subprocess.run(cmd, capture_output=True, timeout=120)
    out.write_bytes(p.stdout)
    html = p.stdout.decode("utf-8", "replace")
    btns = re.findall(r"<button[^>]*>(.*?)</button>", html, re.S)
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = re.sub(r"\s+", " ", txt)
    return {"url": url, "tag": tag, "dom_bytes": len(p.stdout),
            "buttons": len(btns),
            "body_chars": len(txt.strip()),
            "button_labels": [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", b)).strip()[:40] for b in btns][:24],
            "has_root_children": bool(re.search(r'<div id="root">.{40,}', html, re.S)),
            "error_strings": [s for s in ("Cannot read", "Minified React error", "Unexpected token") if s in txt],
            "out": str(out)}
if __name__ == "__main__":
    urls = sys.argv[1:]
    res = []
    for u in urls:
        tag = re.sub(r"[^A-Za-z0-9]+", "_", u.split("4781")[-1] or "root")[:24] or "root"
        try:
            res.append(dump(u, tag))
        except Exception as e:
            res.append({"url": u, "error": str(e)[:200]})
    (here / "cmdr_render_read_r1.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in res:
        keep = {k: v for k, v in r.items() if k in ("url", "dom_bytes", "buttons", "body_chars", "has_root_children", "error_strings", "error")}
        print(json.dumps(keep, ensure_ascii=False).encode("ascii", "replace").decode())
        for b in (r.get("button_labels") or [])[:10]:
            print("   btn:", b.encode("ascii", "replace").decode())
