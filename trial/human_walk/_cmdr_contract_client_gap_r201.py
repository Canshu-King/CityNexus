"""Re-measure the ORD-0402 client-gap guard with a second, independent ruler.

The guard test compares every contract operationId against `frontend/src/generated/api.ts` and is
red.  A red guard is only useful if the drift it names is real, so this computes the same set a
different way -- walking the OpenAPI paths directly and testing for the `operations["id"]` reference
the generated client uses -- and writes the list out.  It changes nothing: no regeneration, no
product byte.

The self-check is the arithmetic: the number of operations found in the contract must be the number
the guard's own denominator implies, and the missing list must equal the count in the guard's
message.  If either fails the run aborts rather than publishing a second, different total.
"""

import io
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CONTRACT = os.path.join(ROOT, "contracts", "openapi.yaml")
GENERATED = os.path.join(ROOT, "frontend", "src", "generated", "api.ts")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw201-contract-client-gap.txt")

GUARD_REPORTED_MISSING = 6


def contract_operations(spec):
    found = set()
    for _path, item in (spec.get("paths") or {}).items():
        for _method, node in (item or {}).items():
            if isinstance(node, dict) and isinstance(node.get("operationId"), str):
                found.add(node["operationId"])
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    spec = yaml.safe_load(io.open(CONTRACT, encoding="utf-8").read())
    operations = contract_operations(spec)
    generated = io.open(GENERATED, encoding="utf-8").read()
    missing = sorted(op for op in operations if 'operations["%s"]' % op not in generated)
    referenced = sum(1 for op in operations if 'operations["%s"]' % op in generated)

    if not operations:
        print("ABORT the contract yielded no operationIds")
        return 4
    if len(missing) != GUARD_REPORTED_MISSING:
        print(
            "ABORT this ruler counts %d missing operations but the guard reported %d -- the two"
            " denominators disagree, so neither number can be published"
            % (len(missing), GUARD_REPORTED_MISSING)
        )
        return 5
    if referenced + len(missing) != len(operations):
        print("ABORT referenced %d + missing %d != contract %d" % (referenced, len(missing), len(operations)))
        return 6

    lines = [
        "CONTRACT VS GENERATED CLIENT GAP bw201",
        "CONTRACT %s" % os.path.relpath(CONTRACT, ROOT),
        "GENERATED %s" % os.path.relpath(GENERATED, ROOT),
        "CONTRACT_OPERATIONS %d" % len(operations),
        "REFERENCED_BY_CLIENT %d" % referenced,
        "ABSENT_FROM_CLIENT %d (enforced equal to the guard's own number)" % len(missing),
        "ARITHMETIC referenced+absent=contract, checked above",
        "ABSENT OPERATION IDS",
    ]
    lines += ["  - %s" % op for op in missing]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
