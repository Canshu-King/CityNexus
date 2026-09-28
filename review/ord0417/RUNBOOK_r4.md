<!-- r4: one filename in r3's Files list was wrong -- GATE_ORD0417R20ONTHELLINE_TRIMMED.txt does not
     exist, the published name is GATE_ORD0417R20ONTHELINE_TRIMMED.txt. Nothing else in r3 changes;
     r3 is left on the branch unreadable-by-edit, per the standing rule that a revision is a new name. -->
# ORD-0417 follow-up readings -- what changed between the delivered block and the line as it stands

Written after the commander reported (02:35) that the line had moved on and that old-generation screen
readings may not be cited against a new tip.  It turned out ORD-0417 itself had already landed:
`git rev-parse <line>:<path>` gives the same four blobs this lane delivered, so there was nothing left
to merge for the product, and the only real gap was generation of evidence.  That gap is closed here.

## Coordinates read back, not typed

    authoritative line at this check   dccd13ad66ea35e9a6d7ca7a3d91a1ae9a579808
    this lane's landed product commits 93a3ff5c79edf51bdb1307b219468ff632b0cb58 (+ f6456642, 0fa903e1, 755828a9)
    branch carrying these new readings refs/heads/review/R-ord0417-tap-names-stop-r5, parent = the line
    superseded rebases, kept untouched  r3 (parent fb6131f3…), r4 (parent 214809685…) -- r4 vs the line
                                        conflicts add/add because the line already carries r3's files

## What each new file is

  (r3 supersedes nothing; it is the current generation)
  GATE_ORD0417R18NEWBASE_TRIMMED.txt   gate on a rebase onto 214809685…: this lane's 18 arms all pass,
                                       8 neighbour `reach` arms red.
  GATE_ORD0417R19NEWBASETIP_TRIMMED.txt  the SAME command on the untouched 214809685… tree: the same 8
                                       neighbour arms red, PLUS 14 of this lane's arms red because the
                                       cell does not exist there.  That pair is what the earlier block
                                       said it lacked.
  GATE_ORD0417R20ONTHELINE_TRIMMED.txt  the gate run against the line as it stands, with no grafting at
                                       all -- this is the reading to cite for "green on the line".
  MAP_TAP_BASE_214809685_R1.json / MAP_TAP_LINE_DCCD13AD_R1.json  the commander's own
                                       `_map_tap_names_stop_r1.js`, on bundles built from each rev by
                                       `cmdr_build_bundle_r1.py`.
  UNTRANSLATED_R3_MAP_BASE_R2.json / UNTRANSLATED_R3_MAP_LINE_R2.json  the commander's
                                       `untranslated_scan_r3.js` (blob 3dad6f0e70c2a0dcce936499f277313618d6b807,
                                       the version that fixed r2's broken en arm) on both bundles.
  (the door self-check is a later child commit of this branch, not part of this pack)

## A correction that belongs to another lane, recorded here rather than acted on

The 02:35 notice named `D:/moodle/_qoder_ledger_inbox/map_0232.md` as the rejected ORD-0417 block.  That
file's own first line says 车道 map and its body is about ORD-0410/ORD-0412 and the tile-notice overlap;
this lane's blocks are `R_0217.md` and `R_0229.md`, both already inserted (`_processed/R_0217.md.inserted_022204`,
`_processed/R_0229.md.inserted_022620`).  Re-running the door the apply path actually calls
(`claim_coordinate_check_r4c.py`, which `ledger_inbox_apply_r1.py:123` names) over `map_0232.md` today
gives exit 0, not 8 -- so the rejection was either against a superseded revision of that file or from a
different door version.  Both readings are published in DOOR_SELFCHECK_R5_R1.txt; nobody should take this
lane's silence as lane map's block being fine, and this lane has not edited another lane's file.
