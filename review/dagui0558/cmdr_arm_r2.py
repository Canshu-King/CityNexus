import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARM = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_dict_key_arm_r1.py"
TIP = io.open(os.path.join(ROOT, "tip_live_0558b.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0558", "cmdr_arm_r2.txt")
log = []


def run(tag):
    p = subprocess.run(["python", ARM, "--repo", "D:/moodle/CityNexus", "--tip", TIP,
                        "--cand", "review/大柜工-0558-r2"],
                       cwd="D:/moodle", capture_output=True, text=True, encoding="utf-8",
                       errors="replace", shell=False)
    body = (p.stdout or "") + (p.stderr or "")
    log.append("[%s] rc=%d" % (tag, p.returncode))
    log.extend(["  " + l for l in body.splitlines() if l.strip()])
    return p.returncode, body


def arm_line(noun):
    return "              text: `GET /places?city_code=${cityCode} -> ${knownIds.size} %s`," % noun


p = os.path.join(ROOT, "frontend", "src", "features", "planning", "aiGenerationRun.ts")

# normal arm: this branch as committed calls no key that either dictionary side lacks
rc1, body1 = run("normal arm: this branch as committed")

# negative arm: that ruler reads git objects, not the worktree, so the blind test has
# to be its own throwaway branch carrying a t() key no dictionary side has. It is
# created and deleted locally only, never pushed, and never touches another lane.
NEGB = "review/dagui-negarm-throwaway-r1"
subprocess.run(["git", "-C", ROOT, "checkout", "-q", "-B", NEGB, "review/大柜工-0558-r2"],
               capture_output=True, shell=False)
rows = io.open(p, encoding="utf-8", newline="").read().split("\n")
anchor = [i for i, l in enumerate(rows) if l.startswith("export async function beginAiRun")]
assert len(anchor) == 1, anchor
probe_line = 'const __neg_missing_key_r1 = t("zzzNegativeArm.KeyNobodyAdded");'
rows.insert(anchor[0], probe_line)
io.open(p, "w", encoding="utf-8", newline="").write("\n".join(rows))
c = subprocess.run(["git", "-C", ROOT, "-c", "user.name=大柜工", "commit", "-qam",
                    "throwaway negative arm for the missing-key ruler"],
                   capture_output=True, text=True, encoding="utf-8", shell=False)
assert c.returncode == 0, c.stdout + c.stderr
rc2, body2 = run("negative arm: branch carrying a t() key no dictionary side has")
subprocess.run(["git", "-C", ROOT, "checkout", "-q", "--", p], capture_output=True, shell=False)
subprocess.run(["git", "-C", ROOT, "checkout", "-q", "review/大柜工-0558-r2"],
               capture_output=True, shell=False)
d = subprocess.run(["git", "-C", ROOT, "branch", "-D", NEGB], capture_output=True,
                   text=True, encoding="utf-8", shell=False)
log.append("throwaway branch deleted rc=%d out=%s" % (d.returncode, d.stdout.strip()))
still = subprocess.run(["git", "-C", ROOT, "branch", "--list", NEGB], capture_output=True,
                       text=True, encoding="utf-8", shell=False)
log.append("throwaway_still_present=%d" % len(still.stdout.strip()))
ok = "VERDICT PASS" in body1 and rc2 != 0 and "MISSING" in body2.upper()
log.append("verdict=%s" % ("PROVEN_two_arms" if ok else "CHECK"))
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if ok else 6)
