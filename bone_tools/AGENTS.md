<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# bone_tools

## Purpose
提供骨骼绑定工作流的全套工具，覆盖 Edit Armature 模式（编辑骨骼）、Pose Mode（姿态调整）、骨骼与顶点组关系管理、以及 CSV 驱动的骨架替换。面板按编辑模式自动切换显示内容。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册四个子模块 |
| `bone_and_vertex_groups.py` | 骨骼与顶点组关系管理：清理无关联项、编号前缀、骨骼/顶点组合并 |
| `bone_edit.py` | 编辑模式骨骼工具：旋转对齐（Y-up/Z-up/正交化）、连接/断开、尾部对齐、Roll 校正、矩阵显示 |
| `bone_pose.py` | 姿态模式工具：旋转对齐、应用姿态/交换 Rest、CSV 选择骨骼、移动/旋转/缩放到活动骨骼、约束管理、矩阵显示 |
| `mod_armature_replace.py` | CSV 驱动骨架替换：导入 CSV、骨骼简化映射、位置复制映射、重命名重绑定映射、批量重命名 |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- `bone_edit.py` 和 `bone_pose.py` 各自定义了 `PG_BoneEditWorldProps` / `PG_BonePoseWorldProps` PropertyGroup，用于矩阵显示和轴约束
- `bone_and_vertex_groups.py` 和 `mod_armature_replace.py` 各自定义了 `ObjType` 辅助类（功能相同但独立）
- CSV 相关功能使用 `scene.xbone_csv_data` JSON 字符串属性传递数据
- `mod_armature_replace.py` 大量调用 `bone_and_vertex_groups.py` 和 `bone_pose.py` 中的 operator（通过 `bpy.ops.xqfa.*`）

### Testing Requirements
- Edit Armature 模式下测试 `bone_edit.py` 的旋转、连接、尾部对齐
- Pose Mode 下测试 `bone_pose.py` 的旋转、应用姿态、约束管理
- 准备至少两个骨架对象测试 `mod_armature_replace.py` 的替换流程
- CSV 测试需准备 UTF-8/GBK 编码的映射表文件

### Common Patterns
- 面板根据 `context.mode` 自动显示 Edit Armature 或 Pose 模式的内容
- 矩阵显示使用 `bpy.types.SpaceView3D.draw_handler_add` 注册覆盖绘制
- 骨骼操作常通过 `context.selected_pose_bones` 或 `context.selected_bones` 获取目标
- 属性组通过 `Scene.bone_edit_world_props` / `Scene.bone_pose_world_props` 挂载

## Dependencies

### Internal
- `mod_armature_replace.py` 调用 `bone_and_vertex_groups.py` 的合并 operator 和 `bone_pose.py` 的姿态应用 operator
- 依赖根 `panel.py` 的子面板切换机制

### External
- 无额外第三方依赖，纯 Blender `bpy` API 实现

<!-- MANUAL: -->
