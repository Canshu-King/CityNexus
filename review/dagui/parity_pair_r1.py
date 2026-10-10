import io, os, re, subprocess, sys

KEY = re.compile(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')
PATH = "frontend/src/i18n/LocaleContext.tsx"
BASE_REF = os.environ.get("DAGUI_BASE_REF", "d435cff26d")
MINE = [
    "simulation.readsDidNotAnswerWhichIsNotTheSameAsNoSlot",
    "simulation.theServerAnsweredWithProposalsStillOpenAcceptTheProposalBelowNowPointsAtAcceptingIsWhatChangesThePlan",
    "simulation.theServerProducedProposalsButNoneOfTheItNowListsIsOpenSoAcceptTheProposalWillRefuseAndSayWhyOnItsOwnLine",
    "simulation.now",
    "simulation.thisActionIsUnavailableRightNow",
    "simulation.thePreviousActionHasNotReturnedYet",
]


def load(text):
    i = text.index("const en: Dict")
    j = text.index("const zhCN: Dict")
    k = text.index("const dictionaries")
    out = {}
    for chunk, name in ((text[i:j], "en"), (text[j:k], "zh")):
        d = {}
        for line in chunk.split("\n"):
            s = line.strip()
            if s.startswith("//") or s.startswith("*"):
                continue
            m = KEY.match(line)
            if m:
                d[m.group(1)] = m.group(2)
        out[name] = d
    return out["en"], out["zh"]


base = subprocess.check_output(
    ["git", "show", "%s:%s" % (BASE_REF, PATH)], text=True, encoding="utf-8"
)
with open(PATH, encoding="utf-8") as f:
    now = f.read()

be, bz = load(base)
ne, nz = load(now)
sys.stdout.write(
    "baseline en=%d zh=%d diff=%s\n" % (len(be), len(bz), sorted(set(be) ^ set(bz)))
)
sys.stdout.write(
    "current  en=%d zh=%d diff=%s\n" % (len(ne), len(nz), sorted(set(ne) ^ set(nz)))
)
sys.stdout.write(
    "added en=%d added zh=%d\n"
    % (len(set(ne) - set(be)), len(set(nz) - set(bz)))
)
missing = [k for k in MINE if k not in ne or k not in nz]
sys.stdout.write("my_keys_missing=%d\n" % len(missing))
sys.stdout.write("baseline_text_rewritten=%d\n" % len([k for k in be if be[k] != ne.get(k)]))
sys.stdout.write("baseline_text_rewritten_zh=%d\n" % len([k for k in bz if bz[k] != nz.get(k)]))
assert not missing, missing
assert sorted(set(ne) ^ set(nz)) == sorted(set(be) ^ set(bz)), "parity delta introduced"
sys.stdout.write("PROVEN parity_delta=0 my_keys_both_sides=%d\n" % len(MINE))
