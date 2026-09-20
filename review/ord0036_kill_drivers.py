"""ORD-0036 kill evidence driver.

Mutants of `frontend/public/sw.js`.  The first one is not a synthetic mutation at all: it
is the committed file from before this fix, which is the shape the user actually hit.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
REL = "frontend/public/sw.js"
SRC = f"{ROOT}/{REL}"
PRISTINE = f"{ROOT}/review/sw.js.pristine"
LOGDIR = f"{ROOT}/review"
SPEC = "e2e/qoder-service-worker.spec.ts"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()


def git_show(rev: str) -> bytes:
    proc = subprocess.run(
        f"git show {rev}:{REL}", cwd=ROOT, capture_output=True, shell=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"cannot read {REL}@{rev}: {proc.stderr[:200]!r}")
    return proc.stdout


ORIGINAL = git_show("HEAD")
PRISTINE_BYTES = open(SRC, "rb").read()
with open(PRISTINE, "wb") as fh:
    fh.write(PRISTINE_BYTES)
baseline = sha1(PRISTINE)
print(f"pristine sha1 {baseline}   original(HEAD) sha1 {sha1(PRISTINE) if PRISTINE_BYTES == ORIGINAL else hashlib.sha1(ORIGINAL).hexdigest()}")

OLD_FALLBACK = b"""  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() => caches.match(event.request).then((cached) => cached ?? caches.match("/v8/live"))),
  );"""

CASES = [
    (
        "kill36-a-shipped-worker",
        "8371",
        "replace-whole",
        ORIGINAL,
        ["sw-never-answers-script-with-html", "sw-activate-keeps-foreign-caches"],
    ),
    (
        "kill36-b-foreign-cache-wipe",
        "8372",
        "substitute",
        (
            b"        const doomed = keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE);",
            b"        const doomed = keys.filter((key) => key !== CACHE);",
        ),
        ["sw-activate-keeps-foreign-caches"],
    ),
    (
        "kill36-c-html-passed-through",
        "8373",
        "substitute",
        (
            b"""        if (/text\\/html/i.test(response.headers.get("content-type") ?? "")) {
          // Fail the request honestly instead of serving a document where code belongs.
          return Response.error();
        }""",
            b"        // mutant: pass whatever the network handed back",
        ),
        ["sw-never-answers-script-with-html"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]

for name, port, kind, payload, expected_nodes in CASES:
    if name not in only:
        continue
    if kind == "replace-whole":
        open(SRC, "wb").write(payload)
        applied = payload != PRISTINE_BYTES
        print(f"{name}: restored the pre-fix worker verbatim ({len(payload)} bytes)")
    else:
        old, new = payload
        text = PRISTINE_BYTES.decode("utf-8")
        count = text.count(old.decode("utf-8"))
        mutated = text.replace(old.decode("utf-8"), new.decode("utf-8"), 1)
        open(SRC, "wb").write(mutated.encode("utf-8"))
        applied = count == 1 and mutated != text
        print(f"{name}: anchor hits={count}, applied={applied}")
    if not applied:
        print(f"{name}: MUTANT NOT APPLIED — skipping, running the suite here would report a verdict "
              f"from a build that was never mutated")
        shutil.copyfile(PRISTINE, SRC)
        continue

    env = dict(os.environ)
    run_id = f"{name.replace('-', '_')[:12]}{int(time.time()) % 100000:05d}"
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": str(int(port) + 100),
            "CITYNEXUS_BACKEND_PORT": port,
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    proc = subprocess.run(
        f"npx playwright test {SPEC} --reporter=list",
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = proc.stdout + proc.stderr
    lines = out.splitlines()
    with open(f"{LOGDIR}/{name}.log", "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  exit={proc.returncode}")
    if "was not able to start" in out:
        print("  INVALID RUN: a webServer never started")
    else:
        for line in lines:
            if " :: sw-" in line and "Error" in line:
                print(f"  red message: {line.strip()[:200]}")
        for node_id in expected_nodes:
            named = f":: {node_id} " in out
            print(f"  node {node_id}: {'NAMED IN A RED' if named else 'SURVIVED'}")

    shutil.copyfile(PRISTINE, SRC)
    now = sha1(SRC)
    print(f"  restored sha1 {now} {'OK' if now == baseline else 'MISMATCH — STOP'}")
    if now != baseline:
        sys.exit(2)
