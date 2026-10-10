import io, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARM = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_cmdr_dict_key_arm_r1.py"
TIP = io.open(os.path.join(ROOT, "tip_live_0558b.txt"), encoding="utf-8").read().strip()
OUT = os.path.join(ROOT, "review", "dagui0558", "cmdr_arm_r3.txt")
BR = "review/大柜工-0558-r2"
NEGB = "review/dagui-negarm-throwaway-r2"
NEGF = "frontend/src/__negarm_probe_r1.ts"
log = []


def git(*a):
    return subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", shell=False)


def run(tag):
    p = subprocess.run(["python", ARM, "--repo", "D:/moodle/CityNexus", "--tip", TIP,
                        "--cand", BR if tag.startswith("normal") else NEGB],
                       cwd="D:/moodle", capture_output=True, text=True,
                       encoding="utf-8", errors="replace", shell=False)
    body = (p.stdout or "") + (p.stderr or "")
    log.append("[%s] rc=%d" % (tag, p.returncode))
    log.extend(["  " + l for l in body.splitlines() if l.strip()])
    return p.returncode, body


rc1, body1 = run("normal arm: this branch as committed")

# negative arm: the ruler reads git objects, so the blind test lives on its own
# throwaway branch and adds a NEW frontend file. It never edits a real source file
# and never touches the branch under delivery.
git("checkout", "-q", "-B", NEGB, BR)
io.open(os.path.join(ROOT, NEGF), "w", encoding="utf-8", newline="\n").write(
    'export const __negarm_r1 = (t: any) => t("zzzNegativeArm.KeyNobodyAdded");\n')
git("add", "-f", "--", NEGF)
c = git("-c", "user.name=大柜工", "commit", "-q", "-m",
        "throwaway negative arm: a t() key no dictionary side carries")
log.append("negative commit rc=%d %s head=%s" % (
    c.returncode, (c.stdout + c.stderr).strip(),
    git("rev-parse", "--short", "HEAD").stdout.strip()))
rc2, body2 = run("negative arm: throwaway branch carrying the missing key")
git("checkout", "-q", BR)
git("branch", "-D", NEGB)
still = git("branch", "--list", NEGB)
gone = git("show", "-s", "--format=%h", "HEAD")
dirty = [l for l in git("status", "--porcelain").stdout.splitlines() if l.strip()]
log.append("throwaway_still_present=%d" % len(still.stdout.strip()))
log.append("delivery_branch_head=%s dirty_lines=%d negfile_on_disk=%d"
           % (gone.stdout.strip(), len(dirty),
              int(os.path.exists(os.path.join(ROOT, NEGF)))))
ok = ("VERDICT PASS" in body1 and rc2 != 0 and "MISSING" in body2.upper()
      and len(still.stdout.strip()) == 0 and not os.path.exists(os.path.join(ROOT, NEGF)))
log.append("verdict=%s" % ("PROVEN_two_arms" if ok else "CHECK"))
io.open(OUT, "w", encoding="utf-8").write("\n".join(log) + "\n")
sys.stdout.write("\n".join(log) + "\n")
sys.exit(0 if ok else 6)
