# review/jiejian —— ORD-0590 execution 域接尖可行性工件

两份脚本都从远端现取权威尖，不钉死 sha；结论文档在 `docs/revolution-archive/EXECUTION_FEASIBILITY.md`。

## 1. `execution_feasibility_probe_r2.py` —— 一把自包含的尺

```
python execution_feasibility_probe_r2.py
```

环境变量（都有默认值）：`CNX_REPO`（本机工作副本，默认 `D:/moodle/CityNexus`）、
`CNX_TIP_REF`（默认 `refs/heads/mirror/integration-frontend-apple-pass1`）、
`CNX_REP_REF`（默认 `refs/heads/gpt/revolution-r33-open-world-journey-adaptation`）。

它现读两尖后依次给出：代表枝对权威尖的 `backend/app/execution/` 独有模块清单与逐字节比对；
每枚模块的传递依赖闭包，按「权威尖已有 / 缺一个可指名的签名 / 整枚整张根本没有」分类，
其中签名级同时做列级（AST 属性访问）与构造器/调用级（`__init__`、函数形参、dataclass 类体字段三路）；
三态表与去重后的根因；`main.py` 的 API 接线面（撞面路由、新路由、缺的请求模型名）。

退出码：`0` = 出表；`3` = 现取不到尖或代表枝——这时它不猜 sha、不出表。

## 2. `graft_smoke_r1.py` —— 双臂对照的探针

它 import `app.execution.*`，所以要给它一棵 backend 树：

```
git archive <权威尖> backend | tar -x -C <目录>
# A 臂：权威尖原样
PYTHONPATH=<目录>/backend python graft_smoke_r1.py A_tip_as_is
# 把判定为 ① 的那几枚拷进 <目录>/backend/app/execution/ 之后
PYTHONPATH=<目录>/backend python graft_smoke_r1.py B_grafted
```

A 臂给出哪些模块在权威尖上确实取不到、哪些已经在线上；B 臂除 import 外还逐个调一次真函数，
把返回的键与值打出来（指纹长度、解析出的对象、被拒的非法 kind）。
两臂原始读数抄在可行性文档第 5 节。

## 口径

- 行数按 `splitlines()` 计；文件以换行结尾时与 `wc -l` 同值。
- 文档里每个计数都由生成器现算并断言，断言不过就不出文档；尖在写作期间移动过，
  移动带来的 `backend/` 变动与本张引用的文件交集为空，这一点也在断言里。
