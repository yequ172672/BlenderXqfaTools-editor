# 骨骼标准数据库自动映射方案

> Canonical Bone Database Design for `mapping_tools` Auto Mapping
>
> **当前有效设计文档** — 替代此前所有映射算法/数据库相关方案文档。

---

## 1. 概述

当前 `auto_match_bones()` 完全依赖名称/层级/空间相似度和预设历史配对。当骨架命名风格差异较大时，匹配结果不稳定。本方案引入一个**固定的标准骨骼数据库**（以 3ds Max Bip01 人体基础骨架为模板），将骨骼按功能分类，每个标准骨骼维护一组别名。自动映射时优先查询数据库，实现更语义化、可学习的匹配。

数据库由两部分组成：

- **默认模板**（`bone_canon_default.json`）：随插件分发，包含 52 个核心骨骼及其常见别名
- **用户层**（`bone_canon_user.json`）：首次运行时生成，记录用户修正和从预设自动派生的新别名

---

## 2. 目标

1. 提供稳定的 52 根核心骨骼功能分类参考
2. 支持两种自动映射算法切换：
   - **智能相似度模式**：现有算法（`name_score + hierarchy_score + spatial_score + preset_bonus`）
   - **数据库匹配模式**：基于标准数据库的功能分类匹配
3. 从用户已有预设自动派生别名，减少手动维护
4. 用户在自动映射出错后手动修正，自动将修正结果吸收进用户层数据库
5. 保持向后兼容，不破坏现有预设和映射列表工作流

---

## 3. 数据模型

### 3.1 文件结构

```
BlenderXqfaTools-editor/
├── mapping_tools/
│   ├── data/
│   │   └── bone_canon_default.json      # 内置默认模板（只读）
│   ├── bone_database.py                  # 数据库加载、查询、写入逻辑
│   ├── modtoolkit.py                     # 现有映射模块（新增算法分支）
│   └── ...
```

用户目录（首次运行时创建）：

```
%USERPROFILE%\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\presets\yuinomodtools\
├── bone_canon_user.json                  # 用户层别名数据
```

### 3.2 JSON Schema

```json
{
  "version": "1.0",
  "schema": "bone_canon",
  "bones": [
    {
      "id": "bip01_head",
      "canonical_name": "Bip01 Head",
      "display_name": "头部",
      "category": "head_neck",
      "side": "center",
      "description": "头部末端骨骼",
      "aliases": [
        "head", "Head", "bip01-head", "bip001-head",
        "mixamorig:head", "def-head", "head_x"
      ]
    },
    {
      "id": "bip01_l_upperarm",
      "canonical_name": "Bip01 L UpperArm",
      "display_name": "左上臂",
      "category": "arm",
      "side": "left",
      "aliases": [
        "upperarm_l", "l_upperarm", "leftupperarm",
        "bip01-l-upperarm", "mixamorig:leftarm"
      ]
    }
  ]
}
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | str | 唯一标识符，不可变 |
| `canonical_name` | str | 标准名称，如 Bip01 命名 |
| `display_name` | str | UI 显示中文名 |
| `category` | str | 分类：`head_neck` / `torso` / `arm` / `leg` / `finger` |
| `side` | str | `left` / `right` / `center` |
| `description` | str | 可选说明 |
| `aliases` | list[str] | 该骨骼可能对应的所有名称，大小写不敏感 |

### 3.3 52 骨分类规划

| 分类 | 数量 | 代表骨骼 |
|------|------|---------|
| 头部与脖子 | 2 | Head, Neck |
| 躯干 | 4 | Pelvis, Spine, Spine1/Chest, Spine2/UpperChest |
| 手臂（左右各 8） | 16 | Clavicle, UpperArm, LowerArm, Hand, Thumb1-3, Index1-3, Middle1-3, Ring1-3, Pinky1-3 等 |
| 腿部（左右各 8） | 16 | Thigh, Calf, Foot, Toe, 脚趾细分等 |
| 手指（左右各 15） | 30 | Thumb/Index/Middle/Ring/Pinky 各 3 节 |

> 注：每个骨骼条目左右独立，不按侧标识合并。

---

## 4. 算法设计

### 4.1 核心思想

先判断**源骨骼名属于哪个标准骨骼**，再判断**目标骨骼名属于哪个标准骨骼**。如果两者命中同一 `id`，则视为功能匹配。

### 4.2 名称到标准骨骼的解析

```python
def resolve_canonical_bone(bone_name: str, db: BoneDatabase) -> Optional[BoneEntry]:
    """
    将任意骨骼名解析到标准骨骼条目。
    匹配规则：与 aliases 中的每个别名计算 name_score，取最高分。
    """
    best_entry = None
    best_score = ALIAS_MATCH_THRESHOLD  # 如 0.6

    for entry in db.entries:
        for alias in entry.aliases:
            score = name_score(bone_name, alias)
            if score > best_score:
                best_score = score
                best_entry = entry

    return best_entry
```

### 4.3 匹配流程

```python
def auto_match_canonical(src_bones, tgt_bones, db, threshold=0.6):
    matched = []
    unmatched_src = []

    for sb in src_bones:
        src_entry = resolve_canonical_bone(sb.name, db)
        if src_entry is None:
            unmatched_src.append(sb.name)
            continue

        best_score = 0.0
        best_tgt = None

        for tb in tgt_bones:
            if tb.name in matched_tgt_names:
                continue
            tgt_entry = resolve_canonical_bone(tb.name, db)
            if tgt_entry is None:
                continue

            if tgt_entry.id == src_entry.id:
                score = _canonical_match_score(sb, tb, src_entry, db)
                if score > best_score:
                    best_score = score
                    best_tgt = tb

        if best_tgt and best_score >= threshold:
            matched.append((sb.name, best_tgt.name, best_score))
            matched_tgt_names.add(best_tgt.name)
        else:
            unmatched_src.append(sb.name)

    return matched, unmatched_src
```

### 4.4 评分权重

当源和目标命中同一 canonical entry 时，计算最终匹配分：

| 维度 | 权重 | 说明 |
|------|------|------|
| 别名置信度 | 0.40 | 骨骼名与匹配别名之间的 `name_score` |
| 侧一致性 | 0.25 | 源/目标解析出的 side 是否一致 |
| 层级相似度 | 0.20 | 路径深度和父骨骼是否对应同一 canonical 层级 |
| 空间相似度 | 0.15 | 归一化坐标距离 + 镜像容差 |

总分范围 `[0, 1]`，建议默认阈值 `0.60`。

### 4.5 未命中数据库时的回退

如果源骨骼或目标骨骼无法解析到任何 canonical entry，则该配对跳过数据库模式，标记为未匹配。这部分骨骼需要用户手动修正，修正后自动补充进用户层数据库。

---

## 5. 自动学习机制

### 5.1 触发时机

用户使用数据库模式执行自动映射后，在映射列表中手动修改某一行：

- 源骨骼名 `src_name`
- 修正后的目标骨骼名 `tgt_name`
- 当前期望的 canonical entry（由 `src_name` 解析得到）

### 5.2 学习规则

```python
def learn_from_correction(src_name: str, tgt_name: str, db: BoneDatabase):
    expected_entry = resolve_canonical_bone(src_name, db)
    if expected_entry is None:
        return

    # 1. 已存在该别名，无需学习
    if db.has_alias(expected_entry.id, tgt_name):
        return

    # 2. 检查是否与其他 entry 冲突
    conflict = db.find_entry_by_alias(tgt_name)
    if conflict and conflict.id != expected_entry.id:
        # 冲突场景：记录但不强制覆盖，避免污染
        db.add_alias(
            expected_entry.id,
            tgt_name,
            source="correction",
            conflict_with=conflict.id
        )
        return

    # 3. 无冲突，直接加入用户层
    db.add_alias(expected_entry.id, tgt_name, source="correction")
    db.save_user_data()
```

### 5.3 从现有预设派生别名

首次生成用户数据库时，批量扫描 `scripts/presets/yuinomodtools/` 中的 `.py` 预设文件：

1. 对每个预设中的 `(vg_name, bone_name)` 配对
2. 使用默认模板尝试解析 `vg_name` → canonical entry
3. 如果命中，将 `bone_name` 作为该 entry 的别名加入用户层
4. 如果未命中，跳过（等待用户后续手动修正时学习）

该过程只执行一次，后续新增预设通过 `_invalidate_preset_cache()` 触发重建。

### 5.4 来源标记

每个别名可记录来源，便于追溯和回退：

- `source: "default"`：来自内置模板
- `source: "preset"`：从用户预设自动派生
- `source: "correction"`：用户手动修正

---

## 6. UI 变更

### 6.1 自动映射区域

在现有"自动映射"按钮旁新增算法下拉框：

```
算法: [数据库匹配 ▼]  [▶ 自动映射]
       智能相似度
```

新增 Scene 属性：

```python
Scene.xbone_automap_mode = EnumProperty(
    name="自动映射算法",
    description="选择自动骨骼匹配算法",
    items=[
        ('SIMILARITY', "智能相似度", "基于名称、层级、空间和预设历史的综合评分"),
        ('CANON', "数据库匹配", "基于标准骨骼数据库的功能分类匹配"),
    ],
    default='SIMILARITY'
)
```

### 6.2 数据库管理折叠面板

- **从预设生成别名**：扫描现有预设，填充用户层数据库
- **导出数据库**：备份 `bone_canon_user.json`
- **重置用户层**：清空用户修正，恢复默认模板
- **查看条目**：列出 52 个 canonical bone，点击展开别名

### 6.3 结果反馈

数据库模式下，匹配结果附加分类标签：

```
Head → head  [头部/中心] score=0.92
Neck → neck  [颈部/中心] score=0.88
```

未匹配骨骼按 `category` 分组显示，方便批量修正。

---

## 7. 迁移与兼容性

- 默认算法保持为 **智能相似度模式**，旧用户无感知
- 数据库模式为显式切换，不影响现有预设和映射列表
- 首次启用插件时自动复制默认模板到用户目录
- 插件更新时只覆盖 `bone_canon_default.json`，`bone_canon_user.json` 保留
- `xbone_csv_data` 和 `xbone_list` 数据结构不变

---

## 8. 实现边界与风险

| 风险 | 应对 |
|------|------|
| 用户修正错误污染数据库 | 来源标记 + 可一键重置用户层；冲突时记录但不覆盖 |
| 别名被多个 entry 争夺 | 按 `name_score` 取最高，或提示用户选择 |
| 52 条无法覆盖特殊骨架 | 允许未来扩展条目；暂时未命中的骨骼走手动修正 + 学习 |
| 首次生成时预设数据不足 | 依赖内置默认模板的覆盖度 |

---

## 9. 实现计划

### 9.1 开发阶段：用本地预设填充默认模板

在实现功能代码之前，需要先用开发者本地已有的预设数据生成 `bone_canon_default.json` 的初始内容。

**数据源**：

```
C:\Users\yequ\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\presets\yuinomodtools
```

**步骤**：

1. 扫描上述目录下所有 `.py` 预设文件，提取 `(vg_name, bone_name)` 配对
2. 以 Bip01 人体基础骨架为参考，将 52 个核心骨骼作为 canonical entry 骨架
3. 对每个 canonical entry，收集所有映射到该功能骨骼的 `vg_name` 和 `bone_name` 作为别名
4. 按出现频率排序/去重，生成 `bone_canon_default.json`
5. 人工复核 52 个条目，补充缺失的通用别名（如 Mixamo、UE、Unity 等命名风格）

**说明**：

- 此步骤为一次性开发工作，生成的 `bone_canon_default.json` 随插件代码提交
- 用户安装插件后，该文件作为内置默认模板，不再依赖开发者本地预设路径
- 如果后续本地预设有更新，可重新运行该工具覆盖默认模板

### 9.2 功能实现顺序

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 0 | **开发阶段：用本地预设生成 `bone_canon_default.json`** | 新增一次性脚本 + `mapping_tools/data/bone_canon_default.json` |
| 1 | 创建 `mapping_tools/data/bone_canon_default.json` 默认模板 | 新增 |
| 2 | 实现 `bone_database.py`：加载、合并默认+用户、查询、写入 | 新增 |
| 3 | 注册 `Scene.xbone_automap_mode` 和 UI 下拉框 | `panel.py`, `modtoolkit.py` |
| 4 | 实现数据库匹配算法 `auto_match_canonical()` | `modtoolkit.py` |
| 5 | 修改 `auto_match_bones()` 根据算法分支 | `modtoolkit.py` |
| 6 | 实现从预设派生别名和用户修正学习 | `bone_database.py`, `modtoolkit.py` |
| 7 | 添加数据库管理 UI | `modtoolkit.py` |
| 8 | 测试：新旧算法对比、学习机制、兼容性 | — |

---

## 10. 测试策略

1. **解析正确性**：常见命名风格（Bip01、Mixamo、UE、Unity、自定义）能否正确解析到 canonical entry
2. **匹配质量**：同一对骨架在数据库模式和相似度模式下的结果对比
3. **学习机制**：手动修正后检查 `bone_canon_user.json` 是否正确追加别名
4. **预设派生**：首次生成时检查现有预设是否被正确吸收
5. **兼容性**：选择相似度模式时输出与修改前一致
6. **升级场景**：插件更新后用户层数据是否保留

---

## 11. 相关文档

- `mapping_tools/BONE_CANON_DATABASE_DESIGN.md`：本文档，当前唯一有效的映射数据库设计方案

> 注：此前相关方案文档已整理归档。本文档采用**固定标准模板 + 用户层别名**的双层结构。