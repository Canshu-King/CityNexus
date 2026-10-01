# -*- coding: utf-8 -*-
"""ORD-0391 screen read-back - a private store for the day15 export, proven to be this lane's.

`_preview.db` is opened `mode=ro` and copied with the SQLite backup API, so the shared store is never
written. The copy gets one marker row that only this lane's store holds, so a 200 on my port cannot be
another lane's backend answering.
"""
import io
import json
import os
import sqlite3

SRC = r"D:\moodle\_qoder_preview_20260920\_preview.db"
DST = r"D:\moodle\_qoder_lane_S4_0926\wt0391\backend\tierC_ord0391_lane.db"
HERE = r"D:\moodle\_qoder_lane_S4_0926\work\ord0391"
LANE = "1d64acf5-3f5f-48e8-a7b4-9d7a37996edb"


def main():
    if os.path.exists(DST):
        os.remove(DST)
    src = sqlite3.connect("file:%s?mode=ro" % SRC.replace("\\", "/"), uri=True)
    dst = sqlite3.connect(DST)
    with dst:
        src.backup(dst)
    src.close()
    con = sqlite3.connect("file:%s?mode=ro" % DST.replace("\\", "/"), uri=True)
    tables = [r[0] for r in con.execute(
        "select name from sqlite_master where type='table' order by name").fetchall()]
    journeys = con.execute("select id, title, status from journeys order by id limit 6").fetchall() \
        if "journeys" in tables else []
    stops = con.execute("select count(*) from itinerary_stops").fetchone()[0] \
        if "itinerary_stops" in tables else None
    con.close()
    rw = sqlite3.connect(DST)
    rw.execute("create table if not exists lane_marker_0391 (who text, stamp text)")
    rw.execute("delete from lane_marker_0391")
    rw.execute("insert into lane_marker_0391 values (?, ?)", (LANE, "ord0391-screen-r1"))
    rw.commit()
    rw.close()
    out = {"source_opened": SRC, "source_access": "mode=ro, copied with the SQLite backup API",
           "copy": DST, "copy_bytes": os.path.getsize(DST), "tables": len(tables),
           "itinerary_stops": stops,
           "journeys_first_six": [{"id": str(j[0]), "title": j[1], "status": j[2]} for j in journeys],
           "marker": "lane_marker_0391 holds this lane's session id",
           "shared_store_written": False}
    io.open(os.path.join(HERE, "store_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"copy_bytes": out["copy_bytes"], "tables": out["tables"],
                      "journeys": len(out["journeys_first_six"])}, ensure_ascii=False))
    print(json.dumps([j["id"] for j in out["journeys_first_six"]], ensure_ascii=False))
    return 0


raise SystemExit(main())
