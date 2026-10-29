"""Check which required body fields of the discovery door the checked-in contract actually declares.

Eight reds read "request body rejected by validation" for one field, `consented_provider`.  The
product requires it and two frontend writers send it, so no traveler is blocked -- but the contract
may still be silent about it, which is a defect of a different kind: the generated client and the
contract stop describing what the door accepts.

The ruler reads the request model's own class body for required field names, then asks the contract
for each one.  It refuses to publish a partial answer: the class must be found, must yield fields,
and every field name it reports must have been seen in the source it came from.
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SCHEMAS = os.path.join(ROOT, "backend", "app", "schemas.py")
CONTRACT = os.path.join(ROOT, "contracts", "openapi.yaml")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw241-contract-field-gap.txt")

CLASSES = ("BootstrapDiscoveryRequest", "RealCityDiscoveryRequest")
FRONTEND_SENDERS = [
    ("frontend/src/features/discovery/BootstrapDiscoveryPanel.tsx", "consented_provider"),
    ("frontend/src/trial/RevolutionQuickExplore.tsx", "consented_provider"),
    ("frontend/src/api/citynexus.ts", "consented_provider"),
]
FIELD = re.compile(r"^\s{4}(\w+)\s*:\s*([^=]+?)(?:\s*=\s*(.+))?$")


def class_fields(source, name):
    lines = source.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("class %s(" % name))
    except StopIteration:
        return None
    fields = []
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if line.startswith("class ") or (line and not line.startswith((" ", "\t")) and line.strip() and not line.startswith("#")):
            break
        match = FIELD.match(line)
        if match:
            declared, default = match.group(2).strip(), match.group(3)
            fields.append((match.group(1), declared, default is not None, i + 1))
    return fields


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    source = io.open(SCHEMAS, encoding="utf-8", errors="replace").read()
    contract = io.open(CONTRACT, encoding="utf-8", errors="replace").read()

    lines = ["CONTRACT VS REQUIRED BODY FIELDS bw241", "SCHEMAS %s" % os.path.relpath(SCHEMAS, ROOT),
             "CONTRACT %s" % os.path.relpath(CONTRACT, ROOT)]
    total_missing = 0
    for name in CLASSES:
        fields = class_fields(source, name)
        if fields is None:
            print("ABORT request model %s not found in %s" % (name, SCHEMAS))
            return 5
        if not fields:
            print("ABORT %s yielded no fields; the parser would report a false clean" % name)
            return 6
        lines.append("CLASS %s fields=%d" % (name, len(fields)))
        for field_name, declared, has_default, line_no in fields:
            in_contract = re.search(r"^\s+%s:" % re.escape(field_name), contract, re.M) is not None
            if not in_contract and not has_default:
                total_missing += 1
            lines.append("  %-24s required=%-5s in_contract=%-5s  source=%s:%d"
                         % (field_name, "no" if has_default else "yes",
                            "yes" if in_contract else "no", "backend/app/schemas.py", line_no))

    for rel, field_name in FRONTEND_SENDERS:
        text = io.open(os.path.join(ROOT, rel.replace("/", os.sep)), encoding="utf-8", errors="replace").read()
        count = text.count(field_name)
        lines.append("FRONTEND_SENDS %s occurrences=%d" % (rel, count))
    lines.append("REQUIRED_FIELDS_ABSENT_FROM_CONTRACT %d" % total_missing)

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
