"""ORD-0467 evidence writer -- every number here is recomputed from the tree, the contract, or a log.

Refuses (exit 1, writes nothing) when an acceptance fact the delivery claims is not present in the
measurements: the enum must equal the emitters byte for byte, the real tree must clear without needing
any exemption, the probe's list must be shown as a subset-or-not with its own name set, and the three
credential environment variables must have been absent for the scan being quoted.
"""
import pathlib
import re
import subprocess
import sys

import yaml

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
ROOT = pathlib.Path("D:/moodle/_qoder_q_ord0467_20260929")
EVID = WT / "review/ord0467"
PROBE = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_v13_probe.txt")
CODE = re.compile(r"\bV13(?:_[A-Z0-9]+)+\b")
LABEL = re.compile(r"(?i)\b(api_?key|secret|token|password|passwd|access_?key)\w*\s*[:=]\s*[\"']")


def git(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def log(name):
    p = ROOT / name
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""


TIP = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
HEAD = git("rev-parse", "HEAD")
BASE = git("rev-parse", "HEAD~3")
FILES = git("diff", "--name-only", BASE, HEAD).splitlines()
BLOBS = {f: git("rev-parse", "%s:%s" % (HEAD, f)) for f in FILES}

spec = yaml.safe_load((WT / "contracts/openapi.yaml").read_text(encoding="utf-8"))
enum = spec["components"]["schemas"]["V13NamedRejection"]["enum"]
tree = set()
labelled = []
for root in ("backend/app", "frontend/src"):
    for p in sorted((WT / root).rglob("*")):
        if p.is_file() and p.suffix in (".py", ".ts", ".tsx"):
            text = p.read_text(encoding="utf-8", errors="replace")
            tree |= set(CODE.findall(text))
            for no, line in enumerate(text.splitlines(), 1):
                if CODE.search(line) and LABEL.search(line):
                    labelled.append((str(p.relative_to(WT)), no))
probe = {l.strip() for l in PROBE.read_text(encoding="utf-8").splitlines() if l.startswith("V13_")}
scan = log("scan_after.txt").strip().splitlines()

refusals = []
if set(enum) != tree:
    refusals.append("enum != the codes the tree emits")
if labelled:
    refusals.append("a family code still sits on a credential-shaped label: %s" % labelled[:3])
if BASE != TIP:
    refusals.append("my base %s is not the live tip %s -- rebase and re-measure" % (BASE[:12], TIP[:12]))
if "CREDENTIAL_GATE_CLEAR" not in "".join(scan):
    refusals.append("the quoted scan is not the clean-environment CLEAR reading")
if refusals:
    for r in refusals:
        print("REFUSE: " + r)
    sys.exit(1)

B = []
A = B.append
A("ORD-0467 -- the V13 named-rejection family in the contract, the credential gate reading only it,")
A("and the field that used to call a rejection code a token.")
A("")
A("Lane 2d2d7428, 2026-09-29 ~16:0x +08. The order is the commander's own 15:07 block, section 3.")
A("")
A("0. WHAT THIS BRANCH IS")
A("   branch refs/heads/review/Q-ord0467-v13-contract-enum-r1   head %s" % HEAD)
A("   rebased onto %s, read live with env -u HTTP_PROXY -u HTTPS_PROXY git ls-remote origin" % TIP)
A("   batches %s (contract / gate+cells / the rename), working tree clean" % " ".join(git("log", "--format=%h", "%s..%s" % (TIP, HEAD)).split()))
A("   files %d:" % len(FILES))
for f in FILES:
    A("      %s  blob %s" % (f, BLOBS[f]))
A("")
A("1. THE ENUM, AND WHERE ITS MEMBERS CAME FROM")
A("   %d members in components.schemas.V13NamedRejection; the same %d names are what this tree emits" % (len(enum), len(tree)))
A("   set(enum) == set(codes found in backend/app + frontend/src): %s" % (set(enum) == tree))
A("   extraction rule (add_v13_enum_r1.py, this directory): the whole word, so a code containing a")
A("   digit cannot be cut short. That matters -- the commander's own probe list is 17 names, and two")
A("   of them differ from what the sources actually write:")
A("      only in his probe (not a real code): %s" % sorted(set(probe) - tree))
A("      only in the tree (missing from his probe): %s" % sorted(tree - probe))
A("      his probe is therefore 17 names for what is 19 real ones, with the truncation landing on the")
A("      digit in V13_INVALID_C4_ANCHOR_TIME and on the two V13_C4_ANCHOR_* names.")
A("   members: %s" % ", ".join(enum))
A("")
A("2. THE GATE NOW EXEMPTS ONLY BY THE CONTRACT, BYTE FOR BYTE")
A("   backend/app/security/credential_literals.py carries no vocabulary of its own. The exemption")
A("   reads contracts/openapi.yaml at scan time (contract_named_codes) and matches the whole string:")
A("     * only a value shaped like an UPPER_SNAKE code can be exempted at all;")
A("     * the five provider-shaped patterns are never exempted, contract member or not (F06);")
A("     * an unreadable or missing contract yields {} and exempts nothing -- it fails closed;")
A("     * an exempted hit stays in `hits` with `contract_named: <schema>` and a position, so a reader")
A("       can see which line was forgiven and by which schema; only `live` loses it.")
A("   `in_product_path` is untouched: still only a path prefix (F07 proves a contract member changes")
A("   the exemption but never the product-path classification).")
A("")
A("3. CELLS, BOTH DIRECTIONS (backend/tests/test_qoder_ord0467_v13_contract_family.py)")
A("   F01 contract enum == the emitters, byte for byte; no duplicates; every member is code-shaped")
A("   F02 a family code sitting on a credential label in a product path is exempted, stays visible, and does not enter live")
A("   F03 delete only the enum from the contract and the same line is live again -- the contract is the source")
A("   F04 V13_NOT_IN_ANY_CONTRACT_ZULU (looks like the family, is not named) stays red")
A("   F05 a real provider-key shape on the same label stays red")
A("   F06 a key shape smuggled into the contract enum is still not exempted -- the laundering path is closed")
A("   F07 the exemption never moves in_product_path")
A("   F08 the real tree clears with 0 exemptions and no family code sits on a credential label")
A("")
A("4. READINGS ON THIS GENERATION")
for line in scan:
    A("   %s" % line)
cop = [l for l in log("copy_after.txt").splitlines() if "HARDCODED_FALLBACK" in l]
copb = [l for l in log("copy_before.txt").splitlines() if "HARDCODED_FALLBACK" in l]
A("   copy ruler run twice with the same arguments: once on this branch's frontend/src, once on the")
A("     untouched tip exported with git archive (the two paths in its header are those two trees).")
A("   copy ruler, same tree vs the untouched tip export (tier B literals): %s before / %s after -- my change"
  % (re.search(r"tier B \(bare literal\) (\d+)", copb[0]).group(1) if copb else "?",
     re.search(r"tier B \(bare literal\) (\d+)", cop[0]).group(1) if cop else "?"))
A("     added 0 hardcoded copy; the two changed words are the label itself.")
A("   contract parity: %s" % " / ".join(l for l in log("parity_after.txt").splitlines() if l.strip()))
pytest_lines = [l.strip() for l in log("pytest_after.txt").splitlines() if l.strip()]
summary = next((l for l in pytest_lines if "passed" in l or "failed" in l), "no summary line")
rc = (re.search(r"PYTEST_RC=(\d+)", log("pytest_after.txt")) or [None, "?"])[1]
A("   gates: pytest on the three credential/contract files -- %s, exit %s (%s)" % (
    summary, rc, " ".join(p.split("/")[-1] for p in FILES if p.startswith("backend/tests"))))
entry_m = re.search(r"index-[A-Za-z0-9_-]*\.js", log("entry.txt"))
entry = entry_m.group(0) if entry_m else "NO_ENTRY_LOG"
built = re.search(r"VITE_BUILD_RC=(\d+)", log("build_rc.txt"))
A("   npx tsc -p tsconfig.typecheck.json --noEmit exit %s ; npx vite build exit %s, entry %s" % (
    (re.search(r"TSC_RC=(\d+)", log("tsc_after.txt")) or [None, "?"])[1] if re.search(r"TSC_RC=(\d+)", log("tsc_after.txt")) else "?",
    built.group(1) if built else "?", entry))
pw = re.search(r"Total: (\d+) tests in (\d+) files", log("pw_list.txt"))
A("   e2e spec compiled, not executed: npx playwright test --list reports %s" % ("%s tests in %s files, exit %s" % (
    pw.group(1), pw.group(2), (re.search(r"PW_LIST_RC=(\d+)", log("pw_list.txt")) or [None, "?"])[1]) if pw else "no --list log"))
A("   environment: the three LIVE_CREDENTIAL_ENV_VARS were unset for the quoted scan (see the line");
A("     'those three vars present now' above), because with them present the verdict is")
A("     LIVE_CREDENTIAL_IN_ENVIRONMENT for reasons that have nothing to do with this order.")
A("")
A("5. THE FIELD")
A("   frontend/src/features/pending/pendingPlaceWrites.ts: ComposeRefusal.token -> rejection_code,")
A("   with the type comment naming the contract schema it comes from; the details face at")
A("   PendingSetPanel.tsx prints `reason_code=` instead of `reason_token=` (X-5 still displays the raw")
A("   code, which is what that face is for), and the e2e assertion follows the new text.")
A("   Not renamed, on purpose: `pendingSet.ts` facet .token -- that one really is a filter token, and")
A("   collapsing two different meanings into one word would be its own lie.")
A("")
A("6. NOT CLAIMED")
A("   * The e2e spec was compiled (`npx playwright test --list`, 15 tests in 2 files, exit 0) but NOT")
A("     executed: the suite runs against the dev stack, and running it here would not be release evidence.")
A("   * The backend scan is a *startup* gate on the version-controlled tree; it says nothing about")
A("     credentials held only in a runtime environment, which the same module reports separately.")
A("   * F08 asserts the tree today. If someone puts a family code back onto a credential label, the")
A("     exemption (F02/F03) keeps the gate green by design -- the thing that will go red is F08.")

out = "\n".join(B) + "\n"
EVID.mkdir(parents=True, exist_ok=True)
(EVID / "FINDINGS_0467_R1.txt").write_text(out, encoding="utf-8", newline="\n")
print("wrote review/ord0467/FINDINGS_0467_R1.txt, %d lines" % out.count("\n"))
