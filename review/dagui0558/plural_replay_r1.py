import io, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FE = os.path.join(ROOT, "frontend")
P = os.path.join(ROOT, "frontend", "src", "features", "planning", "aiGenerationRun.ts")
REL = "frontend/src/features/planning/aiGenerationRun.ts"
TIP = "d89cfea25214b4bbb4e886dca765b096237362f1"
OUT = os.path.join(ROOT, "review", "dagui0558", "plural_replay_r1.txt")
TS = os.path.join(FE, "__plural_fn_tmp_r1.ts")
BUNDLE = os.path.join(ROOT, "review", "dagui0558", "plural_fn_bundle_r1.cjs")
ESBUILD = os.path.join(FE, "node_modules", ".bin", "esbuild.cmd")
CALL = '${englishCountNoun(knownIds.size, "place")}'

io.open(TS, "w", encoding="utf-8", newline="\n").write(
    'import { englishCountNoun } from "./src/lib/plural";\n'
    'const out: string[] = [];\n'
    'for (const n of [1, 2, 5, 0]) out.push(String(n) + "|" + englishCountNoun(n, "place"));\n'
    'console.log(out.join("\\n"));\n'
)
b = subprocess.run([ESBUILD, "__plural_fn_tmp_r1.ts", "--bundle", "--platform=node",
                    "--format=cjs", "--outfile=" + BUNDLE],
                   cwd=FE, capture_output=True, text=True, encoding="utf-8",
                   errors="replace", shell=True)
if b.returncode != 0:
    sys.stdout.write("BUNDLE FAILED %s%s" % (b.stdout, b.stderr))
    sys.exit(2)
q = subprocess.run(["node", BUNDLE], cwd=ROOT, capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
os.remove(TS)
os.remove(BUNDLE)
pairs = {}
for line in (q.stdout or "").splitlines():
    if "|" in line:
        k, v = line.split("|", 1)
        pairs[k.strip()] = v.strip()

base_line = next(l for l in subprocess.check_output(
    ["git", "show", "%s:%s" % (TIP, REL)], cwd=ROOT, text=True,
    encoding="utf-8").split("\n") if "${knownIds.size} places`," in l)
now_line = next(l for l in io.open(P, encoding="utf-8", newline="").read().split("\n")
                if "${knownIds.size}" in l and CALL in l)

# 1. the only difference between the two generations is the noun channel
rebuilt = base_line.replace(" places`,", " %s`," % CALL)
only_noun_channel_changed = rebuilt == now_line

# 2. replay both templates with a fixed city code and the real noun from the lib
def fill(line, n, noun):
    return (line.replace("${cityCode}", "TUT")
                .replace("${knownIds.size}", str(n))
                .replace(CALL, noun)
                .strip())

log = ["real englishCountNoun from the shipped lib (not re-implemented): %s"
       % json.dumps(pairs, ensure_ascii=False)]
log.append("before line read from %s: %s" % (TIP, base_line.strip()))
log.append("after line read from the branch: %s" % now_line.strip())
log.append("only_the_noun_channel_changed=%d" % int(only_noun_channel_changed))
bad = 0
for n in ("1", "2", "5", "0"):
    before_str = fill(base_line, n, "")
    after_str = fill(now_line, n, pairs[n])
    want = "1 place`," if n == "1" else "%s places`," % n
    ok = after_str.endswith(want) and before_str.endswith("%s places`," % n)
    if not ok:
        bad += 1
    log.append("size=%s before_shows=%s after_shows=%s want=%s ok=%d"
               % (n, before_str[-30:], after_str[-30:], want, int(ok)))
verdict = "PROVEN" if (bad == 0 and only_noun_channel_changed and len(pairs) == 4) else "CHECK"
log.append("verdict=%s" % verdict)
log.append("note=the enclosing beginAiRun needs a fetch and store harness; that full-chain run was NOT done here")
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if verdict == "PROVEN" else 6)
