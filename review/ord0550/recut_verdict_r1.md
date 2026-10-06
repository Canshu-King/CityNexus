### ORD-0550 r1 重切判定：我那一手的意图已在尖上，而且尖上那版比我这份更强 —— 所以不交空切（车道 8ac89982 · 绿化工·小许）

**一、结论先说**

你让我把这枝 rebase 到现尖再交一次。我先按形制做了只读复算，得到的答案是：**重切出来会是一枚空切**，而且如果我把自己那份原样盖上去，会把尖上更强的版本换回旧版。所以我停在这里交判定，不推空枝。

**二、三枚坐标（现读）**

- 我那枝：`refs/heads/review/8ac89982-ord0550-named-anchor-rulers-r1`，头 `ee42859729e9e2332e0551797388281eb4d04b1c`，父 `00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9`。
- 现尖：`cfda610a99592b6c4111dbc5ee7ce0544a8f2fe2`（`refs/heads/mirror/integration-frontend-apple-pass1`，随你信里给的坐标，本机 `git ls-remote` 现取同值）。
- 你报的冲突面就是这一枚：`backend/tests/test_qoder_ord0296_write_deadline.py`（两边都动过）。

**三、两边各自动了什么（逐边现算，不是我记的）**

- 我这一手（`00b5f25e` → `ee428597`）：`backend/tests/test_qoder_ord0296_write_deadline.py` 增删 `29/4`，`backend/tests/test_qoder_ord0479_dictionary_key_shape.py` 增删 `35/2`。
- 尖上那一手（`00b5f25e` → `cfda610a9959`）：同一枚 0296 增删 `58/5`，同一枚 0479 增删 `31/2`（尖上同时还落了另外一批新测试文件，与本单无关）。
- 逐枚 blob 摆一起（证明"不是同一份字节"）：0296 我 `f8383ef8df9f1edf791126308d3e591937f4f41e` vs 尖 `032777990661c5220794a91c2a00a8ed1ea97fe7`；0479 我 `4e19854e341a1d5e61752b691b74276c43124477` vs 尖 `91dffbf0f2244df3cf1eb20bf8f1986d37a97d90`。

**四、为什么判"意图已在尖上"（按名字认，不按行号认）**

- 0479 那把尺：尖上写的是 `_table_line_inside_named_const(SITE, "REFUSAL_KEY", VALUE)`，位置在 `backend/tests/test_qoder_ord0479_dictionary_key_shape.py:159`，判的是"被赦免的那一行落在具名表 `REFUSAL_KEY` 的表身里"——与我那版"按具名符号取表身、再判行落在其中"是同一件事的两种写法。
- 0296 那把尺：尖上那版不再点文件名清单，改成从产品自己读两把尺度——`WD.busy_timeout_ms()` 现取射程（符号在 `backend/app/db/write_deadline.py:50`），加一张出厂只有一枚的单源路径白名单 `SINGLE_SOURCE_FILES`，再加"消费方一边向模块要数、一边自己内联写一枚"的检查。它比我那版更晚，而且带着两条后续裁语（`CMDR 02:45` 收形、`CMDR 18:34` 补盲区），我那份只认内联数字。

**五、尖上那版在自己字节上是绿的（跑出来的，不是读出来的）**

我在本车道目录里把现尖的树取出来（`backend` + `data` + `frontend/src`，只读导出，不碰任何共享工作树），用现成 venv 在一次性库上跑了两把尺：

- `backend/tests/test_qoder_ord0296_write_deadline.py`：`11 passed`，件 `review/ord0550/tip_ruler_0296_r1.txt`。
- `backend/tests/test_qoder_ord0479_dictionary_key_shape.py`：`9 passed / 1 skipped`，件 `review/ord0550/tip_ruler_0479_r1.txt`。

两句交代，免得读数被当成别的意思：头一次跑是我把树裁得太小（少了仓库根的 `data/mock`，`seed_demo` 起不来；又少了 `frontend/src`，ORD-0479 那把尺读不到词典），那两次报的错是我的导出缺件，不是尖上的毛病；补齐后如上。库用的是导出树里的一次性文件，用户的共享预览库一次都没开。

**六、我**没有**做、也不打算做的一件事**

我没有把"我那份"和"尖上那份"做逐例对拍（同一枚坏输入两边各判什么）——那是另一件活，而且尖上那版带着后续裁语，形状已不是我的形状。所以本判定只覆盖两件事：我这一手的意图已在尖上；尖上那版在尖的字节上全绿。若你要的是"并集"或"我那份的形状"，请回一句定点，我按新基重切一版再交，不猜。

**七、建议**

本枝按"被现尖取代"闭单即可；我那枝 `ee428597` 留在线上作为记录，我不删不改。名下另一格（ORD-0577 底栏在四枚主路由之外的屏上如何回答"你在哪"）已在测。

**八、纪律**

他人文件零枚改动、权威线移动零次、他人枝零枚、强推零次、`demo/reset` 零次、共享预览库打开零次、凭据零枚落盘零字打印；本轮只读复算与一次性导出树里的两跑。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
