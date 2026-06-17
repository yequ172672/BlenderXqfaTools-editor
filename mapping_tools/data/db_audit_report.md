# 规范骨骼数据库语义审计报告

> 生成时间: 2026-06-17 16:44:43
> 目标文件: `mapping_tools/data/bone_canon_default.json`
> 审计方案: `.omc/plans/db-semantic-audit.md`

## 汇总

| 指标 | 数量 |
|---|---|
| 总别名数 | 714 |
| KEEP (保留) | 712 |
| REMOVE_AUX (辅助骨骼) | 0 |
| REMOVE_MIS (语义错配) | 0 |
| FLAG (待人工复核) | 2 |

## 各条目别名数量

| 条目 | 当前别名数 | KEEP | REMOVE_AUX | REMOVE_MIS | FLAG |
|---|---|---|---|---|---|
| bip01_head | 10 | 10 | 0 | 0 | 0 |
| bip01_l_calf | 22 | 22 | 0 | 0 | 0 |
| bip01_l_clavicle | 18 | 18 | 0 | 0 | 0 |
| bip01_l_finger0 | 14 | 14 | 0 | 0 | 0 |
| bip01_l_finger01 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger02 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger1 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger11 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger12 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger2 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger21 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger22 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger3 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger31 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger32 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger4 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger41 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_finger42 | 13 | 13 | 0 | 0 | 0 |
| bip01_l_foot | 15 | 15 | 0 | 0 | 0 |
| bip01_l_forearm | 20 | 20 | 0 | 0 | 0 |
| bip01_l_hand | 15 | 15 | 0 | 0 | 0 |
| bip01_l_thigh | 17 | 17 | 0 | 0 | 0 |
| bip01_l_toe0 | 11 | 11 | 0 | 0 | 0 |
| bip01_l_upperarm | 18 | 18 | 0 | 0 | 0 |
| bip01_neck | 8 | 8 | 0 | 0 | 0 |
| bip01_pelvis | 13 | 12 | 0 | 0 | 1 |
| bip01_r_calf | 20 | 20 | 0 | 0 | 0 |
| bip01_r_clavicle | 16 | 16 | 0 | 0 | 0 |
| bip01_r_finger0 | 14 | 14 | 0 | 0 | 0 |
| bip01_r_finger01 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger02 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger1 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger11 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger12 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger2 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger21 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger22 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger3 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger31 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger32 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger4 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger41 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_finger42 | 13 | 13 | 0 | 0 | 0 |
| bip01_r_foot | 14 | 14 | 0 | 0 | 0 |
| bip01_r_forearm | 18 | 18 | 0 | 0 | 0 |
| bip01_r_hand | 14 | 14 | 0 | 0 | 0 |
| bip01_r_thigh | 16 | 16 | 0 | 0 | 0 |
| bip01_r_toe0 | 11 | 11 | 0 | 0 | 0 |
| bip01_r_upperarm | 16 | 16 | 0 | 0 | 0 |
| bip01_spine | 9 | 9 | 0 | 0 | 0 |
| bip01_spine1 | 11 | 10 | 0 | 0 | 1 |
| bip01_spine2 | 10 | 10 | 0 | 0 | 0 |

## FLAG 清单（待人工复核）

- `root` @ bip01_pelvis: root 别名在 pelvis 合理但可能让独立根骨误解析进 pelvis。待人工决策
- `chest` @ bip01_spine1: 跨骨架歧义: chest 在中段 spine1，部分骨架 chest=上段 spine2。待人工决策

## REMOVE_AUX 清单（辅助骨骼）

_(无)_

## REMOVE_MIS 清单（语义错配）

_(无)_

## 黑名单建议

_(无需新增)_

## 迁移建议

_(无)_

---

## 结论

数据库没有发现辅助骨骼或语义错配。仅有 2 条 FLAG 待人工复核。
