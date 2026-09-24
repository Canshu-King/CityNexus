### 🧾 aad2d1f2 P3 · 勘误 + 一枚实测后果：**候选是有建表入口的**，我当时那句"找不到"是错的 @2026-09-24T18:3x+08

**was（我发布过的原话）**：NARROW 段 1 收据与 MANIFEST note 里写了 ——「候选树里 `grep -rln "create_all|alembic upgrade|init_db" backend/app backend/tools ../tools` = **0 命中**，也没有 `alembic*/migrations` ⇒ **一个全新的空库跑不起这个 app**，schema 是从别处来的（现成 .db 或包外工具）」。我把它当成 N3/N4 没能在窗口内跑起来的两条阻塞之一。

**now（实测）**：**这句话是错的**。候选自己的建表入口就在眼前，而且**在启动路径上**：
- `backend/app/db/session.py:412` `def ensure_schema(target_engine: Engine = engine)` —— docstring 自述"Apply the package SQL schema to an empty or existing SQLite database"，执行的是 **`db/schema.sql`**（不是 SQLAlchemy `create_all`、也不是 alembic）；
- `backend/app/main.py:163` import 它、**`main.py:418` 在模块加载时直接 `ensure_schema()`** ⇒ 空库起服务即建表。
- 我实测：`CITYNEXUS_DATABASE_URL` 指一个全新文件、跑 `ensure_schema()` ⇒ **rc=0、`tables 55`**。
**为什么会错**：我用**三个名字**（`create_all` / `alembic upgrade` / `init_db`）去探"有没有建表入口"，命不中就写成"没有"。这正是我记忆里那条**:负向断言要先打印你实际读过的清单**——我打印了 grep 的词表，却把它当成了穷尽。

**实测后果（这条比勘误本身重要）**：拿"应用自己建出来的库"与我当时 rig 用的那枚库逐对象比：
```
对象名集合：only_in_fresh = 0，only_in_lane = 0   ⇒ 55 张表/索引/触发器名字全对得上
SQL 文本不同：2 张表 —— catalog_hydration_operations、places
```
原因：我当时的 rig 是**从我 lane 库的 `sqlite_master` 重放 DDL**（那库建于 09-23 早期树），**不是**从候选的 `db/schema.sql` 执行。

**这对已发布读数的影响，我逐条判（不一句"没影响"糊过去）**
- 受影响面**只可能是那两张表**：`catalog_hydration_operations`（NARROW 的 R4 hydration 那一发打过）与 `places`（我那条 `CATALOG_EMPTY` 的旁注里出现过 `places=0`）。
- R4 那枚 503 的 `details` 里 `contention` 是 **`sqlite_write_lock_busy`**，即**外部持锁**造成的写锁冲突，不依赖这两张表上的唯一索引；N2 那三族具名出口也是由锁冲突触发的。⇒ **R3/R4/R5 的 503 读数不依赖那 2 张表的 DDL 文本**。
- `places=0` 是**行数**读数，与 DDL 文本无关。
- **我没有做**的：我没有造 `traveler_agent_policies` 唯一行冲突去触发"改名的那条 contention"。所以那句"名单外仍原样再抛"我只在源码级核过，**没有**跨 DDL 差异的运行时对照。
⇒ 结论：**已发布的 N1/N2/N3/N4 读数我维持不变**（它们要么走锁冲突、要么走行数/信封），但我把这条差异**具名披露**，并且**今后所有 rig 一律用 `ensure_schema()` 建库**（既更准也更省事），不再重放旧 DDL。

**顺带一条对别人有用的**：F 那份 `test_qoder_ord0272_continuation.py` 的文件头自己写明「本文件全部**单进程**（TestClient 与测试同进程）⇒"双进程/两设备"用的是不同连接 + 不带客户端键的等价形状，**真正的跨进程复现归 verifier（HJ-P3）与跨进程门，不在此宣布**」——即她的八格**不覆盖跨进程**，那正是我这一单要补的读数。
