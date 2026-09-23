"""微探针：create_savepoint + 外层 rollback 到底能不能把 ORM 已 commit 的行回滚掉？

与门、与路由都无关——先证明机制，再谈是谁绕过了它。自己的临时库，跑完删。
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

TMP = pathlib.Path(tempfile.mkdtemp(prefix="cnx_probe_"))
DB = TMP / "probe.db"
os.environ["CITYNEXUS_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
os.environ["CITYNEXUS_AI_ENABLED"] = "false"
for n in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY", "CITYNEXUS_HERMES_API_KEY"):
    os.environ.pop(n, None)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path("D:/moodle/_qoder_f_ord253_20260923/backend")))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.models import IdempotencyKey  # noqa: E402   # 换无外键的表：探针测的是机制，不是业务
from app.db.session import ensure_schema, engine  # noqa: E402

ensure_schema()
now = datetime.now(timezone.utc).isoformat()
with engine.connect() as conn:
    tx = conn.begin()
    inner = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    inner.add(SimpleNamespace()) if False else None
    row = IdempotencyKey(key="probe-claim", operation="probe", request_hash="h",
                           response_status=None, response_json=None,
                           created_at=now, expires_at=now)
    inner.commit()                       # 模拟 impl 内部那次 commit：只该 RELEASE SAVEPOINT
    with engine.connect() as other:
        seen_inside = other.execute(select(func.count()).select_from(IdempotencyKey)
                                    .where(IdempotencyKey.key == "probe-claim")).scalar()
    tx.rollback()                        # 外层回滚
with engine.connect() as check:
    after = check.execute(select(func.count()).select_from(IdempotencyKey)
                          .where(IdempotencyKey.key == "probe-claim")).scalar()
print(f"机制读数：内层 commit 后、外层提交前，别的连接看到 {seen_inside} 行；"
      f"外层 rollback 之后剩 {after} 行")
print("结论：", "机制可用（同事务同生死成立）⇒ 路由里另有一条独立提交"
      if after == 0 else "机制本身就不成立 ⇒ savepoint 语义在这套组合下不生效")
import shutil
engine.dispose()
for _ in range(20):
    shutil.rmtree(TMP, ignore_errors=True)
    if not TMP.exists():
        break
    import time as _t; _t.sleep(0.2)
assert not TMP.exists(), "自我清理失败"
print("临时目录残留：0")
