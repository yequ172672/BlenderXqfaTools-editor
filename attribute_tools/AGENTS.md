<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# attribute_tools

## Purpose
提供网格对象顶点属性的批量管理工具，包括顶点组、Shape Key、UV 贴图、顶点颜色（Color Attribute）的增删改查，以及视口覆盖绘制和顶点 ID 复制功能。所有工具在 3D 视口 N-panel 的 XQFA 标签下以子面板形式呈现。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册五个子模块 |
| `vertex_groups.py` | 顶点组管理：统计、删除空组、基于位置的匹配重命名、排序匹配 |
| `shapekey.py` | Shape Key 管理：匹配重命名、排序、按序重命名、选择受影响顶点、传递 |
| `uv.py` | UV 贴图管理：批量添加/重命名（TEXCOORD 命名）、设置 active/render、删除 |
| `vertex_colors.py` | 顶点颜色管理：设置 active/render、添加/重命名（COLOR 命名）、类型转换、调色板系统 |
| `extra_object_info.py` | 视口覆盖：绘制顶点组/Shape Key 统计、顶点/Loop ID，复制选中顶点 ID |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- 所有面板使用 `bl_space_type = 'VIEW_3D'` + `bl_region_type = 'UI'`，位于 XQFA 标签下
- `extra_object_info.py` 同时注册了视口覆盖（`draw_handler_add`）和 UV 编辑器覆盖
- `vertex_colors.py` 使用 `PaletteColorItem` PropertyGroup 和 `CollectionProperty` 实现调色板
- `vertex_groups.py` 的匹配重命名使用 NumPy 的相似度矩阵进行贪心匹配

### Testing Requirements
- 需要一个带有顶点组、Shape Key、UV 层和顶点颜色的网格对象
- 视口覆盖需在 3D 视口和 UV 编辑器中分别验证
- Shape Key 传递操作需要源和目标对象的顶点数完全一致

### Common Patterns
- 所有批量操作通过 `context.selected_objects` 遍历选中对象
- 属性索引使用 `Scene.*_target_index` 属性控制
- 面板仅在 `active_xbone_subpanel == 'AttributeTools'` 时显示
- 顶点数据操作使用 `foreach_get`/`foreach_set` 提高性能

## Dependencies

### Internal
- 依赖根 `panel.py` 注册的 `Scene.active_xbone_subpanel` 枚举属性控制面板显示
- 其他模块通过 `xqfa.shape_keys_match_rename` 等 bl_idname 调用此处的 operator

### External
- NumPy — 用于顶点组匹配和 Shape Key 比较的高效矩阵运算

<!-- MANUAL: -->
