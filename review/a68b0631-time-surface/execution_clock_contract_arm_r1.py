"""Counter-arm for the execution-clock CONTRACT: the response must declare which zone the instant
is in, and the generated client must carry those fields.

The gap this pins: `/journeys/{journey_id}/execution-clock` answered `{type: object}` -- it declared
no properties at all.  So the moment's zone was never part of the contract; it was a private detail
of the service, the generated client could not see it, and nothing could hold the payload to naming a
zone its own instant is not in.

This arm reads the real files:
  * the contract must declare `used_timezone` and `timezone_honoured` on that response, and
  * the generated client must actually carry them,
so a service that starts speaking for itself has to bring the contract with it.  It exits non-zero
with the offending reading printed.
"""
import io
import re
import sys

ROOT = "D:/moodle/_qoder_rel_ord0447_wt/"
CONTRACT = ROOT + "contracts/openapi.yaml"
CLIENT = ROOT + "frontend/src/generated/api.ts"
CLOCK_PATH = "/journeys/{journey_id}/execution-clock"


def clock_block(text):
    """The lines of the clock response, from its path key to the next path key.

    The contract writes `  /journeys/{journey_id}/execution-clock:` while the generated client writes
    the same key inside quotes (`  "/journeys/{journey_id}/execution-clock": {`), so both spellings are
    accepted -- a matcher that only knows one of them reports the branch's own fix as missing.
    """
    lines = text.split("\n")
    start = None
    for i, l in enumerate(lines):
        s = l.strip().strip('"').lstrip(":").strip('"')
        if s.startswith(CLOCK_PATH):
            start = i
            break
    if start is None:
        return None, None
    for j in range(start + 1, len(lines)):
        s = lines[j].strip().strip('"')
        if s.startswith("/") and (lines[j].rstrip().endswith(":") or lines[j].rstrip().endswith("{")):
            return lines[start:j], (j - start)
    return lines[start:], len(lines) - start


def operation_block(text):
    """The generated client's `getJourneyExecutionClock` operation, which is where its field types
    actually live.

    The client does not inline the response fields under the path key -- it writes
    `get: operations["getJourneyExecutionClock"]` and puts the types under `operations`.  Reading the
    path block alone finds no fields and reports the branch's own regenerated client as carrying
    nothing, so the operation name is resolved and its block read instead.
    """
    m = re.search(r'operations\["(getJourneyExecutionClock)"\]', text)
    if not m:
        return None
    name = m.group(1)
    lines = text.split("\n")
    start = None
    for i, l in enumerate(lines):
        if l.strip().startswith(name + ":"):
            start = i
            break
    if start is None:
        return None
    depth = 0
    for j in range(start, len(lines)):
        depth += lines[j].count("{") - lines[j].count("}")
        if j > start and depth <= 0:
            return "\n".join(lines[start:j + 1])
    return "\n".join(lines[start:])


def main() -> int:
    bad = []
    checks = 0

    contract = io.open(CONTRACT, encoding="utf-8", errors="replace").read()
    block, size = clock_block(contract)
    if block is None:
        bad.append("the contract no longer declares %s" % CLOCK_PATH)
    else:
        body = "\n".join(block)
        if "type: object" in body and "properties:" not in body:
            bad.append("the clock response still declares `type: object` with no properties "
                       "(%d lines in the block) -- the moment's zone is still not in the contract"
                       % size)
        for field in ("used_timezone", "timezone_honoured"):
            checks += 1
            if field not in body:
                bad.append("the contract does not declare `%s` on the clock response" % field)

    client = io.open(CLIENT, encoding="utf-8", errors="replace").read()
    if "/journeys/{journey_id}/execution-clock" not in client:
        bad.append("the generated client no longer carries %s" % CLOCK_PATH)
    op = operation_block(client)
    if op is None:
        bad.append("the generated client does not reference getJourneyExecutionClock")
    else:
        for field in ("used_timezone", "timezone_honoured"):
            checks += 1
            if not re.search(r"^\s*%s\s*[?:]" % field, op, re.M):
                bad.append("the generated client does not type `%s` on the clock response "
                           "(regenerate it)" % field)

    print("execution-clock contract honesty: %d checks, %d bad" % (checks, len(bad)))
    print("   contract block lines           = %s" % size)
    print("   client counts used_timezone    = %d" % client.count("used_timezone"))
    print("   client counts timezone_honoured= %d" % client.count("timezone_honoured"))
    if bad:
        print("\nARM BITES -- the clock payload's zone is not in the contract or the client:")
        for b in bad:
            print("   " + b)
        return 1
    print("\nARM_QUIET: the contract and the generated client both declare which zone the instant is in.")
    return 0


if __name__ == "__main__":
    sys.exit(main())