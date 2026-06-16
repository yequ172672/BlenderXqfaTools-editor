<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# other_tools

## Purpose
提供杂项建模和绑定辅助工具集，包含 13 个操作符，涵盖微型平面创建、组件重命名、Shape Key 应用、按材质分离、八面体 UV 计算、选择工具（按边数、按坐标）、三角面细分逆操作、递归选择子对象等。

## Key Files

| File | Description |
|------|-------------|
| `misc.py` | 核心模块（~1000 行）：所有 13 个操作符、辅助函数、UI 面板 |
| `texconv.exe` | Windows 纹理转换工具（被 material_tools 的烘焙功能使用） |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- `misc.py` 是一个综合性大文件，包含多个工作流的工具
- `XQFA_OT_NumberToBone` 是最复杂的操作符，涉及材质分配、网格合并、顶点组匹配、按材质分离、骨架修改器复制等多个步骤
- `XQFA_OT_OctahedralUV` 计算平滑法线并投影到八面体上存储为 UV（用于某些引擎的法线编码）
- `XQFA_OT_UndoTriSubdivide` 是三角面中点细分的逆操作，通过溶解特定边恢复四边面
- `texconv.exe` 实际被 `material_tools/bake_node_groups.py` 使用，放置在此目录是历史原因
- 面板 `XQFA_PT_Demo` 使用 `sk_source_mesh` PointerProperty 引用源网格

### Testing Requirements
- `XQFA_OT_MiniPlane` 需要选中网格对象测试微型平面创建
- `XQFA_OT_NumberToBone` 需要多个网格对象 + 骨架对象测试完整工作流
- `XQFA_OT_OctahedralUV` 需要带有 UV 贴图的网格对象
- 选择工具需要在编辑模式下测试

### Common Patterns
- 面板 `XQFA_PT_Demo` 仅在 `active_xbone_subpanel == 'OtherTools'` 时显示
- `XQFA_Utils` 提供 `is_mesh()` / `is_armature()` 静态辅助方法
- 选择工具使用 `bpy.context.tool_settings.mesh_select_mode` 检查选择模式
- 辅助函数 `unit_vector_to_octahedron()` 和 `calc_smooth_normals()` 为独立的数学工具函数

## Dependencies

### Internal
- 依赖根 `panel.py` 的子面板切换机制

### External
- 无额外第三方依赖，纯 Blender `bpy` API 实现

<!-- MANUAL: -->
