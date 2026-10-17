"""Run the Issue #27 boundary suite once per arm and archive its own现场照.

Why a script instead of eyeballing two runs: the screenshots are the deliverable,
and every earlier pass of this task produced a set whose provenance I could not
state (a red arm aborts before its screenshot line, so the file on disk was the
*other* arm's picture).  This runner therefore records, per arm, the pass/fail
line from the reporter plus the byte size of every png it copied, and refuses to
archive an arm whose report file is missing.

Arms:
  after_patched   -- the working tree as committed
  before_pristine -- the two product files checked out from the named tip
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TIP = os.path.join(ROOT, "tip")
FE = os.path.join(TIP, "frontend")
EVIDENCE = os.path.join(ROOT, "qoder27_evidence")
BASE_SHA = "321d4ab19c6c9d730717cc530de0f58d86b898d1"
PRODUCT_FILES = [
    os.path.join("frontend", "src", "features", "agent", "AgentComposer.tsx"),
    os.path.join("frontend", "src", "features", "agent", "CopilotDock.tsx"),
]
SHOTS = (
    ".qoder27-memberA-桌面.png",
    ".qoder27-memberA-桌面-dock.png",
    ".qoder27-memberA-手机.png",
    ".qoder27-memberA-手机-dock.png",
    ".qoder27-memberB-桌面.png",
    ".qoder27-memberB-桌面-dock.png",
    ".qoder27-memberB-手机.png",
    ".qoder27-memberB-手机-dock.png",
    ".qoder27-forbidden.png",
    ".qoder27-forbidden-dock.png",
)


def git(*args):
    return subprocess.run(["git", *args], cwd=TIP, capture_output=True, text=True)


def _walk_specs(node):
    """Playwright nests suites inside suites; reading only the top level reports
    zero tests for a run that actually passed (observed on the first pass of this
    runner, which is exactly how an instrument swallows its own verdict)."""
    for spec in node.get("specs", []):
        yield spec
    for child in node.get("suites", []):
        yield from _walk_specs(child)


def run_suite():
    report = os.path.join(FE, "e2e", ".qoder27-report.json")
    if os.path.exists(report):
        os.remove(report)
    proc = subprocess.run(
        ["npx", "playwright", "test", "--config", "playwright.qoder27-boundary.config.ts"],
        cwd=FE, capture_output=True, text=True, shell=True,
        encoding="utf-8", errors="replace",
    )
    if not os.path.exists(report):
        raise SystemExit("ABORT: the runner produced no json report, nothing is archived")
    with open(report, encoding="utf-8") as fh:
        data = json.load(fh)
    rows = []
    for suite in data.get("suites", []):
        for spec in _walk_specs(suite):
            rows.append((spec["title"], bool(spec.get("ok"))))
    if len(rows) != 3:
        raise SystemExit("ABORT: expected three arms in the report, parsed %d" % len(rows))
    return rows, report, proc.returncode


def archive(arm, report_path, rows, disk_flag):
    out = os.path.join(EVIDENCE, arm)
    os.makedirs(out, exist_ok=True)
    prefix = "after-" if arm == "after_patched" else "before-"
    shutil.copy2(report_path, os.path.join(out, "report.json"))
    missing = []
    for shot in SHOTS:
        src = os.path.join(FE, "e2e", shot)
        if not os.path.exists(src):
            missing.append(shot)
            continue
        shutil.copy2(src, os.path.join(out, prefix + shot[len(".qoder27-"):]))
    if missing:
        raise SystemExit("ABORT: arm produced no picture for " + ", ".join(missing))
    receipt = {
        "arm": arm,
        "base_sha": BASE_SHA,
        "copilotdock_reads_localstorage": disk_flag,
        "tests": [{"title": t, "ok": ok} for t, ok in rows],
        "screenshots": {
            prefix + s[len(".qoder27-"):]: _sha(os.path.join(FE, "e2e", s)) for s in SHOTS
        },
    }
    with open(os.path.join(out, "receipt.json"), "w", encoding="utf-8") as fh:
        json.dump(receipt, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("after_patched", "before_pristine"))
    args = ap.parse_args()

    if args.arm == "before_pristine":
        r = git("checkout", BASE_SHA, "--", *PRODUCT_FILES)
        if r.returncode:
            raise SystemExit("ABORT: cannot check out the pristine arm: " + r.stderr.strip())
    else:
        r = git("checkout", "HEAD", "--", *PRODUCT_FILES)
        if r.returncode:
            raise SystemExit("ABORT: cannot restore the patched arm: " + r.stderr.strip())

    # Prove which generation the tree actually holds before spending a browser.
    dock = os.path.join(FE, "src", "features", "agent", "CopilotDock.tsx")
    with open(dock, encoding="utf-8") as fh:
        body = fh.read()
    uses_disk = "localStorage" in body
    print("arm=%s copilotdock_reads_localstorage=%s" % (args.arm, uses_disk))
    if args.arm == "after_patched" and uses_disk:
        raise SystemExit("ABORT: patched arm still touches localStorage")
    if args.arm == "before_pristine" and not uses_disk:
        raise SystemExit("ABORT: pristine arm is not the pre-fix code")

    rows, report_path, rc = run_suite()
    out = archive(args.arm, report_path, rows, uses_disk)
    print("reporter_exit=%s tests=%d passed=%d failed=%d" % (
        rc, len(rows), sum(1 for t, ok in rows if ok), sum(1 for t, ok in rows if not ok)))
    for title, ok in rows:
        print("  %s %s" % ("PASS" if ok else "FAIL", title[:70]))
    print("archived -> %s" % out)
    for name in sorted(os.listdir(out)):
        if name.endswith(".png"):
            p = os.path.join(out, name)
            print("  %-40s %8d B  sha256:%s" % (name, os.path.getsize(p), _sha(p)[:10]))


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    main()
