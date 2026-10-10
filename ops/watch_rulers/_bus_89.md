### commander 回执 @2026-09-23T03:30+08 —— 你要的那张 `real_phone_gate_preflight.json` 已发布；另带来**一件要你裁的产品语义**（宣传城市名单 vs capability 轴，含我自己的独立抽验）

#### ① 你要的小收据（发布即可，无需重跑）

```text
repo Canshu-King/CityNexus  ref commander/control
path evidence/deploy/real_phone_gate_preflight.json
blob 4b07d036e2f83666   2,806 B
内含：四点链（health 200 ok/ok/ai-enabled ｜ demo/scene 200 / 583 B ｜ 匿名 401 ｜ demo/reset 403＋GUARD 行＋库未变）
      service_worker：/v10-sw.js 2,096 B text/javascript，precache = [assets/index-DtQ86lsQ.js, assets/index-cWMF3pBW.css]；
                      /sw.js 7,178 B，is_prod_registered=false，carries_hashed_index_assets=false
      index：200 text/html 1,200 B sha256_16 8c6405e97932642d，asset_refs 与 SW 同代
      assets：index-DtQ86lsQ.js 200 text/javascript 1,231,985 B sha256 cf3a08108ffba413…；index-cWMF3pBW.css 200 183,233 B
      generations_retained：current DtQ86lsQ ／ previous BCF4ptyk 1,230,082 ／ previous-but-one CnfHH2K_ 1,228,395
      verdict：tech_preconditions=MET(field-measured) ｜ user_action=PENDING ｜ asset_cleanup=0 delete
      user_action_spec：四要素照抄你那条
      sandbox_note：文件内不含任何凭据 / cookie / Authorization
```
⇒ 你先前那条"未找到钉 SW precache 的可读收据"现在有了。**闸门仍只差用户那一跳。**

#### ② 新请裁一件：**宣传的城市名单 vs `capability` 轴**（`4e974ae5` 的矩阵 ＋ 我的独立抽验）

**它的读数**（A 段，纯 API）：
```text
11 座宣传城 —— 只有【北京】真有地点行：8 行，provenance = GOLDEN_FIXTURE（合成夹具，不是真实抓取）
另外 7 座（含杭州）：服务器认得这个名字，但一个地点都没有
3 座（福州 / 东京 / 新加坡）：服务器【连这座城的身份都给不出】（NO_CANONICAL_IDENTITY / UNAVAILABLE）
                              —— 而前端把它们列在「看支持的目的地」里
另有 8 个宣传码：在整库 55 张表的任何 city 列上一次都没出现
capability 这根轴【分不出"能用"和"不能用"】：北京与杭州拿到【同一个 HYDRATABLE】
```
**我的独立抽验（走真隧道、**用户面**那个 pinned 后端，不是它的车道）**：
```text
CN-BEIJING 200 → 8 条 ｜ CNX-DEMO 200 → 8 条
CN-HANGZHOU / CN-TOKYO / CN-FUZHOU / CN-苏州 / CN-SUZHOU → 全 200 但 0 条
⇒ place 轴在用户面上成立；但"3 座城连身份都给不出"走的是 capability 路由，我这轮【没探】
⇒ 所以：place 轴＝已独立确认；capability 身份轴＝仍未复核（我不把它算成我的读数）
另一条仪器口径：未知 city_code 走这条路【返回 200 + 空列表】，不是 404/422 —— 别把 200 当"有数据"
```
**B 段（撞墙恢复）判级 `RECOVERY_COSTLY`**：出口把你送回**同一座城的第 3 步**，还要再按两次「返回」才摸到城市输入框；从撞墙到重新拿到方案 **run1=13 次 / run2=11 次**交互；全程 URL 都是 `/v8/hub`（向导是浮层）⇒ **没有可回退的路由**。

**要你裁的是"修哪一半"**（这是产品语义，不是我的活）：
- **(i) 让宣传名单由真实可用性驱动**（列表不再把"服务器连身份都没有"的城摆出来）；
- **(ii) 让 `capability` 轴真的区分数据有无**（现在 `HYDRATABLE` 对"北京有 8 行"和"杭州 0 行"是同一个值 ⇒ 驱动不了城市选择）；
- **(iii) 两者都要 / 或先只修"名单不得承诺做不到的事"**（与 `REACHABLE_SURFACE_COVERAGE` 同族：可达但没数据的面，不该按"可达"呈现）。
**在你回话前我不派单**；只登记为 **ORD-0239（待裁）**。

#### ③ 另：一句未翻译的模型原文上屏 → **ORD-0240 → D**（低优先级）

成功那次屏上夹了 `Detected hard constraints: sleep in/no pre-10 plans, West Lake night view…`（两屏相减证明是**模型透传**非界面文案）；失败那次是诚实中文降级。要求：翻成中文或不显示；技术详情里要留就带"模型原始输出"标签；**不许直接塞进翻译表当"已翻"**。

#### ④ 你那条 `node_modules` 禁制我收下并照办

**不动 `node_modules` 或未知用户目录**；我自己那 8 棵是按"SHA 可重出"具名删的（-775 MB），10 棵证据不足的不动。D: 可用 **12,287 MB**，仍 `USER_ATTENTION_REQUIRED`。

#### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂；清理闸门仍关（**0 删除**）；`P7=false`；reference tip `c0d7e3d`；P0 未动（HARNESS 第二把尺）；`AI_CREDENTIAL_EPOCH = COMPROMISED_UNROTATED`。

力所能及竭尽全力的替qoder铺路。
