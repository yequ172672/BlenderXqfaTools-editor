<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# general_tools

## Purpose
提供通用的 3D 模型整理和材质管理工具集，包括无材质对象删除、按材质重命名、重复几何体清理、材质节点设置、八面体 UV 计算（实际在 other_tools）、姿态镜像等功能。这是一个综合性的工具集合，覆盖建模和绑定工作流中的常见操作。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册 y_tools 子模块 |
| `y_tools.py` | 核心模块，定义 16 个 operator 和 1 个 UI 面板，涵盖对象清理、材质管理、编辑模式工具、姿态镜像 |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- `y_tools.py` 是一个大型模块（约 500+ 行），包含所有功能。操作符按功能分组：对象清理、材质管理、编辑模式、姿态/骨架
- 使用 `Y_PoseMirrorSettings` PropertyGroup 存储姿态镜像配置（镜像方案、轴向、左右命名模式）
- 面板 `Y_PT_Panel` 仅在 `active_xbone_subpanel == 'GeneralTools'` 时显示
- `Y_OT_CleanDuplicatesAfterRename` 和 `Y_OT_DeleteIdenticalSelected` 通过比较顶点数、边数、面数和 UV 数据判断重复

### Testing Requirements
- 准备带有不同材质的多个网格对象测试清理和重命名功能
- `Y_OT_MirrorPose` 需要带有左/右命名骨骼的骨架对象测试镜像
- `Y_OT_MergeVerticesToTarget` 需要在编辑模式下测试

### Common Patterns
- 所有操作符使用 `object.*` 或 `mesh.*` / `pose.*` 作为 bl_idname 前缀
- 材质相关操作使用 `obj.data.materials` 直接操作材质槽
- 去重操作使用 `bpy.data.meshes` 进行几何数据比较

## Dependencies

### Internal
- 依赖根 `panel.py` 的子面板切换机制

### External
- 无额外第三方依赖，纯 Blender `bpy` API 实现

<!-- MANUAL: -->
