import io, json, sys
from pathlib import Path
BACKEND = Path(r"D:/moodle/_qoder_b_ord0417_20260928/ord0550cut_00b5f25e/backend")
sys.path.insert(0, str(BACKEND))
from app.security import credential_literals as CL
report = CL.scan(CL.REPO)
out = {"verdict": report["verdict"], "hits_in_product_path": report["hits_in_product_path"],
       "hits_undeclared": report.get("hits_undeclared"),
       "exemptions": [{k: e[k] for k in ("line","path","pattern","reason") if k in e}
                      for e in report["vocabulary_exemptions"]]}
site = CL.REPO / "frontend/src/features/shared/SharedJourneyPanel.tsx"
lines = site.read_text(encoding="utf-8", errors="replace").splitlines()
out["site_lines_25_60"] = ["%d| %s" % (i, lines[i-1]) for i in range(25, 61)]
io.open(r"D:/moodle/_qoder_b_ord0417_20260928/run/probe_0479_r1.json","w",encoding="utf-8",newline="\n").write(json.dumps(out, ensure_ascii=False, indent=1))
print("ok")
