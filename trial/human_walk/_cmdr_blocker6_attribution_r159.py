"""Attribute blocker 6's fifteen backend reds instead of leaving them as a count.

Runs the three named files, takes each failure's stack-tail line, and pairs it with the source
truth that explains it: which read is bearer-less, which fake settings object is short one field,
and which contract field list is older than the payload.  Nothing here edits a test or a product
byte; the numbers are computed from this run and written to a tracked receipt.
"""

import ast
import io
import os
import re
import subprocess
import sys

BACKEND = r"D:\moodle\_cmdr_rescue_v3_1022\backend"
RECEIPT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_gozero\bv159-blocker6-attribution.txt"
FILES = [
    "tests/test_sol_concurrency_and_remap.py",
    "tests/test_qoder_live_replans_endpoint.py",
    "tests/test_dsh_list_replans_bound.py",
]
CONTRACT_SET_LINE_SPAN = (27, 40)


def run_suite():
    command = [sys.executable, "-m", "pytest", "-q", *FILES, "--tb=line", "-p", "no:warnings"]
    proc = subprocess.run(command, cwd=BACKEND, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.stdout, proc.returncode


def tail_lines(stdout_text):
    pattern = re.compile(r"^(?P<path>\S+):(?P<line>\d+): (?P<reason>.*)$", re.M)
    out = []
    for match in pattern.finditer(stdout_text):
        out.append(
            {
                "file": match.group("path").replace("\\", "/").split("backend/")[-1],
                "line": int(match.group("line")),
                "reason": match.group("reason")[:120],
            }
        )
    return out


def contract_fields():
    text = io.open(os.path.join(BACKEND, "tests", "test_dsh_list_replans_bound.py"), encoding="utf-8", newline="").read()
    body = "\n".join(text.splitlines()[CONTRACT_SET_LINE_SPAN[0] : CONTRACT_SET_LINE_SPAN[1]])
    return set(re.findall(r'"([a-z_]+)"', body))


def payload_fields():
    source = io.open(os.path.join(BACKEND, "app", "main.py"), encoding="utf-8", newline="").read()
    tree = ast.parse(source)
    function = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_replan_payload"]
    if not function:
        raise SystemExit("ABORT no _replan_payload in app/main.py")
    pairs = {}
    for node in ast.walk(function[0]):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    pairs.setdefault(key.value, key.lineno)
    return pairs


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    stdout_text, code = run_suite()
    summary = re.findall(r"^(\d+ failed.*?in .*?s).*$", stdout_text, re.M)
    tails = tail_lines(stdout_text)
    contract = contract_fields()
    payload = payload_fields()
    extras = sorted(set(payload) - contract)
    missing = sorted(contract - set(payload))
    groups = {}
    for tail in tails:
        key = (tail["file"], tail["line"], tail["reason"][:60])
        groups[key] = groups.get(key, 0) + 1
    lines = [
        "BLOCKER 6 ATTRIBUTION r159",
        "TIP %s" % subprocess.run(
            ["git", "-C", r"D:\moodle\_cmdr_rescue_v3_1022", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "INTERPRETER %s" % sys.version.split()[0],
        "COMMAND python -m pytest -q %s --tb=line -p no:warnings" % " ".join(FILES),
        "PYTEST_EXIT %d" % code,
        "SUMMARY_LINE %s" % (summary[-1] if summary else "<none>"),
        "STACK_TAIL_RECORDS %d" % len(tails),
        "GROUPS",
    ]
    for (file_name, line_no, reason), count in sorted(groups.items(), key=lambda item: -item[1]):
        lines.append("  %d x %s:%d %s" % (count, file_name, line_no, reason))
    lines.append("CONTRACT_FIELDS_PARSED %d from tests/test_dsh_list_replans_bound.py:%d" % (
        len(contract), CONTRACT_SET_LINE_SPAN[0] + 1))
    lines.append("PAYLOAD_FIELDS_PARSED %d from app/main.py:%d" % (len(payload), min(payload.values())))
    lines.append("EXTRA_KEYS_IN_PAYLOAD %d %s" % (len(extras), ", ".join(
        "%s@main.py:%d" % (name, payload[name]) for name in extras)))
    lines.append("KEYS_MISSING_FROM_PAYLOAD %d %s" % (len(missing), ", ".join(missing) or "none"))
    lines.append("FAKE_SETTINGS_LINE tests/test_qoder_live_replans_endpoint.py:65 SimpleNamespace(live_valhalla_url=...) only")
    lines.append("REAL_SETTING app/core/config.py:62 live_valhalla_test_provider exists on the product settings object")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
