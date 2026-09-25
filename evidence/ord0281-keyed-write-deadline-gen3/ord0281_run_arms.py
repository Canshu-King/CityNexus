"""ORD-0281 (keyed half) arms runner: one real spec, five tree shapes, restored byte-exact every time.

Five runs, because one spec cannot show both that the bound fires and that the number is the thing that moved:

  bound2000   the tree's own constant patched to 2 s  -> TA / TB / TD / K1 / K2 read here
  bound1000   the same spec, constant halved, baseline declared  -> TC: the rendered number and the arrival
              time must BOTH move. A dead constant (a second inline copy, or a wrapper nobody calls) keeps one
              of them and goes red.
  ca-*        three counter-arms, each a one-hunk patch that must turn a named arm RED:
              ca_no_delegate  revert readDeadline.ts to the bare write pass-through   -> TB red
              ca_keyless_too  make the key test answer "yes" for a keyless request     -> K1 red
              ca_fixed_secs   freeze the seconds in the sentence to 99                 -> TB red (this is the
                              positive control the standing rule asks for: equality must be able to fail)

Everything is patched from pristine bytes in memory and restored in `finally`, with the restored digest and
`git status` printed before any verdict is discussed -- a mutant left in the tree is worse than no measurement.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
FE = LANE / "frontend"
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
SPEC = "e2e/qoder-ord0281-keyed-write-deadline.spec.ts"
WRITE_DEADLINE = FE / "src/lib/writeDeadline.ts"
READ_DEADLINE = FE / "src/lib/readDeadline.ts"
BASE = os.environ.get("CNX_0281_BASE", "90d29a172e186aab6e6cb138ab4583ccf93bfa68")  # the authority tip moves under a candidate; the run names whichever one it ran on
ARMS = ("TA", "TB", "TC", "TD", "K1", "K2", "K3")
CONST = "export const CLIENT_WRITE_DEADLINE_MS = 60_000;"
DELEGATE = "    return fetchWithWriteDeadline(input, init);"
KEY_TEST = "  if (!headers) return false;"
SECONDS = "  const seconds = Math.round(deadlineMs / 1000);"

RUNS = {
    # The shipped 60 s bound cannot be waited out inside a gate window, so the arms that need a trigger run on a
    # tree whose constant is patched, and the arms that read the shipped value run only on the UNPATCHED tree.
    # Each run's map names every arm, with "skipped" written where the arm does not apply to that tree shape --
    # an expected skip is a stated boundary; an arm that vanished because an earlier red killed the serial chain
    # is how the first two passes lost K3 without anyone noticing.
    "pristine": {"patches": [], "bound_ms": "60000", "baseline_ms": "60000",
                 "expect": {"TA": "passed", "TB": "skipped", "TC": "skipped", "TD": "skipped",
                            "K1": "skipped", "K2": "passed", "K3": "skipped"}},
    "bound2000": {"patches": [(WRITE_DEADLINE, CONST, CONST.replace("60_000", "2_000"))],
                  "bound_ms": "2000", "baseline_ms": "4000",
                  "expect": {"TA": "passed", "TB": "passed", "TC": "passed", "TD": "passed",
                             "K1": "passed", "K2": "skipped", "K3": "passed"}},
    "bound1000": {"patches": [(WRITE_DEADLINE, CONST, CONST.replace("60_000", "1_000"))],
                  "bound_ms": "1000", "baseline_ms": "2000",
                  "expect": {"TA": "passed", "TB": "passed", "TC": "passed", "TD": "passed",
                             "K1": "passed", "K2": "skipped", "K3": "passed"}},
    "ca_no_delegate": {"through": "K3", "intended": "K3", "patches": [(READ_DEADLINE, DELEGATE, "    return fetch(input, init);"),
                                   (WRITE_DEADLINE, CONST, CONST.replace("60_000", "2_000"))],
                       "bound_ms": "2000", "baseline_ms": "4000",
                       "expect": {"TA": "passed", "TB": "passed", "TC": "passed", "TD": "passed",
                                  "K1": "passed", "K2": "skipped", "K3": "failed"}},
    "ca_keyless_too": {"through": "K1", "intended": "K1", "patches": [(WRITE_DEADLINE, KEY_TEST,
                                    "  if (!headers) return true;\n"
                                    "  if (Object.keys(headers).length === 0) return true;"),
                                   (WRITE_DEADLINE, CONST, CONST.replace("60_000", "2_000"))],
                       "bound_ms": "2000", "baseline_ms": "4000",
                       "expect": {"TA": "passed", "TB": "passed", "TC": "passed", "TD": "passed",
                                  "K1": "failed", "K2": "skipped", "K3": "failed"}},
    "ca_fixed_secs": {"through": "TB", "intended": "TB", "patches": [(WRITE_DEADLINE, SECONDS, "  const seconds = 99;"),
                                  (WRITE_DEADLINE, CONST, CONST.replace("60_000", "2_000"))],
                      "bound_ms": "2000", "baseline_ms": "4000",
                      "expect": {"TA": "passed", "TB": "failed", "TC": "failed", "TD": "passed",
                                 "K1": "passed", "K2": "skipped", "K3": "passed"}},
}


RED = ("failed", "timedOut")  # a test that never finishes is red, under whatever name the reporter gives it


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def apply(patches):
    """Apply the hunks IN ORDER, accumulating per file; refuse if an anchor is not exactly one line.

    The first version re-read each file from its pristine bytes for every hunk, so on a file carrying two hunks
    the second silently undid the first -- which is why two of the three counter-arms measured nothing at all in
    the first full pass. A mutant that never landed can neither condemn a spec nor exonerate it, so a hunk that
    changes nothing is now an error rather than a pass.
    """
    pristine = {p: p.read_bytes() for p in {pp for pp, _, _ in patches}}
    current = dict(pristine)
    for p, needle, repl in patches:
        text = current[p].decode("utf-8")
        hits = [i + 1 for i, l in enumerate(text.splitlines()) if needle in l]
        if len(hits) != 1:
            raise SystemExit(f"anchor is not unique in {p.name}: {hits} for {needle!r}")
        current[p] = text.replace(needle, repl, 1).encode("utf-8")
    for p, b in current.items():
        if b == pristine[p]:
            raise SystemExit(f"the declared patch would change nothing in {p.name}")
        p.write_bytes(b)
    return pristine


def env_for(run_id: str, port: str) -> dict:
    e = dict(os.environ)
    db = (LANE / "backend" / f"_{run_id}.db").as_posix()
    e.update({
        "CITYNEXUS_E2E_AUTHORITATIVE": "1",
        "CITYNEXUS_E2E_PORT": port,
        "CITYNEXUS_BACKEND_PORT": str(int(port) + 38000),
        "CITYNEXUS_PYTHON": r"D:\moodle\CityNexus\.venv\Scripts\python.exe",
        "CITYNEXUS_E2E_RUN_ID": run_id,
        "CITYNEXUS_DATABASE_URL": f"sqlite:///{db}",
        "CITYNEXUS_AI_ENABLED": "false",
        "CITYNEXUS_EVIDENCE_DIR": str(WORK / f"e2e_ord0281_{run_id}"),
    })
    e.pop("DEEPSEEK_API_KEY", None)
    e.pop("CITYNEXUS_AI_API_KEY", None)
    return e


def play(spec_env: dict, json_out: pathlib.Path, log_out: pathlib.Path) -> dict:
    env = dict(spec_env)
    env["PLAYWRIGHT_JSON_OUTPUT_NAME"] = str(json_out)
    r = subprocess.run(["node", "node_modules/@playwright/test/cli.js", "test",
                        "-c", "playwright.config.ts", SPEC, "--reporter=json"],
                       cwd=str(FE), env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1800)
    log_out.write_text((r.stdout or "") + (r.stderr or ""), "utf-8", newline="\n")
    outcomes = {}
    if json_out.exists():
        rep = json.loads(json_out.read_text(encoding="utf-8"))

        def walk(n):
            for s in n.get("suites", []) or []:
                walk(s)
            for sp in n.get("specs", []) or []:
                m = re.match(r"ord0281-(T[A-D]|K[0-9])", sp.get("title", ""))
                if not m:
                    continue
                for tt in sp.get("tests") or []:
                    for res in tt.get("results") or []:
                        outcomes.setdefault(m.group(1), res.get("status"))
        walk({"suites": rep.get("suites") or []})
    return {"rc": r.returncode, "outcomes": outcomes, "log": log_out.name}


def main() -> int:
    tip = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    if tip != BASE:
        # What has to be reachable from HEAD is the authority tip -- not its parent: a candidate can be more
        # than one commit deep over the base (gen-3 is, after the instrument fixes), and comparing only HEAD^
        # refused to measure exactly the tree it was pointed at.
        anc = subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, tip],
                             capture_output=True).returncode
        if anc != 0:
            raise SystemExit(f"{BASE[:12]} is not an ancestor of HEAD ({tip[:12]}); rc={anc}")
        dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain", "frontend/src",
                                "frontend/e2e"], capture_output=True, text=True).stdout.strip()
        if dirty:
            raise SystemExit("product paths are dirty; the run would measure an uncommitted tree: "
                             + dirty[:180])
        print(f"running on candidate {tip[:12]} over base {BASE[:12]}", flush=True)
    stamp = time.strftime("%H%M%S")
    results, digests = {}, {}
    for name, cfg in RUNS.items():
        files = {p for p, _, _ in cfg["patches"]}
        pristine = {p: p.read_bytes() for p in files}
        digests[name] = {"before": {p.name: hashlib.sha256(pristine[p]).hexdigest()[:16] for p in files}}
        try:
            apply(cfg["patches"])
            digests[name]["mutant"] = {p.name: sha(p)[:16] for p in files}
            run_id = ("0281" + {"pristine": "p1", "bound2000": "p2", "bound1000": "p3", "ca_no_delegate": "p4",
                                "ca_keyless_too": "p5", "ca_fixed_secs": "p6"}[name]) + stamp[-4:]
            port = str(4470 + list(RUNS).index(name))  # 4400-4466 belong to runs that are already on disk; stay off their ports
            e = env_for(run_id, port)
            e["CNX_0281_BOUND_MS"] = cfg["bound_ms"]
            e["CNX_0281_BASELINE_MS"] = cfg["baseline_ms"]
            if name == "pristine":
                e["CNX_0281_PRISTINE"] = "1"
            res = play(e, WORK / f"ord0281_{name}_{stamp}.json", WORK / f"ord0281_{name}_{stamp}.log")
            # one file per arm, so a second worker can never overwrite a reading I am about to quote
            per = {}
            # (a joined glob pattern used to make this a path that cannot exist, so a green suite read as MISSING)
            evidence = WORK / f"e2e_ord0281_{run_id}" / "ord0281"
            for f in (sorted(evidence.glob("arm_*.json")) if evidence.exists() else []):
                body = json.loads(f.read_text(encoding="utf-8"))
                per[str(body.get("arm"))] = body
            res["run_id"] = run_id
            res["per_arm"] = {a: {"status": (v or {}).get("status"),
                                  "expectation": (v or {}).get("expectation")} for a, v in per.items()}
            res["expected"] = cfg["expect"]
            res["meets_expectation"] = all(
                ((per.get(a) or {}).get("status") in RED) if want == "failed"
                else (per.get(a) or {}).get("status") == want
                for a, want in cfg["expect"].items())
            order = ["TA", "TB", "TC", "TD", "K1", "K2", "K3"]
            through = cfg.get("through")
            judged = order[: order.index(through) + 1] if through else list(cfg["expect"])
            missing = [a for a in judged if a not in per]
            # arms the intended red took with it are named, never counted as green
            res["arms_judged"] = judged
            res["arms_aborted_by_the_red_arm"] = [a for a in order
                                                  if a not in judged and a not in per]
            res["expected_arms_without_a_file"] = missing
            res["meets_expectation"] = all(
                ((per.get(a) or {}).get("status") in RED) if want == "failed"
                else (per.get(a) or {}).get("status") == want
                for a, want in cfg["expect"].items() if a in judged) and not missing
            if through:  # a counter-arm is only a counter-arm if the arm it names actually went red
                res["meets_expectation"] = bool(res["meets_expectation"]
                                                 and (per.get(cfg["intended"]) or {}).get("status") in RED)
            res["readings"] = {a: (v or {}).get("reading") for a, v in per.items()}
            results[name] = res
            print(f"\n{name}: rc={res['rc']} run={run_id} as_expected={res['meets_expectation']}"
                  + (f" MISSING={missing}" if missing else ""))
            for a in ARMS:
                v = per.get(a) or {}
                rd = v.get("reading") or {}
                print(f"   {a:3s} {str(v.get('status')):8s} verdict={rd.get('verdict')} "
                      f"elapsed={rd.get('elapsed_ms')} named={rd.get('sentence_seconds_named')} "
                      f"screen={str(rd.get('on_screen'))[:34]}")
        finally:
            for p, b in pristine.items():
                p.write_bytes(b)
            ok = all(sha(p) == hashlib.sha256(b).hexdigest() for p, b in pristine.items())
            dirty = subprocess.run(["git", "-C", str(LANE), "status", "--porcelain",
                                    "frontend/src", "frontend/e2e"],
                                   capture_output=True, text=True).stdout.strip()
            print(f"   restored byte-exact={ok} | src+e2e dirty={dirty[:120]!r}")
            digests[name]["restored"] = ok
    verdicts = {n: (results.get(n, {}).get("meets_expectation"), results.get(n, {}).get("outcomes")) for n in RUNS}
    intended = {"ca_no_delegate": "K3", "ca_keyless_too": "K1", "ca_fixed_secs": "TB"}
    bits = {a: (results.get(a, {}).get("per_arm", {}).get(w, {}).get("status") in RED
                and results.get(a, {}).get("meets_expectation"))
            for a, w in intended.items()}
    teeth = all(bits.values())
    baseline_ok = all(bool(verdicts.get(r, (False,))[0]) for r in ("pristine", "bound2000", "bound1000"))
    out = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0281 keyed half · arms",
           "lane": "B c01d72a3", "base_tip": BASE, "spec": SPEC, "runs": results, "digests": digests,
           "counter_arms_bit": teeth, "per_counter_arm_bit": bits,
           "baseline_arms_met": baseline_ok,
           "verdict": ("TEETH_AND_BASELINE" if (teeth and baseline_ok) else "INCONCLUSIVE"),
           "derived_result": None}
    p = WORK / "ord0281_arms_run.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
    print(f"\nverdict={out['verdict']} counter_arms_bit={teeth} baseline_met={baseline_ok} -> {p.name}")
    return 0 if out["verdict"] == "TEETH_AND_BASELINE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
