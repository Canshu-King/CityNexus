# -*- coding: utf-8 -*-
"""ORD-0610 现场探针：把代表枝的 presence 放进尖树，用真库真会话各跑两种调用。
一臂给签名成员号，一臂不给，各自把回话原样落文件——不猜异常，跑出来才写。"""
import subprocess
import sys

VENV = r"D:/moodle/CityNexus/backend/.venv/Scripts/python.exe"
TREE = "D:/moodle/_qoder_pinggong_0588/backend"
OUT = "D:/moodle/_pinggong_scratch/0610/"

SCRIPT = r'''
import os, sys
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("tests"))
import conftest  # 同套件一样把测试库钉在临时文件上
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from app.db.session import SessionLocal, ensure_schema
from app.db.models import Journey, LocationObservation, Traveler
from app.main import app

ensure_schema()
client = TestClient(app)
TZ = timezone(timedelta(hours=8))
now = datetime(2026, 11, 3, 9, 0, tzinfo=TZ)
tid = str(uuid4())
with SessionLocal() as s:
    s.add(Traveler(id=tid, display_name="0610 probe", email=None, locale="zh-CN",
                   timezone="Asia/Shanghai", created_at=now.isoformat(), updated_at=now.isoformat()))
    s.commit()
created = client.post("/api/v1/journeys", json={
    "traveler_id": tid, "title": "0610 probe", "city_code": "CN-XIAMEN",
    "timezone": "Asia/Shanghai", "start_at": now.isoformat(),
    "end_at": (now + timedelta(days=2)).isoformat(),
    "budget": {"amount_minor": 90000, "currency": "CNY"}, "planning_mode": "balanced"})
print("A0 走真门建一趟行程 http_status=%d" % created.status_code)
jid = str(created.json()["id"])

with SessionLocal() as s:
    journey = s.get(Journey, jid)
    from app.execution.presence import presence_projection
    print("A1 给签名成员号（真会话、真库）：")
    try:
        presence_projection(s, journey, viewer_member_id="member-1", now=now)
        print("   没抛异常")
    except Exception as exc:
        print("   %s: %s" % (type(exc).__name__, exc))
    print("A2 不给成员号：")
    out = presence_projection(s, journey, viewer_member_id=None, now=now)
    print("   state=%s reason_code=%s" % (out["state"], out["reason_code"]))
    print("A3 尖上这张表实际有哪几列（PRAGMA 现读）：")
    rows = [r[1] for r in s.connection().exec_driver_sql("PRAGMA table_info(location_observations)")]
    print("   %s" % rows)
    print("A4 一枚真行能不能带上成员归属：")
    try:
        LocationObservation(id=str(uuid4()), journey_id=jid, latitude=1.0, longitude=2.0,
                            accuracy_m=5.0, captured_at=now.isoformat(), journey_member_id="member-1")
        print("   构造成功")
    except Exception as exc:
        print("   %s: %s" % (type(exc).__name__, exc))
'''


with open("D:/moodle/_pinggong_scratch/0610/_probe_r1.py", "w", encoding="utf-8") as handle:
    handle.write(SCRIPT)

proc = subprocess.run([VENV, "-X", "utf8", OUT + "_probe_r1.py"], cwd=TREE, capture_output=True)
text = proc.stdout.decode("utf-8", "replace") + "\n[stderr]\n" + proc.stderr.decode("utf-8", "replace")
with open(OUT + "presence_real_db_probe.txt", "w", encoding="utf-8") as handle:
    handle.write("rc=%d\n%s" % (proc.returncode, text))
print(text[-2200:])
sys.exit(proc.returncode)
