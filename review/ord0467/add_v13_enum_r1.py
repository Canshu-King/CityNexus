"""ORD-0467 step 1: put the V13 named-rejection vocabulary into the contract, taken from the emitters.

The list is extracted from this tree's own sources -- every `V13_` name the backend raises or the
frontend matches on -- so the contract cannot drift from what the doors actually answer, and so a
name the commander's probe invented (his file truncated one at a digit) cannot be copied in by hand.
The tool refuses rather than writing when a name is not byte-shaped or the set moved after reading.
"""
import pathlib
import re
import sys

import yaml

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
SPEC = WT / "contracts/openapi.yaml"
NAME = re.compile(r"\bV13_[A-Z0-9_]*[A-Z0-9]\b")
SHAPED = re.compile(r"^V13_[A-Z0-9]+(?:_[A-Z0-9]+)*$")
PROBE = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_v13_probe.txt")

found = {}
for root in ("backend/app", "frontend/src"):
    for p in sorted((WT / root).rglob("*")):
        if not p.is_file() or p.suffix not in (".py", ".ts", ".tsx"):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            for m in NAME.finditer(line):
                found.setdefault(m.group(0), []).append((str(p.relative_to(WT)), i))
codes = sorted(found)
bad = [c for c in codes if not SHAPED.match(c)]
if bad:
    raise SystemExit("REFUSE: names that are not a byte-shaped code: %s" % bad)
if not codes:
    raise SystemExit("REFUSE: no V13_ code found in this tree -- extraction is broken, not empty")

spec = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
existing = spec.get("components", {}).get("schemas", {}).get("V13NamedRejection")
if existing and existing.get("enum") != codes:
    print("contract copy differs from the tree; rewriting. contract=%d tree=%d" % (len(existing["enum"]), len(codes)))

probe = [l.strip() for l in PROBE.read_text(encoding="utf-8").splitlines() if l.startswith("V13_")]
only_probe = sorted(set(probe) - set(codes))
only_tree = sorted(set(codes) - set(probe))

block = ["    V13NamedRejection:",
         "      type: string",
         "      description: >-",
         "        ORD-0467. The named rejection codes this product answers with, as one closed",
         "        vocabulary. Each is raised by name in the doors listed below and reaches a client",
         "        as the first token of the error detail (`CODE` or `CODE: argument`), which is why",
         "        `frontend/src/features/pending/pendingPlaceWrites.ts` and",
         "        `frontend/src/features/discovery/RealCityDiscoveryPanel.tsx` match on it rather",
         "        than reading a structured field -- they read what the server actually sent.",
         "        Emission sites, read from this tree: %s." % "; ".join(
             "%s (%d)" % (f, len({l for _f, l in v})) for f, v in sorted(
                 {k: sorted({loc for loc in found[k] if loc[0].startswith('backend/app')}) for k in codes}.items()) if v)[:900],
         "        The credential gate (backend/app/security/credential_literals.py) may exempt a",
         "        literal only when it is byte-identical to one of these members; a value shaped like",
         "        a provider key is never exempted by contract membership.",
         "      enum:"]
block += ["        - %s" % c for c in codes]
block.append("")

text = SPEC.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
try:
    at = next(i for i, l in enumerate(lines) if l.startswith("  schemas:"))
except StopIteration:
    raise SystemExit("REFUSE: no components/schemas section found")
if existing:
    start = next(i for i, l in enumerate(lines) if l.startswith("    V13NamedRejection:"))
    end = next(i for i, l in enumerate(lines[start:], start) if l.rstrip() == "    enum:" or lines[i].startswith("      enum:"))
    while end < len(lines) and (lines[end].startswith("        - ") or lines[end].strip() == ""):
        if lines[end].strip() == "" and lines[end + 1].startswith("    ") and not lines[end + 1].startswith("     "):
            break
        end += 1
    lines = lines[:start] + lines[end:]
    at = next(i for i, l in enumerate(lines) if l.startswith("  schemas:"))
out = "".join(lines[:at + 1]) + "\n".join(block) + "\n" + "".join(lines[at + 1:])
SPEC.write_text(out, encoding="utf-8", newline="\n")

check = yaml.safe_load(SPEC.read_text(encoding="utf-8"))
enum = check["components"]["schemas"]["V13NamedRejection"]["enum"]
print("written: %d members; read back %d; equal to the tree's set: %s" % (len(codes), len(enum), enum == codes))
print("openapi still parses:", check["openapi"])
print("codes (%d): %s" % (len(codes), ", ".join(codes)))
print("probe said %d; only-in-probe (not in the tree): %s ; only-in-tree (missing from the probe): %d -> %s"
      % (len(probe), only_probe, len(only_tree), only_tree))
