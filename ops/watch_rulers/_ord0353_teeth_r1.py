"""ORD-0353 teeth: put each regression back on purpose and show which assertion bites.

One mutation at a time, always restored, so the shipped tree is the tree that was measured.
"""
import io
import re
import subprocess
import sys

ROOT = r"D:\moodle\_qoder_ord0344_S1\frontend"
WIZARD = ROOT + r"\src\features\setup\JourneyTrialSetup.tsx"
FACTS = ROOT + r"\src\lib\rawFacts.ts"
PANEL = ROOT + r"\src\components\RawFactsPanel.tsx"


def read(path):
    return io.open(path, encoding="utf-8").read()


def write(path, text):
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def replace_once(path, old, new):
    text = read(path)
    hits = text.count(old)
    if hits != 1:
        raise SystemExit(f"ABORT: {path} matched {hits} times, expected exactly 1")
    write(path, text.replace(old, new))


def restore(path):
    subprocess.run(["git", "restore", path], cwd=ROOT + r"\..", check=True)


def run(title_fragment):
    proc = subprocess.run(
        "npx playwright test --config=playwright.ord0353-S1.config.ts -g "
        + '"'
        + title_fragment
        + '"',
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    nodes = sorted(set(re.findall(r"qoder-ord0353-[^\n]*? :: ([a-z0-9-]+) —", out)))
    passed = "passed" in out and " failed" not in out
    return proc.returncode, nodes, passed


MUTATIONS = [
    (
        "M1 fold removed from the failure screen (the ORD-0353 shape before this order)",
        [
            (
                WIZARD,
                lambda t: re.sub(
                    r"\n *<details className=\"trial-technical\".*?</details>\n",
                    "\n",
                    t,
                    flags=re.S,
                ),
            )
        ],
        "the fold is on the failure screen",
    ),
    (
        "M2 the answered body's own text rides into a data-* attribute (Q71 class r6 cannot see)",
        [
            (
                FACTS,
                lambda t: t.replace(
                    "    receipt: readErrorReceipt(parseJsonOrNull(rawText)),",
                    "    receipt: (() => {\n"
                    "      const view = readErrorReceipt(parseJsonOrNull(rawText));\n"
                    "      return { ...view, attrs: { ...view.attrs, \"data-body-head\": rawText.slice(0, 40) } };\n"
                    "    })(),",
                ),
            )
        ],
        "the fold is on the failure screen",
    ),
    (
        "M3 the screen invents a receipt-shaped number when the server sent none (Q68)",
        [
            (
                PANEL,
                lambda t: t.replace(
                    "{`${receiptLabel(facts.receipt.present, zh)}：${facts.receipt.text}`}",
                    "{`${receiptLabel(facts.receipt.present, zh)}：${facts.receipt.present ? facts.receipt.text : \"CNX-7K3M9QTB\"}`}",
                ),
            )
        ],
        "no receipt key",
    ),
]

results = []
for label, edits, fragment in MUTATIONS:
    for path, fn in edits:
        text = read(path)
        patched = fn(text)
        if patched == text:
            raise SystemExit(f"ABORT: {label} changed nothing in {path}")
        write(path, patched)
    rc, nodes, passed = run(fragment)
    results.append((label, rc, nodes, passed))
    for path, _ in edits:
        restore(path)
    print(f"{label}\n  exit={rc} bit_nodes={nodes} unexpectedly_green={passed}", flush=True)

clean_rc, clean_nodes, clean_passed = run("the fold is on the failure screen")
print(f"AFTER RESTORE exit={clean_rc} green={clean_passed}", flush=True)
if not all((r[1] != 0 and r[2]) for r in results):
    print("VERDICT: at least one mutation was not caught", flush=True)
    sys.exit(1)
if not clean_passed:
    print("VERDICT: restore did not return the tree to green", flush=True)
    sys.exit(1)
print("VERDICT: all three mutations caught, restored tree green", flush=True)
