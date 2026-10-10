## commander 更正 @2026-09-23T03:40+08 —— **上一条（03:38）我推错了一层**：那句"三值、没有第四种 unknown"的文档**在手机那棵树上是对的**；四值只在活线 ⇒ 手机今天看不到 `UNKNOWN_RETRYABLE`

### ① 两棵树不是同一份（这是根因）

```text
活线 _qoder_integration_20260919/backend @ 349c4fa (09-23 03:27)
  app/anywhere_capability.py   75,980 B   sha256_16 cb0e24c14fa7ad73
  CAPABILITY_STATES = ("READY", "HYDRATABLE", "UNKNOWN_RETRYABLE", "UNAVAILABLE")    ← 四值
  GET /api/v1/destinations/capability 在 main.py:2823

手机后端 _qoder_cmdr_gate_20260921/backend @ 53fe8e8 (09-21 18:02)   ← **预览/手机跑的就是这棵**
  app/anywhere_capability.py   23,225 B   sha256_16 0231d36670b8b543       ← 只有活线的 1/3 大
  CAPABILITY_STATES = ("READY", "HYDRATABLE", "UNAVAILABLE")                 ← **三值**
  GET /api/v1/destinations/capability 也**存在**（main.py:2813）
⇒ 两份文件 `identical: False`
```

### ② 更正我上一条的推断

我 03:38 那块写"`app/anywhere_capability.py:13` 的文档那句是过期的"。**对活线成立，对手机那棵树不成立**——那棵树**本来就是三值**，文档与代码**在它内部自洽**。
**成因清楚了**：两棵树在"仲裁冻结 `UNKNOWN_RETRYABLE`"**之前就分了岔**（手机树停在 09-21 18:02），活线后来跟上了那第四态，而**同一个文件的文档段没被顺手改** ⇒ 所以"文档 vs 代码"的分歧**只在活线上是真的**。

### ③ 对 ORD-0239 的直接影响（这条必须写进规格）

```text
手机今天消费的是【三值版本】⇒ 手机上不会出现 UNKNOWN_RETRYABLE
活线四值版本才是路线图的目标面
而"后端 pinned"是我们刻意维持的部署约束（REPRODUCED(tree) vs NOT-DEPLOYED(phone)）
⇒ ORD-0239 的规格必须逐条标明【针对哪棵树】；UI 消费规则（HYDRATABLE_ON_DEMAND 要标"需要加载数据"、先 hydrate、重判 READY）可以在前端单独落，
  但"把 availability 拆成四轴事实"这一半必须落在活线，手机上要等下次后端换代才能看见。
```
⇒ **同时**：HARNESS 要钉的"11 城矩阵 ＋ support contract 规格"必须**两棵树各出一份**（矩阵在手机上我已经抽验过 place 轴；capability 轴要分别写"三值树怎么说 / 四值树怎么说"）。

### ④ 一条可复用的口径（入册）

**凡"文档与代码不一致"的判定，先确认你看的是哪棵树/哪个提交**——本机同一个 repo 路径下有三棵以上的后端树（活线、pinned、各车道导出），**同一文件的 sha 可以差 3 倍**。我这一条就是差点把"活线的文档落后"写成"产品文档落后"。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。
