"""ORD-0485 -- stage this lane's deliverables into the worktree, scrubbed, and prove the ledger
was not touched.

Rules this implements in code rather than in prose:
  * share tokens never leave the lane. The token values are collected from the receipts' own
    named fields and replaced everywhere, so no heuristic is judging what looks secret; the three
    screenshots that paint a token inside an open fold are not staged at all.
  * the shared ledger (D:/moodle/CITYNEXUS_AGENT_CONTROL.md) must be byte-identical before and
    after this tool runs -- LEDGER_SINGLE_WRITER_V1 says a lane drops a block in the inbox, it
    does not write the book.
  * every staged file is listed with bytes and sha256, so a reader can compare the copy against
    the original without taking this tool's word for it.
"""
import hashlib
import json
import os
import re
import shutil
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
WT = LANE + "/wt"
STAGE = WT + "/review/ord0485-phone-walk"
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"

TOOLS = ["stack_up_r1.py", "static_identity_r2.py", "db_snapshot_r1.py", "db_snapshot_proof_r2.py",
         "walk_phone_r1.cjs",
         "walk_phone_r2.cjs", "share_receive_walk_r1.cjs", "wizard_and_live_share_r1.cjs",
         "server_cells_r1.py", "i18n_key_gap_r1.py", "i18n_key_gap_r2.py", "i18n_gap_pair_r1.py",
         "serve_g1_r1.py", "import_g1_read_r1.cjs",
         "candidate_prereq_r1.py", "make_readings_r1.py", "package_deliverables_r1.py"]

RECEIPTS = [("run/stack_up_r1.json", "stack_up_r1.json"),
            ("run/static_identity_r2.json", "static_identity_r2.json"),
            ("evidence/db_snapshot_proof_r2.json", "db_snapshot_proof_r2.json"),
            ("evidence/i18n_gap_base_gen_r1.json", "i18n_gap_base_gen_r1.json"),
            ("evidence/i18n_gap_candidate_gen_r1.json", "i18n_gap_candidate_gen_r1.json"),
            ("evidence/i18n_gap_pair_r1.json", "i18n_gap_pair_r1.json"),
            ("evidence/walk_r2/walk_r2.json", "walk_r2.json"),
            ("evidence/share_r1/share_r1.json", "share_r1.json"),
            ("evidence/wizard_r1/wizard_r1.json", "wizard_r1.json"),
            ("evidence/server_cells_r1.json", "server_cells_r1.json"),
            ("evidence/i18n_gap_r1.json", "i18n_gap_r1.json"),
            ("evidence/candidate_prereq_r1.json", "candidate_prereq_r1.json"),
            ("evidence/import_face_4861.json", "import_face_4861_G0.json"),
            ("evidence/import_face_4862.json", "import_face_4862_G1.json"),
            ("run/report_ord0485_G0_r2.json", "carrier_G0_pre_fix.json"),
            ("run/report_ord0485_G1_r2.json", "carrier_G1_candidate.json"),
            ("run/report_ord0485_gates.json", "neighbour_word_gates_G1.json"),
            ("run/server_cells_r1.stdout.json", "server_cells_r1_stdout.json")]

SHOTS = [("evidence/walk_r2/A_first_visit.png", "A_first_visit_wizard.png"),
         ("evidence/walk_r2/B_after_sealed_demo.png", "B_hub_sealed_demo.png"),
         ("evidence/walk_r2/C_hub.png", "drawer_hub.png"),
         ("evidence/walk_r2/C_live.png", "drawer_live.png"),
         ("evidence/walk_r2/C_map.png", "drawer_map.png"),
         ("evidence/walk_r2/C_studio.png", "drawer_studio.png"),
         ("evidence/walk_r2/C_stay.png", "drawer_stay.png"),
         ("evidence/walk_r2/C_discover.png", "drawer_discover.png"),
         ("evidence/walk_r2/C_import.png", "drawer_import_PRE_FIX_pill.png"),
         ("evidence/walk_r2/C_bookings.png", "drawer_bookings.png"),
         ("evidence/walk_r2/C_agent.png", "drawer_agent.png"),
         ("evidence/walk_r2/C_authoritative.png", "drawer_authoritative.png"),
         ("evidence/walk_r2/C_intelligence.png", "drawer_intelligence.png"),
         ("evidence/walk_r2/C_twin.png", "drawer_twin.png"),
         ("evidence/walk_r2/C_trash.png", "drawer_trash.png"),
         ("evidence/walk_r2/C_access.png", "drawer_access.png"),
         ("evidence/walk_r2/C_trips.png", "drawer_trips.png"),
         ("evidence/walk_r2/C_me.png", "drawer_me.png"),
         ("evidence/walk_r2/D_trips-tab-bookings.png", "trips_bookings_tab.png"),
         ("evidence/walk_r2/D_inbox-tab-paste.png", "trips_bookings_paste_tab.png"),
         ("evidence/walk_r2/E_stay.png", "stay_screen.png"),
         ("evidence/walk_r2/F_access.png", "access_before_choice.png"),
         ("evidence/walk_r2/G_hub_refresh.png", "hub_hard_refresh.png"),
         ("evidence/share_r1/H4_receive.png", "share_receive_revoked_token.png"),
         ("evidence/share_r1/H5_bad_token.png", "share_receive_unknown_token.png"),
         ("evidence/wizard_r1/J2_receive_live.png", "share_receive_live_token.png"),
         ("evidence/wizard_r1/K5_after_wait.png", "hub_after_creating_a_trip.png"),
         ("evidence/L_import_candidate.png", "import_CANDIDATE_pill.png")]

TOKEN_IN_SENTENCE = re.compile("邀请令牌（服务器原样给的）：([A-Za-z0-9_-]{16,})")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def collect_tokens():
    """The exact token strings this lane minted, read out of its own receipts."""
    toks = set()
    for rel in ("evidence/share_r1/share_r1.json", "evidence/wizard_r1/wizard_r1.json"):
        blob = open(os.path.join(LANE, rel.replace("/", os.sep)), encoding="utf-8").read()
        for m in TOKEN_IN_SENTENCE.finditer(blob):
            toks.add(m.group(1))
        for field in ("token_read_from_rendered_sentence", "live_token_read_from_rendered_sentence"):
            mm = re.search('"%s": "([A-Za-z0-9_-]{16,})"' % field, blob)
            if mm:
                toks.add(mm.group(1))
    return toks


def main():
    ledger_before = sha(LEDGER)
    tokens = collect_tokens()
    os.makedirs(STAGE + "/tools", exist_ok=True)
    os.makedirs(STAGE + "/receipts", exist_ok=True)
    os.makedirs(STAGE + "/shots", exist_ok=True)
    manifest = []

    for t in TOOLS:
        dst = STAGE + "/tools/" + t
        shutil.copyfile(LANE + "/tools/" + t, dst)
        manifest.append({"path": "review/ord0485-phone-walk/tools/" + t,
                         "bytes": os.path.getsize(dst), "sha256": sha(dst)})

    for rel, name in RECEIPTS:
        src = os.path.join(LANE, rel.replace("/", os.sep))
        text = open(src, encoding="utf-8", errors="replace").read()
        hits = 0
        for tok in sorted(tokens, key=len, reverse=True):
            if tok in text:
                hits += text.count(tok)
                text = text.replace(tok, tok[:4] + "MASKED_len32")
        out = STAGE + "/receipts/" + name
        open(out, "w", encoding="utf-8", newline="\n").write(text)
        manifest.append({"path": "review/ord0485-phone-walk/receipts/" + name,
                         "bytes": os.path.getsize(out), "sha256": sha(out),
                         "token_occurrences_masked": hits})

    missing = []
    for rel, name in SHOTS:
        src = os.path.join(LANE, rel.replace("/", os.sep))
        if not os.path.exists(src):
            missing.append(rel)
            continue
        dst = STAGE + "/shots/" + name
        shutil.copyfile(src, dst)
        manifest.append({"path": "review/ord0485-phone-walk/shots/" + name,
                         "bytes": os.path.getsize(dst), "sha256": sha(dst)})

    not_staged = [
        {"local": "evidence/share_r1/H2_after_invite.png",
         "reason": "paints a live share token inside the opened grant fold"},
        {"local": "evidence/share_r1/H3_token_fold.png",
         "reason": "paints a live share token inside the opened grant fold"},
        {"local": "evidence/wizard_r1/J1_access_live.png",
         "reason": "paints live share tokens in three opened grant folds"},
        {"local": "evidence/i18n_gap_r1.json",
         "reason": "SUPERSEDED BY MY OWN DEFECT: r1 wrote to one fixed path, so the candidate run "
                   "overwrote the tip reading and the first delivered sheet quoted that clobbered "
                   "number as the tip's. Replaced by i18n_gap_base_gen_r1.json and "
                   "i18n_gap_candidate_gen_r1.json; the file stays on this machine as the record."},
        {"local": "evidence/walk_r1/walk_r1.json",
         "reason": "first walk run: its drawer helper refused to re-open the covered menu button, so "
                   "every C_* row is an instrument ABORT and would read as a product defect; kept "
                   "locally, superseded by walk_r2"},
    ]
    payload = {"tool": "package_deliverables_r1",
               "staged_at": __import__("datetime").datetime.now().astimezone().isoformat(),
               "tokens_known_and_masked": len(tokens),
               "token_shapes_replaced": sum(m.get("token_occurrences_masked", 0) for m in manifest),
               "manifest": manifest,
               "shots_missing_locally": missing,
               "not_staged": not_staged,
               "ledger_sha256_before": ledger_before,
               "ledger_sha256_after": sha(LEDGER),
               "ledger_untouched": sha(LEDGER) == ledger_before}
    open(STAGE + "/MANIFEST_r1.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps(payload, indent=2, ensure_ascii=False))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps({"staged_files": len(manifest),
                      "tokens_known_and_masked": payload["tokens_known_and_masked"],
                      "token_shapes_replaced": payload["token_shapes_replaced"],
                      "shots_missing_locally": missing,
                      "ledger_untouched": payload["ledger_untouched"]}, indent=2))
    return 0 if payload["ledger_untouched"] and not missing else 4


if __name__ == "__main__":
    sys.exit(main())
