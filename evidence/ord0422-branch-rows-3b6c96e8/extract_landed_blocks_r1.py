# Pulls my own delivered blocks back out of the ledger mirror as they actually landed, one file each,
# so the coordinate door can be run on the bytes in the ledger rather than on my local draft. The
# refusal the commander reported was against an earlier snapshot of one of these blocks; this decides
# that by measurement instead by argument.
import json
import json
import re
import subprocess
import sys

REF = sys.argv[1]
PATH = "CITYNEXUS_AGENT_CONTROL.md"
raw = subprocess.run(["git", "-C", "D:/moodle/_qoder_q_ord0422/wt", "show", "%s:%s" % (REF, PATH)],
                     capture_output=True).stdout.decode("utf-8", "replace")
lines = raw.splitlines(keepends=True)
starts = [i for i, l in enumerate(lines)
          if l.startswith("### ORD-0422") and "车道 Q" in l]
out = []
for n, i in enumerate(starts):
    end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("### ")), len(lines))
    body = "".join(lines[i:end])
    head = lines[i].strip()[:96]
    p = "D:/moodle/_qoder_q_ord0422/landed_block_%d.md" % n
    open(p, "w", encoding="utf-8", newline="\n").write(body)
    bare = [m.group(0) for m in re.finditer(r"\b\d+\s*(?:条|处|枚|次|行|个)\b", body)]
    out.append({"index": n, "heading": head, "bytes": len(body.encode("utf-8")),
                "lines": body.count("\n"), "file": p,
                "arabic_quantifiers_found": bare})
print(json.dumps({"ledger_ref": REF, "my_block_headings": len(starts), "blocks": out},
                  ensure_ascii=False, indent=1))
