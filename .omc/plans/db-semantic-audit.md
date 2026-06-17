# 规范骨骼数据库语义审计方案 (db-semantic-audit)

> 状态: **pending approval** — 规划文档，未执行。
> 用途: 交给 AI 代理执行。本文档自包含，代理只需按章节顺序操作。
> 目标文件: `mapping_tools/data/bone_canon_default.json`
> 数据来源(只读参考): `C:\Users\yequ\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\presets\yuinomodtools\*.py`

---

## 0. 背景与问题

`bone_canon_default.json` 的别名由 `dev_seed_canon.py` 自动生成：扫描 64 个预设文件里的**全部** `(vg, bone)` 映射对，用宽松阈值 0.55 模糊匹配后，把每侧骨骼名都当别名塞进规范条目。该流程**未经人工策展**，存在三类隐蔽噪声：

1. **辅助骨骼残留** — 游戏 rigs 里的变形/服装/毛发/肌肉骨(`Muscle_L_Knee`、`_Twist`、`Hair_*`、`Tie_*`、`Armor`、`Besagew` 等)虽大部分被阈值挡住，但少量可能"刚好够格"被 seed 进核心条目。
2. **语义错配** — 一个真实骨骼名被模糊匹配到**错误的**规范条目(如某别名实际属于大腿却被 seed 进小腿)。
3. **冗余/游戏专属命名** — 同一骨骼的大量命名变体(连字符/空格/下划线/驼峰)、整条 rig 的专属命名，造成 `name_score` 打平(见此前手指错配根因)。

**核心矛盾**：辅助骨骼不该出现在规范库里(它们应进黑名单 `is_core_bone` 过滤，而非当别名)；语义错配的别名会让 `resolve_exact` 把源骨骼导向错误条目，引发 CANON 错配链。

## 1. 目标与范围

**目标**：让 `bone_canon_default.json` 的每个别名都**语义合法**地属于其规范条目，剔除辅助骨骼、错配、冗余噪声。

**范围内**：仅 `bone_canon_default.json` 的 `aliases` 数组。
**范围外**：不改 `canonical_name`/`display_name`/`id`/`category`/`side`/`description`；不改 `modtoolkit.py` 算法；不改用户覆盖层 `bone_canon_user.json`。

## 2. 执行总流程(代理按此顺序)

```
Phase A 准备    → Phase B 逐条目语义审计 → Phase C 汇总报告(dry-run)
→ [人工复核 REMOVE 裁决] → Phase D 应用 → Phase E 验证
```

**铁律：先 dry-run 出报告，REMOVE 裁决必须经人工复核确认后才执行 Phase D。不得跳过复核直接改库。**

## 3. 语义分类法(每个别名归入一类)

对每个 `alias`，结合其所属 `entry` 的解剖含义(见附录 A)，判定：

| 裁决 | 含义 | 处理 |
|---|---|---|
| **KEEP** | 别名是该规范骨骼的合法命名变体(解剖同义词、命名约定变体、侧变体) | 保留 |
| **REMOVE_AUX** | 别名指**辅助/非核心骨骼**(变形肌、服装、毛发、武器、道具、表情细节等)，根本不该进规范库 | 移除，并记入黑名单建议 |
| **REMOVE_MIS** | 别名是真实核心骨骼，但语义属于**另一个**规范条目(错配) | 移除；若能确定正确条目，记"建议迁移" |
| **FLAG** | 不确定/有歧义 | 不动，列入人工复核 |

## 4. 辅助骨骼识别规则(REMOVE_AUX 判定)

别名命中以下**任一**特征 → `REMOVE_AUX`(并进黑名单建议)：

### 4.1 变形/校正骨骼
- 前缀 `Muscle_`、`Muscle.`、`muscle` (如 `Muscle_L_Knee`)
- 后缀/中缀 `Twist`、`_twist`、`-twist` (如 `Bip001-L-Thigh-Twist`、`Muscle_L_CalfTwist`)
- 变形根 `*_Root` 挂在非 pelvis 条目上 (如 `Bone_L_Scapula_Root`、`P_L_Chest_Root`、`Root_L_UpperChest`)
- 校正/修正常见词：`corrective`、`fix`、`helper`

### 4.2 服装/装备/道具
- 关键词：`armor`、`armour`、`besagew`、`pauldron`、`gauntlet`、`greave`、`skirt`、`robe`、`cape`、`cloak`、`scarf`、`belt`、`buckle`、`button`、`strap`、`ribbon`、`bow`(作装饰，非 elbow)、`glove`、`boot`、`shoe`、`hat`、`crown`、`horn`
- 示例：`L_Shoulder_Armor001`、`B_Besagew_L`、`D_Execution`

### 4.3 毛发/面部细节/非骨架
- `hair`、`tie`(领带/绳结，如 `Tie_1`)、`wing`、`tail`、`weapon`、`prop`
- `eyeball`、`smastoid`(乳突肌)、`jaw`(注意：`jaw` 在 head 条目下可 KEEP，需结合条目判断)、`teeth`、`tongue`、`nose`、`ear`、`lip`、`brow`

### 4.4 游戏专属整骨命名
- 含明显游戏/项目标记且无解剖含义的整名：`D_Execution`、`D_*`、`BN_*`、`NonEx_*`、`Po_*`、`Dm_*` 等前缀
- **注意**：单纯的命名风格变体(Bip01-/Bip001-/mixamorig:/spine_01 等)**不算**辅助骨骼，属于 KEEP

> **歧义防护**：`bow` 在 `elbow`/`longbow` 里是误命中。判定时看**整词 token**，不是子串。`left elbow` 的 token 是 `{left, elbow}`，`bow` 不是独立 token → KEEP。代理必须按 token 判断，禁止裸 `in` 子串匹配。

## 5. 语义错配识别规则(REMOVE_MIS 判定)

别名是真实骨骼但挂错条目。判定方法：

1. 解析别名的**主体部位 token**(剔除 side/bip01/mixamorig 等噪声词后的核心词)。
2. 比对附录 A 该 `entry` 的"解剖含义"。
3. 若主体部位与条目含义**不一致** → `REMOVE_MIS`，并注明建议归属条目。

**示例**：
- `left elbow` 挂在 `bip01_l_forearm` → 前臂包含肘关节区域 → KEEP(合法同义)
- `left knee` 挂在 `bip01_l_thigh`(大腿) → 膝盖属于小腿条目 `bip01_l_calf` → `REMOVE_MIS`(建议迁移到 calf)
- `hips`/`pelvis` 挂在非 pelvis 条目 → `REMOVE_MIS`

**侧一致性检查**：`side=left` 的条目，其别名若**仅含右侧标记**(`right`/`_r` 且无 left) → `REMOVE_MIS` 或 `FLAG`。中性别名(`hips`/`spine`/`head`，无侧标记)在 center 条目 KEEP，在 left/right 条目上一般 KEEP(中性同义)。

## 6. 受保护别名(严禁移除)

以下别名是人工验证的 ground truth，**任何情况下不得移除**：

1. 每个条目的 `canonical_name` 与 `display_name` 本身(及其大小写变体)。
2. **手指源命名约定别名**(近期人工补充，pattern 保护)：
   - `thumb\d_[lr]` (如 `thumb0_l`、`thumb2_r`)
   - `(indexfinger|middlefinger|ringfinger|littlefinger)\d_[lr]` (如 `ringfinger3_l`)
3. Bip01/Bip001/Mixamo 标准命名变体(`bip01-l-finger0`、`mixamorig:leftthumbproximal` 等)——这些是核心匹配骨干，KEEP。
4. 解剖学标准同义词(`hips`/`pelvis`/`spine`/`head`/`neck`/`knee`/`elbow`/`wrist`/`ankle` 等)在其正确条目下。

**代理若对某别名是否受保护存疑，一律判 `FLAG`，不得自作主张 REMOVE。**

## 7. 逐条目审计流程(Phase B)

对 `bone_canon_default.json` 的**每个** bone 条目：

1. 读取 `id` / `canonical_name` / `display_name` / `category` / `side`，从附录 A 取该条目解剖含义。
2. 遍历 `aliases` 数组，对每个别名：
   a. token 化(按 `_. : - 空格` 切分，转小写，剔除噪声词 `bip01`/`bip001`/`mixamorig`/`def`/`b005`/`l`/`r`/`left`/`right`)。
   b. 命中第 4 章辅助骨骼特征(token 级) → `REMOVE_AUX` + 黑名单建议。
   c. 否则比对主体部位与条目含义(第 5 章) → 一致 `KEEP` / 不一致 `REMOVE_MIS`。
   d. 命中第 6 章受保护 → 强制 `KEEP`(覆盖 a-c)。
   e. 不确定 → `FLAG`。
3. 记录裁决与理由。

**配额软约束(触发复核，不自动删)**：审计后若某条目别名数 < 3 或 > 25，在报告里标注"异常数量"，人工复核是否删过头或仍有冗余。

## 8. 输出格式(Phase C，dry-run 报告)

生成 `mapping_tools/data/db_audit_report.md` + `db_audit_verdicts.json`：

```json
{
  "generated_at": "<代理填时间>",
  "summary": {
    "total_aliases": 714,
    "keep": 600, "remove_aux": 30, "remove_mis": 15, "flag": 20
  },
  "blacklist_suggestions": ["muscle_", "_twist", "besagew", "armor", "hair", "tie_"],
  "entries": {
    "bip01_l_calf": {
      "aliases": [
        {"alias": "left knee", "verdict": "KEEP", "reason": "膝=小腿条目同义"},
        {"alias": "Muscle_L_Knee", "verdict": "REMOVE_AUX", "reason": "Muscle_ 变形骨"},
        {"alias": "left thigh", "verdict": "REMOVE_MIS", "reason": "主体 thigh 属大腿", "suggest_entry": "bip01_l_thigh"}
      ]
    }
  }
}
```

报告同时输出：每条目的审计前后别名数、黑名单建议清单、迁移建议清单、FLAG 清单。

## 9. 应用(Phase D，人工复核后)

**前置**：人工逐条确认 `REMOVE_AUX` 与 `REMOVE_MIS` 裁决(可批量接受/驳回/改判)。

1. 备份：`cp bone_canon_default.json bone_canon_default.json.bak`。
2. 按确认后的裁决，从对应条目 `aliases` 移除别名。
3. 去重(按 lower) + 跨条目冲突检查(同一 lower 别名不得属两个条目)。
4. 写回 JSON(`ensure_ascii=False, indent=2`)。
5. **不自动改 `modtoolkit.py` 黑名单**——黑名单建议单独列给人工。

## 10. 验证(Phase E)

应用后必须全部通过：

1. **JSON 合法性**：`python -c "import json;json.load(open('data/bone_canon_default.json',encoding='utf-8'))"`
2. **手指 ground truth 不退化**：运行 `python C:\Users\yequ\.claude\skills\bone-db-cleanup\learn_from_preset.py mapping_tools/正确预设.py`，确认 `[L3] 手指段号归一化: 30 对一一对应, 0 处违规`、`30/30` 源/目标精确命中同条目。
3. **解析率不降**：用 `数据库方案log.txt` 与 `传统预设方案log.txt` 里的源骨骼名重跑 `resolve_exact`，核心骨骼(躯干/四肢/手指)解析率不得低于审计前。
4. **受保护别名仍在**：抽样确认 `thumb0_l`/`ringfinger3_l`/`mixamorig:leftthumbproximal` 等仍在库。
5. **别名数合理**：每条目 5~20 之间，无条目归零。

任一不通过 → 回滚 `.bak`，复核裁决。

## 11. 交付清单(代理产出)

- [ ] `mapping_tools/data/db_audit_verdicts.json` — 全量裁决
- [ ] `mapping_tools/data/db_audit_report.md` — 人类可读报告(汇总 + 黑名单建议 + 迁移建议 + FLAG 清单)
- [ ] (复核后)更新 `bone_canon_default.json` + `.bak` 备份
- [ ] 验证报告(第 10 章 5 项结果)
- [ ] `mapping_tools/AGENTS.md` 同步(Common Patterns 补"语义审计"条目，记录别名数变化)

## 12. 安全红线(代理必须遵守)

1. **不跳过人工复核**直接应用 REMOVE。
2. **不动** `canonical_name`/`id`/`category`/`side`/`display_name`/`description`。
3. **不动** `bone_canon_user.json` 与 `modtoolkit.py`。
4. **不动**受保护别名(第 6 章)，存疑一律 FLAG。
5. **不提交 git、不 push、不开 PR**——只改本地文件，由用户决定提交。
6. 应用前**必须备份** `.bak`，验证失败必须能回滚。
7. token 级判定，**禁止裸子串 `in` 匹配**(防 `bow`∈`elbow` 误杀)。

---

## 附录 A：规范条目解剖对照表(审计基准)

代理审计时以此为"该条目应当代表什么"的权威参照。

| entry_id | canonical_name | category | side | 解剖含义 |
|---|---|---|---|---|
| bip01_pelvis | Bip01 Pelvis | torso | center | 骨盆/髋(躯干根) |
| bip01_spine | Bip01 Spine | torso | center | 脊椎下段 |
| bip01_spine1 | Bip01 Spine1 | torso | center | 脊椎中段 |
| bip01_spine2 | Bip01 Spine2 | torso | center | 脊椎上段/上胸 |
| bip01_neck | Bip01 Neck | head_neck | center | 颈 |
| bip01_head | Bip01 Head | head_neck | center | 头 |
| bip01_l_clavicle | Bip01 L Clavicle | arm | left | 左锁骨/肩 |
| bip01_l_upperarm | Bip01 L UpperArm | arm | left | 左上臂 |
| bip01_l_forearm | Bip01 L Forearm | arm | left | 左前臂(含肘区) |
| bip01_l_hand | Bip01 L Hand | arm | left | 左手(含腕) |
| bip01_r_clavicle | Bip01 R Clavicle | arm | right | 右锁骨/肩 |
| bip01_r_upperarm | Bip01 R UpperArm | arm | right | 右上臂 |
| bip01_r_forearm | Bip01 R Forearm | arm | right | 右前臂(含肘区) |
| bip01_r_hand | Bip01 R Hand | arm | right | 右手(含腕) |
| bip01_l_thigh | Bip01 L Thigh | leg | left | 左大腿 |
| bip01_l_calf | Bip01 L Calf | leg | left | 左小腿(含膝) |
| bip01_l_foot | Bip01 L Foot | leg | left | 左脚/踝 |
| bip01_l_toe0 | Bip01 L Toe0 | leg | left | 左脚趾 |
| bip01_r_thigh | Bip01 R Thigh | leg | right | 右大腿 |
| bip01_r_calf | Bip01 R Calf | leg | right | 右小腿(含膝) |
| bip01_r_foot | Bip01 R Foot | leg | right | 右脚/踝 |
| bip01_r_toe0 | Bip01 R Toe0 | leg | right | 右脚趾 |
| bip01_l_finger0 | Bip01 L Finger0 | finger | left | 左拇指近节 |
| bip01_l_finger01 | Bip01 L Finger01 | finger | left | 左拇指中节 |
| bip01_l_finger02 | Bip01 L Finger02 | finger | left | 左拇指远节 |
| bip01_l_finger1 | Bip01 L Finger1 | finger | left | 左食指近节 |
| bip01_l_finger11 | Bip01 L Finger11 | finger | left | 左食指中节 |
| bip01_l_finger12 | Bip01 L Finger12 | finger | left | 左食指远节 |
| bip01_l_finger2 | Bip01 L Finger2 | finger | left | 左中指近节 |
| bip01_l_finger21 | Bip01 L Finger21 | finger | left | 左中指中节 |
| bip01_l_finger22 | Bip01 L Finger22 | finger | left | 左中指远节 |
| bip01_l_finger3 | Bip01 L Finger3 | finger | left | 左无名指近节 |
| bip01_l_finger31 | Bip01 L Finger31 | finger | left | 左无名指中节 |
| bip01_l_finger32 | Bip01 L Finger32 | finger | left | 左无名指远节 |
| bip01_l_finger4 | Bip01 L Finger4 | finger | left | 左小指近节 |
| bip01_l_finger41 | Bip01 L Finger41 | finger | left | 左小指中节 |
| bip01_l_finger42 | Bip01 L Finger42 | finger | left | 左小指远节 |
| bip01_r_finger0..42 | (右指 0~42) | finger | right | 右侧各指各节(同左指语义,侧为右) |

> 手指条目段号约定(绝对，目标侧)：`FingerN`=近节(0)、`FingerN1`=中节(1)、`FingerN2`=远节(2)，N=指型(0拇指/1食/2中/3无名/4小)。

## 附录 B：噪声词剔除清单(token 化时移除，不参与语义判定)

`bip01`、`bip001`、`mixamorig`、`def`、`b005`、`l`、`r`、`left`、`right`、`lt`、`rt`、空串

## 附录 C：已知歧义点(预判，代理判 FLAG 即可，不强求解决)

1. **`chest` 归属**：当前挂在 `bip01_spine1`(中段)，但部分骨架 chest=上段(`spine2`)。跨骨架歧义，审计时若见到 `chest` 在 spine1 → `FLAG`，附注"跨骨架歧义，待人工决策"。
2. **`hips`/`root` 归属**：`root` 别名在 pelvis 条目合理(骨盆常作根)，但若源骨架有独立根骨 `Bip001`，`root` 会让根骨误解析进 pelvis。审计时 `root` 在 pelvis → `FLAG`。
3. **`jaw` 在 head**：合法(head 含颌)，KEEP。
4. **`collar`/`collarbone`/`shoulder` 在 clavicle**：合法同义，KEEP。
