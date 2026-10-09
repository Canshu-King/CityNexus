# -*- coding: utf-8 -*-
"""ORD-0557 static arms for frontend/src/lib/failureAttribution.ts.

Four questions, each answered by reading the tree rather than by remembering it:

  A  the four strings this order names, re-located on the current tip;
  B  the two that were moved: the read is in place, the word it now prints is the word the
     dictionary already held, and this branch added no dictionary key;
  C  the two that were NOT moved: where the locale actually lives, and who would have to
     change if the fallback were localized where it is produced;
  D  the dictionary-side gate, in the form ORD-0533 states it: a read key must carry both arms.

Run: python review/taichenggong/fallback_arms_r1.py
Exit: 0 all arms pass / 1 an arm failed / 2 a file could not be read (never folded into "none")
"""

import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SRCROOT = os.path.join(REPO, "frontend", "src")
TARGET = "frontend/src/lib/failureAttribution.ts"
LABELS = "frontend/src/i18n/travelerLabels.ts"
LOCALE = "frontend/src/i18n/LocaleContext.tsx"
INBOX = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
SETUP = "frontend/src/features/setup/JourneyTrialSetup.tsx"
REF = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = os.path.join(HERE, "fallback_arms_r1.txt")

failures = []
lines = []


def say(text):
    lines.append(text)


def read(rel):
    path = os.path.join(REPO, *rel.split("/"))
    if not os.path.isfile(path):
        raise SystemExit("2 cannot read %s" % path)
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read().splitlines()


def hits(rel, pattern):
    rx = re.compile(pattern)
    return [(i + 1, ln.strip()) for i, ln in enumerate(read(rel)) if rx.search(ln)]


def walk_sources():
    for root, dirs, files in os.walk(SRCROOT):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "__snapshots__")]
        for name in files:
            if name.endswith((".ts", ".tsx")) and not name.endswith((".d.ts",)):
                yield os.path.relpath(os.path.join(root, name), REPO).replace("\\", "/")


def git(*args):
    return subprocess.run(["git", "-C", REPO] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def check(name, ok, detail):
    say("%-4s %s :: %s" % ("OK" if ok else "RED", name, detail))
    if not ok:
        failures.append(name)


def main():
    tip = (git("ls-remote", "origin", REF).split() or [""])[0]
    if len(tip) != 40:
        raise SystemExit("2 ls-remote gave no 40-character tip")
    say("0 tip read live for this run: %s" % tip)

    src = read(TARGET)
    tip_src = git("show", "%s:%s" % (tip, TARGET))

    # ---- A -----------------------------------------------------------------------------
    say("A where the four strings this order names sit right now (read, not copied)")
    for label, pattern in (("item1 content-type unknown", r"content-type unknown"),
                           ("item2 empty-body fallback", r"empty \$\{error\.body_kind\} body"),
                           ("item3+4 zh media-type fallback", r'\?\? "未知"')):
        found = [(n, ln[:70]) for n, ln in
                 [(i + 1, ln) for i, ln in enumerate(src)] if re.search(pattern, ln)]
        say("  %-30s working-tree sites=%d %s" % (label, len(found), [n for n, _ in found]))
    tip_hard = [i + 1 for i, ln in enumerate(tip_src.splitlines()) if '?? "未知"' in ln]
    check("A1 the tip really carried both zh fallbacks", len(tip_hard) == 2,
          "hardcoded zh fallback on the tip at lines %s" % tip_hard)

    # ---- B -----------------------------------------------------------------------------
    say("B the pair that moved")
    reads = hits(TARGET, r'categoryLabel\("UNKNOWN", zh\)')
    check("B1 two reads of the existing key are in place", len(reads) == 2,
          "reads at lines %s" % [n for n, _ in reads])
    left = hits(TARGET, r'\?\? "未知"')
    check("B2 no hardcoded zh fallback left in this file", left == [],
          "still-hardcoded lines %s" % [n for n, _ in left])

    rows = hits(LABELS, r"^\s*UNKNOWN: \{ zh:")
    decl = hits(LABELS, r"^const CATEGORY_LABELS")
    entry_line = None
    for n, _ in rows:
        if decl and n > decl[0][0]:
            entry_line = n
            break
    check("B2b the CATEGORY_LABELS row the order points at is found", entry_line is not None,
          "CATEGORY_LABELS declared at %s, UNKNOWN rows at %s"
          % ([n for n, _ in decl], [n for n, _ in rows]))
    if entry_line:
        text = dict(rows)[entry_line]
        zh = re.search(r'zh: "([^"]+)"', text)
        en = re.search(r'en: "([^"]+)"', text)
        check("B3 the key resolves to the very word that was removed",
              bool(zh) and zh.group(1) == "未知" and bool(en),
              "%s:%s zh arm %r en arm %r" % (LABELS, entry_line,
                                             zh.group(1) if zh else None,
                                             en.group(1) if en else None))
        check("D1 both arms exist for the key this branch reads", bool(zh) and bool(en),
              "row at %s:%s carries zh and en" % (LABELS, entry_line))
        say("  other UNKNOWN rows in the same table file: %s"
            % [n for n, _ in rows if n != entry_line])

    dict_files = [f for f in git("diff", "--name-only", tip, "--", "frontend/").split()
                  if f and "/i18n/" in f]
    changed = [f for f in git("diff", "--name-only", tip, "--", "frontend/").split() if f]
    check("B4 this branch added no dictionary key", dict_files == [],
          "dictionary files changed by this branch: %s" % (dict_files or "none"))
    say("  files this branch changes: %s" % changed)

    # ---- C -----------------------------------------------------------------------------
    say("C the pair that stayed, and the reason, read off the tree")
    ctor = hits(TARGET, r"^\s*constructor\(status: number")
    check("C1 the error is built where no locale exists", len(ctor) == 1,
          "%s:%s %s" % (TARGET, ctor[0][0], ctor[0][1][:100]) if ctor else "constructor not found")
    classify = hits(TARGET, r"^export function classifyReadFailure")
    say("  %s:%s %s" % (TARGET, classify[0][0], classify[0][1][:100]) if classify else "  no signature found")

    callers = []
    for rel in walk_sources():
        if rel.endswith("failureAttribution.ts"):
            continue
        for n, ln in enumerate(read(rel), 1):
            if "classifyReadFailure(" in ln:
                callers.append("%s:%d" % (rel, n))
    files_out = sorted({c.split(":")[0] for c in callers})
    check("C2 localizing at the production site means changing other files",
          len(callers) > 0 and len(files_out) > 0,
          "%d call sites of classifyReadFailure across %d other files" % (len(callers), len(files_out)))
    for c in callers[:5]:
        say("  caller %s" % c)
    say("  files carrying callers: %s" % files_out)

    locale_global = hits(TARGET, r"citynexus\.locale|documentElement\.lang|navigator\.language|useT\(")
    check("C3 this module holds no locale channel of its own", locale_global == [],
          "locale globals read in this file: %s" % locale_global)
    storage_only = hits(TARGET, r"localStorage")
    say("  (localStorage does appear here, at %s, and only for the journey reference keys - "
        "not for a locale)" % [n for n, _ in storage_only])
    locale_elsewhere = []
    for rel in walk_sources():
        if rel.endswith("LocaleContext.tsx"):
            continue
        for n, ln in enumerate(read(rel), 1):
            if re.search(r"getItem\(\"citynexus\.locale\"\)|documentElement\.lang", ln):
                locale_elsewhere.append("%s:%d" % (rel, n))
    say("  who reads the persisted locale anywhere in the frontend: %s" % (locale_elsewhere or "nobody outside LocaleContext"))
    hook = hits(LOCALE, r"^export function (useT|useLocale)")
    say("  the dotted dictionary is only reachable through context: %s lines %s"
        % (LOCALE, [n for n, _ in hook]))

    sink = hits(INBOX, r"error\.content_type")
    telemetry = hits(TARGET, r"content_type=\$\{content_type\}")
    copy_reads = hits(TARGET, r"attribution\.content_type \?\? categoryLabel")
    say("  the field the second string writes is read at: copy arms %s, telemetry %s, another screen %s"
        % ([n for n, _ in copy_reads], [n for n, _ in telemetry], [n for n, _ in sink]))

    prop = hits(SETUP, r"sealedDemoDetail")
    check("C4 the first string's only consumer declares the prop and never renders it",
          len(prop) == 1 and "useState" not in prop[0][1],
          "%s mentions: %s" % (SETUP, [(n, ln[:60]) for n, ln in prop]))
    rule_sites = []
    for rel in ("frontend/src/app/V8Experience.tsx",
                "frontend/src/features/recovery/RecoveryRequiredPanel.tsx",
                "frontend/src/features/discovery/prepFailureCopy.ts"):
        for n, ln in hits(rel, r"ORD-0273-TEXT|not a safe stand-in|used to print|must not reach"):
            rule_sites.append("%s:%d %s" % (rel, n, ln[:64]))
    say("  standing rule that an error's own prose stays off the screen: %s" % rule_sites[:4])

    text = "\n".join(lines) + "\n"
    open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    sys.stdout.write(text)
    if failures:
        sys.stdout.write("FAIL arms: %s\n" % ",".join(failures))
        raise SystemExit(1)
    sys.stdout.write("PASS all arms green\n")


if __name__ == "__main__":
    ast.parse(open(os.path.abspath(__file__), encoding="utf-8").read())
    main()
