"""(ii) 的根因探针：GHOST_MISSION_ROW 那一枚 mission 到底是**哪条连接、哪个事务**放出去的。

1f86a8f 的门测出"占了键却没回填的那一发，库里仍留 1 行 mission"。我先前只把这个事实报成红，
没报出写它的人。这一支不改产品码、不改断言，只做两件事：
  ① 给引擎挂 before_cursor_execute，按顺序记下 INSERT / SAVEPOINT / RELEASE / ROLLBACK TO 与所属连接；
  ② 给 JourneyMission 挂 after_insert，抓 Python 栈，点名写下这一行的那个函数。
库用的是本工具自己的临时文件，绝不指 `_live.db` / 开发库；跑完删干净并回验目录已消失。
"""
from __future__ import annotations

import os
import pathlib
import shutil
import sys
import tempfile
import traceback
import uuid
from datetime import datetime, timedelta, timezone

tmp = pathlib.Path(tempfile.mkdtemp(prefix="cnx_o253_ghost_"))
db = tmp / "probe.db"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")
os.environ["CITYNEXUS_AI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path("D:/moodle/_qoder_f_ord253_20260923/backend")))

assert "_live" not in db.name and "citynexus.db" not in db.name, "SETUP：不许碰用户库"

from fastapi.testclient import TestClient                      # noqa: E402
from sqlalchemy import event, select                           # noqa: E402

from app.commerce.idempotency import canonical_request_signature  # noqa: E402
from app.db.models import IdempotencyKey, JourneyMission        # noqa: E402
from app.db.session import SessionLocal, engine                 # noqa: E402
from app.main import app                                        # noqa: E402

client = TestClient(app)
TZ = timezone(timedelta(hours=8))
CMD_A = "我护照丢了，请告诉我怎么办。"
LOG: list[tuple[int, str, str, str]] = []
STACKS: list[list[str]] = []
_seq = 0


def _note(kind: str, conn, detail: str) -> None:
    global _seq
    _seq += 1
    LOG.append((_seq, kind, f"conn={id(conn):x}", detail[:150]))


PRODUCT_DIR = str(pathlib.Path("D:/moodle/_qoder_f_ord253_20260923/backend/app")).lower()


@event.listens_for(engine, "before_cursor_execute")
def _sql(conn, cursor, statement, parameters, context, executemany):
    head = statement.strip().upper()
    keep = ("INSERT INTO JOURNEY_MISSIONS", "INSERT INTO IDEMPOTENCY_KEYS",
            "SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT", "BEGIN", "COMMIT",
            "ROLLBACK", "DELETE FROM JOURNEY_MISSIONS", "UPDATE IDEMPOTENCY_KEYS")
    if head.startswith(keep):
        _note("sql", conn, head.split("\n")[0])
    if head.startswith("INSERT INTO JOURNEY_MISSIONS"):
        # 写这一行的人：同一个观测点上抓栈，连接身份与栈必然对应
        frames = [f"    {t.filename.split(chr(92))[-1]}:{t.lineno} {t.name}"
                  for t in traceback.extract_stack()[:-1]
                  if PRODUCT_DIR in t.filename.lower().replace("/", "\\")
                  and "site-packages" not in t.filename.lower()]
        STACKS.append(frames[-14:])


# savepoint 边界由上面的 SQL 文本给出（SAVEPOINT / RELEASE / ROLLBACK TO）；这里只记事务级动作
for kind in ("commit", "rollback"):
    def _mk(k: str):
        def _h(conn):
            _note("tx:" + k, conn, "")
        return _h

    event.listen(engine, kind, _mk(kind))


def _rows() -> list[tuple[str, str]]:
    with SessionLocal() as s:
        return [(m.id[:8], m.status) for m in s.scalars(select(JourneyMission)).all()]


# ------------------------------------------------------------------ 复刻 G1 的前置状态
traveler = client.post("/api/v1/travelers",
                       json={"display_name": "ghostprobe", "timezone": "Asia/Shanghai"})
assert traveler.status_code == 201, traveler.text
start = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
journey = client.post("/api/v1/journeys", json={
    "traveler_id": traveler.json()["id"], "title": "ghostprobe", "city_code": "CNX-DEMO",
    "timezone": "Asia/Shanghai", "start_at": start.isoformat(),
    "end_at": (start + timedelta(days=1, hours=8)).isoformat(),
    "budget": {"amount_minor": 20000, "currency": "CNY"}, "planning_mode": "balanced"})
assert journey.status_code == 201, journey.text
jid = str(journey.json()["id"])
key = f"ghostprobe-{uuid.uuid4().hex[:8]}"
scoped = f"agent.command:{key}"
sig = canonical_request_signature({"journey_id": jid, "command": CMD_A,
                                   "requested_autonomy": "PLAN_ONLY"})
now = datetime.now(timezone.utc)
with SessionLocal() as s:
    s.add(IdempotencyKey(key=scoped, operation="agent.command", request_hash=sig,
                         response_status=None, response_json=None,
                         created_at=now.isoformat(),
                         expires_at=(now + timedelta(days=7)).isoformat()))
    s.commit()
print(f"[setup] journey={jid[:8]} 占位行=未回填  库里 mission 行数={len(_rows())}")

before = len(_rows())
LOG.clear()
STACKS.clear()
r = client.post(f"/api/v1/journeys/{jid}/agent/commands",
                json={"command": CMD_A, "requested_autonomy": "PLAN_ONLY"},
                headers={"Idempotency-Key": key})
after_rows = _rows()

print(f"[read] status={r.status_code} message={str(r.json())[:160]}")
print(f"[read] mission 行：前 {before} → 后 {len(after_rows)}  {after_rows}")
print("\n[事务/语句顺序]（conn= 不同的十六进制就是不同的连接）")
for seq, kind, conn, detail in LOG:
    print(f"  {seq:3d} {kind:24s} {conn:16s} {detail}")
print("\n[写这一行 mission 的栈]（只留产品帧）")
for st in STACKS:
    print("\n".join(st) or "  <没有产品帧>")

same_conn = {c for _, _, c, _ in LOG}
print(f"\n[归属] 出现过的连接数={len(same_conn)} {sorted(same_conn)}")
print(f"[结果] {'GHOST 复现：rollback 之后仍有 ' + str(len(after_rows)) + ' 行' if len(after_rows) > before else '这一支没复现（0 新增行）'}")

engine.dispose()
shutil.rmtree(tmp)
print(f"[收尾] 临时目录已删并回验：{not tmp.exists()}  库文件存在={db.exists()}")
