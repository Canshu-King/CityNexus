"""Ask the classroom stack whether a real route capture is even possible right now.

The pre-flight found zero frozen mobility facts.  Whether that means "cannot capture" or "has not
captured yet" changes what the operator should expect tomorrow, so this reads the stack's own
provider status endpoint.  Output is masked: every run of thirteen or more token characters is
replaced, and the run aborts if anything resembling a key (a long hex or base64-looking run) survived
the mask, so the receipt can be committed without ever carrying credential material.
"""

import io
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw221-classroom-provider-readiness.txt")
URL = "http://127.0.0.1:60362/api/v1/providers/v9"

MASK = re.compile(r"[A-Za-z0-9_\-]{13,}")
LEAK = re.compile(r"[0-9a-f]{24,}|[A-Za-z0-9+/]{32,}={0,2}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(URL, timeout=30) as response:
            status, body = response.status, response.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 - a readiness probe must report, not crash the run
        status, body = None, repr(exc)

    masked = MASK.sub("<masked>", body)
    survivors = [len(match.group(0)) for match in LEAK.finditer(masked)]
    if survivors:
        print("ABORT the mask left %d long token-shaped runs; nothing written" % len(survivors))
        return 5

    ready = re.findall(r'"([a-z_0-9]+)":\{[^{}]*?"status":"([A-Z_]+)"', masked)
    lines = [
        "CLASSROOM PROVIDER READINESS bw221",
        "URL %s" % URL,
        "HTTP_STATUS %s bytes_before_mask=%d" % (status, len(body)),
        "AMAP_AS_REPORTED_BY_THE_STACK %s" % (" ".join(
            "%s=%s" % pair for pair in ready if pair[0] in ("amap",)
        ) or "no amap status pair parsed"),
        "ALL_STATUS_PAIRS %s" % masked_status_pairs(ready),
        "MASK runs of 13+ token characters replaced; leak check found no long hex/base64 survivor",
        "MASKED_BODY %s" % masked[:300],
    ]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


def masked_status_pairs(pairs):
    return " ".join("%s=%s" % (name, "MASKED" if MASK.search(value) else value) for name, value in pairs)


if __name__ == "__main__":
    sys.exit(main())
