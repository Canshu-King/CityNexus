"""Resolve two guard reds by measurement: the credential verdict and the receipt-table LIKE.

ORD-0307's gate and ORD-0332's "receipts are never persisted" guard are both red, and both messages
stopped short of naming what they actually hit.  This calls the product's own scanner and the product's
own table metadata, so the answer comes from the same code the guards use.

Two rules are bolted into this door rather than remembered:
  * no secret may leave the run.  Every credential-ish environment value is collected first and the
    finished report is checked against each one; if any value appears anywhere in the text the run
    aborts before writing, so a leak is impossible by construction rather than by care.
  * the two hypotheses about the receipt guard are mutually exclusive, so the run prints both counts:
    tables whose name contains 'receipt' (what the guard's LIKE matches) and models that carry an
    error-receipt column/table at all (what the design claim is about).
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BACKEND = os.path.join(ROOT, "backend")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw206-two-guard-resolutions.txt")

SECRET_ENV_WORDS = ("KEY", "TOKEN", "SECRET", "PASSWORD")


def secret_values():
    out = []
    for name, value in os.environ.items():
        if not value or len(value) < 6:
            continue
        if any(word in name.upper() for word in SECRET_ENV_WORDS):
            out.append(value)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, BACKEND)
    from app.db.models import Base  # noqa: E402
    from app.security import credential_literals as CL  # noqa: E402

    report = CL.scan(CL.REPO)
    tables = sorted(Base.metadata.tables)
    receipt_named = [t for t in tables if "receipt" in t]
    error_receipt_hits = []
    for path in (os.path.join(BACKEND, "app"), ):
        for dirpath, _dirs, files in os.walk(path):
            for name in files:
                if not name.endswith(".py"):
                    continue
                full = os.path.join(dirpath, name)
                text = io.open(full, encoding="utf-8", errors="replace").read()
                if "error_receipt" in text:
                    error_receipt_hits.append(os.path.relpath(full, ROOT))

    undeclared_outside = [
        h for h in report["hits"] if not h.get("declared") and not h.get("in_product_path")
    ]
    files_outside = sorted({h["path"] for h in undeclared_outside})

    lines = [
        "TWO GUARD RESOLUTIONS bw206",
        "TIP %s" % os.popen("git -C %s rev-parse HEAD" % ROOT).read().strip(),
        "CREDENTIAL SCANNER (the product's own, called here)",
        "  verdict=%s env_present=%s hits_total=%s hits_in_product_path=%s"
        % (report["verdict"], report["env_present"], report.get("hits_total"), report["hits_in_product_path"]),
        "  undeclared_and_outside_product_path %d files, listed by name only" % len(files_outside),
    ]
    lines += ["    - %s" % f for f in files_outside]
    lines += [
        "RECEIPT TABLES (what the guard's LIKE matches)",
        "  tables_in_metadata %d, name contains 'receipt': %d" % (len(tables), len(receipt_named)),
    ]
    lines += ["    - %s" % t for t in receipt_named]
    lines += [
        "  files under backend/app that mention error_receipt: %d" % len(error_receipt_hits),
    ]
    lines += ["    - %s" % f for f in sorted(error_receipt_hits)[:20]]
    error_receipt_table = [t for t in tables if "error_receipt" in t]
    lines.append(
        "  tables named for error receipts: %d -- if this is zero the design claim stands and the"
        " guard's LIKE is simply too wide" % len(error_receipt_table)
    )

    text = "\n".join(lines)
    leaked = [len(value) for value in secret_values() if value in text]
    if leaked:
        print("ABORT the report would carry a live credential value; nothing written")
        return 5
    if len(error_receipt_table) > 0 and len(receipt_named) == 0:
        print("ABORT the two receipt counts contradict each other; not publishing")
        return 6

    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write(text + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    print("SECRET_SCAN checked %d credential-ish environment values against the report"
          % len(secret_values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
