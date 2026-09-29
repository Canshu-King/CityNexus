"""ORD-0444 -- drive the screen walk in two states, then prove the new arm bites.

Everything written here is read out of a live run: two page reads against the built bundle served by
this lane's own static server, and a mutation of the product byte that the new test arm must refuse.
The mutation is applied and reverted inside this file, and the revert is verified by re-running the
arms after it.
"""
import io
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

WT = r"D:/moodle/_qoder_newlane_ord0444_20260929/wt2"
BACKEND = os.path.join(WT, "backend")
PRIVATE_DB = os.path.join(BACKEND, "ord0444walk.db")
CLIENT = os.path.join(WT, "frontend/src/features/collections/collections.ts")
WALK = os.path.join(WT, "review/ord0444/prod_r3_screen_walk.cjs")
PY = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
NODE = "node"
BASE = "http://localhost:60186"
API = "http://127.0.0.1:60185/api/v1"
TRAVELER = "11111111-1111-4111-8111-111111111111"
PLACE = "place-beijing-houhai"
OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))
GOOD = 'export const COLLECTIONS_LIST_PATH = "/api/v1/collections";'
BAD = 'export const COLLECTIONS_LIST_PATH = "/collections";'


def post(path, body):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode("utf-8"), method="POST")
    req.add_header("content-type", "application/json")
    return json.loads(OP.open(req, timeout=30).read())


def walk(state):
    env = dict(os.environ)
    # `require` resolves from the script's own directory, so the frontend's modules are named here
    # rather than moving the instrument out of the evidence folder it belongs to.
    env["NODE_PATH"] = os.path.join(WT, "frontend", "node_modules")
    p = subprocess.run([NODE, WALK, BASE, state], capture_output=True, encoding="utf-8",
                       errors="replace", cwd=os.path.join(WT, "frontend"), env=env)
    if p.returncode != 0:
        raise SystemExit("walk failed: " + p.stderr[:400])
    return json.loads(p.stdout)


def rows():
    con = sqlite3.connect(PRIVATE_DB)
    out = (con.execute("SELECT count(*) FROM collection_folders").fetchone()[0],
           con.execute("SELECT count(*) FROM collection_items").fetchone()[0])
    con.close()
    return out


def pytest():
    p = subprocess.run([PY, "-m", "pytest", "tests/test_qoder_ord0444_collections.py", "-q",
                        "--no-header"], cwd=BACKEND, capture_output=True, encoding="utf-8",
                       errors="replace")
    lines = (p.stdout or "").strip().splitlines()
    return p.returncode, [l for l in lines if " passed" in l or " failed" in l], lines


report = {"base": BASE, "api": API, "store_before": rows()}
shelf = post("/collections", {"name": "周末收藏", "owner_traveler_id": TRAVELER})
item = post("/collections/%s/items" % shelf["id"], {"place_id": PLACE, "note": "傍晚去"})
report["seeded_through_the_doors"] = {"shelf_id": shelf["id"], "shelf_name": shelf["name"],
                                      "owner": shelf["owner_traveler_id"],
                                      "item_name": item["name"], "item_note": item["note"]}
report["store_after_seed"] = rows()
report["walk_with_one_row"] = walk("with-one-row")

con = sqlite3.connect(PRIVATE_DB)
con.execute("DELETE FROM collection_items")
con.execute("DELETE FROM collection_folders")
con.commit()
con.close()
report["store_after_clear"] = rows()
report["walk_empty"] = walk("empty")

# --- the new arm against the byte it exists to refuse ---
src = open(CLIENT, encoding="utf-8").read()
assert src.count(GOOD) == 1, "the constant is not where this file thinks it is"
mutated = {}
try:
    open(CLIENT, "w", encoding="utf-8", newline="\n").write(src.replace(GOOD, BAD))
    rc, summary, _ = pytest()
    rc_one, summary_one, lines_one = pytest()
    mutated = {"rc_with_contract_path": rc,
               "summary": [l for l in lines_one
                           if "FAILED" in l or " passed" in l or " failed" in l][-6:],
               "named_arm": "test_the_face_fetches_the_runtime_prefix_not_the_contract_path"}
finally:
    open(CLIENT, "w", encoding="utf-8", newline="\n").write(src)
    back = open(CLIENT, encoding="utf-8").read()
    report["reverted_byte_for_byte"] = (back == src)
rc_after, summary_after, _ = pytest()
report["mutant"] = mutated
report["arms_after_revert"] = {"rc": rc_after, "summary": summary_after}

out = os.path.join(WT, "review/ord0444/prod_r3_walk_and_mutant.json")
json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("loaded panel :", report["walk_with_one_row"]["panel_text"][:120])
print("empty  panel :", report["walk_empty"]["panel_text"][:120])
print("tokens loaded:", report["walk_with_one_row"]["machine_tokens_in_body"],
      "empty:", report["walk_empty"]["machine_tokens_in_body"])
print("mutant       :", mutated.get("summary"))
print("revert ok    :", report["reverted_byte_for_byte"], "arms:", summary_after)
