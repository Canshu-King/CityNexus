"""Ruler: two arms must never share a Chrome profile directory, a receipt filename or a screenshot name.

This session paid for it three times.  ba103 and the first bb104 were cp-derived from az102 and only the
receipt and screenshot names got changed, so bb104 died on the profile lock while ba103's "independent
walk" was really a second page inside a browser that az102 was still driving -- readings that looked like
fresh evidence and were not.  Earlier, _go_to_active_chrome_r7 and _r10 wrote into one receipt, so only
one run's lines survived and it cannot be recovered which.  A rule I have to remember is a rule that will
be broken, so the rule lives here and reads the arms themselves.

Screenshot names are only checked when they are literal (shot("half-day-430-before") / path:
"${DIR}/430-aq-after-research.png").  Most arms build the name from shot(`name`) with a caller-supplied
argument or a ${TAG} prefix, and those resolve per run; pretending a variable is a collision would bury the
three real ones under false red.

A pass is only worth anything if the ruler can see a collision, so the control at the bottom is not a
hand-written dictionary -- it runs the same scan() over a temporary directory containing two synthetic
arms that really do share a profile, a receipt and a literal screenshot name.  If scan() cannot catch
that, the ruler exits 2 instead of reporting the tree clean.
"""
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
WALK = ROOT / "trial" / "human_walk"
PROFILE_RE = re.compile(r'launchPersistentContext\(\s*"([^"]+)"|PROFILE\s*=\s*"([^"]+)"')
OUT_RE = re.compile(r'OUT\s*=\s*`\$\{DIR\}/([^`"]+)`|OUT\s*=\s*"\$\{DIR\}/([^"]+)"')
# Literal, non-templated screenshot names only: a name containing ${...} is not one fixed file.
SHOT_RE = re.compile(
    r'\bshot\("([A-Za-z0-9_.-]+)"\)'
    r'|path:\s*"\$\{DIR\}/([A-Za-z0-9_.-]+)\.png"'
    r'|path:\s*`\$\{DIR\}/([A-Za-z0-9_.-]+)\.png`'
)

SYNTH_A = """const ctx = await chromium.launchPersistentContext("D:/synthetic/shared-profile", {
const OUT = `${DIR}/shared-receipt.txt`;
await shot("shared-screen-before");
"""
SYNTH_B = """const PROFILE = "D:/synthetic/shared-profile";
const OUT = `${DIR}/shared-receipt.txt`;
await shot("shared-screen-before");
"""


def scan(walk_dir: pathlib.Path):
    """Return (profiles, receipts, shots, arm_count, declaring_arm_count) as name -> sorted owner sets.

    declaring counts only arms that name a profile or a receipt, because that is the population the
    profile/receipt rule covers; arms that only take screenshots are reported separately.
    """
    profiles: dict[str, set[str]] = {}
    receipts: dict[str, set[str]] = {}
    shots: dict[str, set[str]] = {}
    files = sorted(walk_dir.glob("*.mjs"))
    declaring = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        hit = False
        for match in PROFILE_RE.finditer(text):
            value = match.group(1) or match.group(2)
            if value:
                profiles.setdefault(value.casefold(), set()).add(path.name)
                hit = True
        for match in OUT_RE.finditer(text):
            value = match.group(1) or match.group(2)
            if value:
                receipts.setdefault(value, set()).add(path.name)
                hit = True
        for match in SHOT_RE.finditer(text):
            value = match.group(1) or match.group(2) or match.group(3)
            if value:
                shots.setdefault(value, set()).add(path.name)
        if hit:
            declaring += 1
    return profiles, receipts, shots, len(files), declaring


def clashes(mapping):
    return {k: v for k, v in mapping.items() if len(v) > 1}


def control() -> int:
    """The ruler must catch a real collision.  Returns 0 if it can, else a short reason."""
    with tempfile.TemporaryDirectory(prefix="arm_collision_control_") as tmp:
        box = pathlib.Path(tmp)
        (box / "_synth_a_r1.mjs").write_text(SYNTH_A, encoding="utf-8")
        (box / "_synth_b_r2.mjs").write_text(SYNTH_B, encoding="utf-8")
        profiles, receipts, shots, total, declaring = scan(box)
        if total != 2 or declaring != 2:
            return "saw arms=" + str(total) + " declaring=" + str(declaring) + ", expected 2 and 2"
        pc = clashes(profiles)
        rc = clashes(receipts)
        sc = clashes(shots)
        if len(pc) != 1 or len(rc) != 1 or len(sc) != 1:
            return ("caught " + str(len(pc)) + " profile, " + str(len(rc)) + " receipt and "
                    + str(len(sc)) + " shot clash groups, expected one of each")
        if pc.popitem()[1] != {"_synth_a_r1.mjs", "_synth_b_r2.mjs"}:
            return "caught the clash but not both owners of it"
        if sc.popitem()[0] != "shared-screen-before":
            return "caught a shot clash but not the literal screenshot name"
    return 0


def main() -> int:
    bad = control()
    if bad:
        print("SELFTEST_RED " + bad + " -- a ruler that cannot see a collision is not a pass")
        return 2
    print("SELFTEST_OK synthetic pair sharing profile+receipt+literal screenshot was caught by the same scan()")
    if not WALK.is_dir():
        print("SELFTEST_RED no trial/human_walk directory here, which is not a pass")
        return 4
    profiles, receipts, shots, total, declaring = scan(WALK)
    print("ARMS files=" + str(total) + " declaring_profile_or_receipt=" + str(declaring)
          + " profiles=" + str(len(profiles)) + " receipts=" + str(len(receipts))
          + " literal_screenshots=" + str(len(shots)))
    if total == 0:
        print("SELFTEST_RED no arms found, which is not a pass")
        return 4
    profile_clash = clashes(profiles)
    receipt_clash = clashes(receipts)
    shot_clash = clashes(shots)
    for name, owners in sorted(profile_clash.items()):
        print("PROFILE_CLASH " + name.rstrip("/").split("/")[-1] + " <- " + ", ".join(sorted(owners)))
    for name, owners in sorted(receipt_clash.items()):
        print("RECEIPT_CLASH " + name + " <- " + ", ".join(sorted(owners)))
    for name, owners in sorted(shot_clash.items()):
        print("SHOT_CLASH " + name + " <- " + ", ".join(sorted(owners)))
    count = len(profile_clash) + len(receipt_clash) + len(shot_clash)
    if count:
        print("COLLISIONS " + str(count) + " groups (each one means an arm is reading or writing "
              "another arm's browser, receipt or screenshot)")
        return 1
    print("COLLISIONS 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
