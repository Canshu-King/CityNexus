### 加闸工 ORD-0592 腿的报警（10-12 20:48）：吸收面 面涨了，成因在下面

跑批第 c2 拍现读，命令原样 `git -C D:\moodle\CityNexus ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`。

| 读数 | 值 | 锚 |
|---|---|---|
| 权威尖 | 3bf57cc0e15ee4defc833e3a3c7463d0be0d2f60 | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 表内枝数 | 41 枚 | docs/REVOLUTION_ABSORPTION_MANIFEST.tsv:2 |
| 已挂吸收代 | 0 枚 | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 未吸收 | 41 条 | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 按 verdict 分 | TO_ABSORB 35 条／CARRIED_BY_REP 6 条 | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 枝对象取不到 | 0 枚 | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 尺退出码 | 4（语义见 live_checks/revolution_absorption_check_r1.py:9） | live_checks/patrol/_absorption_state_20261012.tsv:3 |
| 这一拍的判语 | 面涨了 | live_checks/patrol/_absorption_state_20261012.tsv:3 |

成因怎么读：尺只判两件事——表里每枚枝的 sha 取得到取不到、已声明的吸收代是不是权威尖的祖先。
所以「面涨了」只有三种来路：有人把某行的 absorbed_on 清空了、那枚吸收代不在权威线上了、
或表里多了一行还没落。哪一种都由上面那几行坐标指回对账表自己那一行，不必猜。

这条腿每拍都跑一次尺，并把数落进带日期的状态件 live_checks/patrol/_absorption_state_20261012.tsv（第 3 行是本拍）；同一形状的块不重交，冷却 240 分钟装在腿自己身上（live_checks/patrol/_absorption_cstate.json:1），判定变了或更坏就立刻再交。
