# 自动骨骼匹配算法优化方案

> 针对 `mapping_tools/modtoolkit.py` 中 `auto_match_bones()` 及相关函数的改进计划

---

## 1. 算法现状概览

### 1.1 评分公式

```
total = 0.30 × name_score + 0.15 × hierarchy_score + 0.10 × spatial_score + 0.45 × preset_bonus
```

| 维度 | 权重 | 函数 | 说明 |
|------|------|------|------|
| 名称相似度 | 0.30 | `name_score()` | Jaccard + 去侧前缀加成 |
| 层级相似度 | 0.15 | `hierarchy_score()` | 路径名称逐层加权 Jaccard + 深度差惩罚 |
| 空间相似度 | 0.10 | `spatial_score()` | 归一化坐标欧氏距离 + 镜像容差 |
| 预设加成 | 0.45 | `preset_bonus()` | 历史映射频率归一化 + 部分匹配间接加成 |

### 1.2 匹配流程

1. 过滤核心骨骼 (`is_core_bone`)
2. 对所有 `(src, tgt)` 对计算四维评分矩阵
3. 按总分降序排列
4. 贪心匹配：阈值 ≥ 0.25 且 src/tgt 均未占用时配对

### 1.3 设计哲学

- **预设驱动**：0.45 权重是有意为之——使用越多、系统越聪明
- **贪心匹配**：简单有效，避免复杂度爆炸
- **核心骨骼过滤**：排除物理/IK/辅助骨骼，聚焦主骨架

---

## 2. 优化项

### 优化 1：`_tokenize()` 增加 camelCase 和数字分词

**现状问题**

```python
def _tokenize(name: str) -> list:
    return [t for t in re.split(r"[_. \-]", name.lower()) if t]
```

只按 `_. -` 分隔符拆分，以下名称产生次优 token：

| 输入 | 当前结果 | 期望结果 |
|------|---------|---------|
| `LeftHand` | `["lefthand"]` | `["left", "hand"]` |
| `UpperArm2` | `["upperarm2"]` | `["upper", "arm", "2"]` |
| `HandL1` | `["handl1"]` | `["hand", "l", "1"]` |

**改进方案**

```python
def _tokenize(name: str) -> list:
    s = re.sub(r'([a-z])([A-Z])', r'\1_\2', name)  # camelCase split
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', s)  # acronym split
    s = re.sub(r'(\d+)', r'_\1_', s)  # isolate digits
    return [t for t in re.split(r"[_. \-]+", s.lower()) if t]
```

**影响范围**：`name_score()` > `_strip_side()` > 所有依赖 token 的评分

---

### 优化 2：`_strip_side()` 增加后缀式左右标识

**现状问题**

```python
_SIDE_PREFIXES = ["left_", "right_", "l_", "r_", "left", "right", "lt_", "rt_", "lt", "rt"]
```

只处理前缀式侧标识（`L_Hand`、`LeftHand`），不处理后缀式：

| 输入 | 当前结果 | 期望结果 |
|------|---------|---------|
| `Hand_L` | `hand_l` | `hand` |
| `ArmLeft` | `armleft` | `arm` |
| ` Shoulder_R ` | `shoulder_r` | `shoulder` |

**改进方案**

```python
_SIDE_PREFIXES = ["left_", "right_", "l_", "r_", "lt_", "rt_", "lt", "rt"]
_SIDE_SUFFIXES = ["_left", "_right", "_l", "_r", "_lt", "_rt", "left", "right", "lt", "rt"]

def _strip_side(name: str) -> str:
    lower = name.lower().strip("_")
    for prefix in _SIDE_PREFIXES:
        if lower.startswith(prefix) and len(lower) > len(prefix):
            return lower[len(prefix):]
    for suffix in _SIDE_SUFFIXES:
        if lower.endswith(suffix) and len(lower) > len(suffix):
            return lower[:len(lower) - len(suffix)]
    return lower
```

**注意**：需避免过度剥离（如 `R` → 空），加长度守卫。

---

### 优化 3：降低 `preset_bonus()` 部分匹配分数

**现状问题**

```python
# 部分匹配逻辑
if src_as_vg > 0 and tgt_as_bone > 0:
    return 0.25  # 两端都出现在预设中但未配对
if src_as_vg > 0 or tgt_as_bone > 0:  # 仅一端出现
    return 0.10
```

0.25 × 0.45 = 0.1125 贡献到总分，接近或超过部分名称匹配（0.30 × 0.5 = 0.15）。
仅一端出现的 0.10 × 0.45 = 0.045 也可能干扰排序。

**问题场景**：`src=Hand` 在预设中作为 vg 出现过 10 次，`tgt=Head` 从未出现过，
但 `Head` 凑巧在某个无关 bone 对中出现过 → 得到 0.045 间接加成，可能错误排在更匹配的对之前。

**改进方案**

```python
# 两端都出现在预设中（但未直接配对）
if src_as_vg > 0 and tgt_as_bone > 0:
    return 0.10  # 从 0.25 降至 0.10
# 仅一端出现 — 不给加成
return 0.0  # 从 0.10 降至 0.0
```

**理由**：部分匹配只能排除"完全不可能"，不应该积极推动匹配。真正的置信来源应该是直接预设匹配和名称/层级/空间证据。

---

### 优化 4：预设索引预构建——O(1) 部分匹配查询

**现状问题**

```python
src_as_vg = sum(v for (vg, _), v in preset_data.items() if vg == src_lower)
tgt_as_bone = sum(v for (_, b), v in preset_data.items() if b == tgt_lower)
```

对每个 `(src, tgt)` 对都线性扫描整个 `preset_data` 字典。
骨数 N × M 对 × K 个预设对 = O(NMK)。

**改进方案**

在 `load_preset_mappings()` 中预构建两个反向索引：

```python
# 在 load_preset_mappings() 末尾添加：
vg_index = {}    # {vg_name_lower: total_count}
bone_index = {}   # {bone_name_lower: total_count}
for (vg, bone), count in pair_counts.items():
    vg_index[vg] = vg_index.get(vg, 0) + count
    bone_index[bone] = bone_index.get(bone, 0) + count

# 存入缓存（改为返回三元组或使用模块级变量）
_preset_vg_index = vg_index
_preset_bone_index = bone_index
```

`preset_bonus()` 中改为：

```python
src_as_vg = _preset_vg_index.get(src_lower, 0)
tgt_as_bone = _preset_bone_index.get(tgt_lower, 0)
```

**性能影响**：部分匹配从 O(K) → O(1)。总复杂度从 O(NMK) → O(NM + K)。

---

### 优化 5：骨骼路径/位置缓存

**现状问题**

- `_get_bone_path()` 每次从骨骼向上遍历 parent 链，O(depth)
- `_get_bone_head_local()` 每次属性访问有微小开销
- 在 O(N×M) 的评分循环中重复计算同一骨骼的路径和位置

**改进方案**

```python
def auto_match_bones(src_armature_obj, tgt_armature_obj, threshold=0.25):
    src_bones = [b for b in src_armature_obj.data.bones if is_core_bone(b.name)]
    tgt_bones = [b for b in tgt_armature_obj.data.bones if is_core_bone(b.name)]

    # 预缓存
    src_paths = {b.name: _get_bone_path(b) for b in src_bones}
    tgt_paths = {b.name: _get_bone_path(b) for b in tgt_bones}
    src_positions = {b.name: _get_bone_head_local(b) for b in src_bones}
    tgt_positions = {b.name: _get_bone_head_local(b) for b in tgt_bones}

    # 评分时使用缓存值
    for sb in src_bones:
        for tb in tgt_bones:
            hs = hierarchy_score_fast(src_paths[sb.name], tgt_paths[tb.name])
            ss = spatial_score_fast(src_positions[sb.name], tgt_positions[tb.name], ...)
            ...
```

需要新增接受预计算参数的 `hierarchy_score_fast()` 和 `spatial_score_fast()` 变体，
原函数保留以兼容。

**性能影响**：每骨骼仅计算一次路径/位置，减少 N×M 次重复计算。

---

### 优化 6：鲁棒的预设配对解析

**现状问题**

```python
vg_matches = vg_pattern.findall(content)
bone_matches = bone_pattern.findall(content)
for vg_name, bone_name in zip(vg_matches, bone_matches):
    ...
```

`zip` 假设 vg 和 bone 按 1:1 顺序出现且一一对应。
如果预设文件格式有变动、注释干扰、或条目不完整（只有 vg 没有 bone），配对会错位。

**改进方案**

```python
def _parse_preset_file(filepath: str) -> list[tuple[str, str]]:
    """解析单个预设文件，返回可靠的 (vg, bone) 配对列表。"""
    pairs = []
    current_vg = None
    current_bone = None
    current_idx = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            # 提取 item_sub_N 索引
            idx_match = re.search(r'item_sub_(\d+)', line)
            # 提取 vg 值
            vg_match = re.search(r"\.vg\s*=\s*['\"]([^'\"]+)['\"]", line)
            bone_match = re.search(r"\.bone\s*=\s*['\"]([^'\"]+)['\"]", line)

            if idx_match:
                idx = int(idx_match.group(1))
                if current_vg is not None and current_bone is not None and current_idx is not None:
                    pairs.append((current_vg, current_bone))
                current_idx = idx
                current_vg = vg_match.group(1) if vg_match else None
                current_bone = bone_match.group(1) if bone_match else None
            elif vg_match and current_idx is not None:
                current_vg = vg_match.group(1)
            elif bone_match and current_idx is not None:
                current_bone = bone_match.group(1)

    # 最后一组
    if current_vg and current_bone:
        pairs.append((current_vg, current_bone))

    return pairs
```

使用 `item_sub_N` 索引作为配对锚点，确保 vg 和 bone 正确关联到同一列表项，即使格式有变化也不会错位。

---

## 3. 实施优先级

| 优先级 | 优化项 | 风险 | 预期收益 |
|--------|--------|------|---------|
| P0 | 优化 3：降低部分匹配分数 | 低 | 直接提升匹配准确性 |
| P0 | 优化 6：鲁棒预设解析 | 低 | 修复潜在错位 bug |
| P1 | 优化 1：camelCase 分词 | 中 | 显著改善混写骨名匹配 |
| P1 | 优化 2：后缀式侧标识 | 低 | 增加后缀格式覆盖率 |
| P2 | 优化 4：预设索引预构建 | 低 | 性能提升，大规模骨架必须 |
| P2 | 优化 5：骨骼路径/位置缓存 | 低 | 性能提升，非常规场景 |

---

## 4. 测试要点

- **回归测试**：每次优化后使用已有预设执行自动映射，比对结果的差异
- **新增用例**：
  - camelCase 骨名：`LeftHand`、`UpperArm2`、`Spine1`
  - 后缀式侧标识：`Hand_L`、`ArmRight`
  - 预设部分匹配：含仅 vg 或仅 bone 的预设文件
  - 大规模骨架（100+ 骨骼）性能基准
- **手动验证**：在 Blender 4.5+ 中加载两套骨架，检查匹配率和配对正确性