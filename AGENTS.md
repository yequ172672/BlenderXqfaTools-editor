<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# BlenderXqfaTools-editor

## Purpose
XqfaTools 是一个面向 Blender 4.5+ 的综合 3D 建模/绑定/材质工作流插件。提供骨骼编辑、顶点属性管理、材质烘焙与管理、骨骼映射与 ABP 生成、通用模型整理等工具集。作为上游 `XQFAAAA/BlenderXqfaTools` 的 fork，增加了自动骨骼映射、ABP 节点生成等扩展功能。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 插件入口，声明 `bl_info`，注册所有子模块和偏好设置（texconv.exe 路径） |
| `panel.py` | 主 UI 面板，在 3D 视口 N-panel 的 XQFA 标签下创建五个子面板切换按钮 |
| `README.md` | 项目文档，中文说明所有功能、安装方式和目录结构 |
| `git-fork-workflow.md` | Fork 工作流开发指南 |
| `.gitignore` | 忽略 `__pycache__/`、`.vscode/`、`.vibe-coding/` |

## Subdirectories

| Directory | Purpose |
|-----------|---------|
| `bone_tools/` | 骨骼编辑、姿态调整、骨骼与顶点组清理、CSV 驱动的骨架替换（see `bone_tools/AGENTS.md`） |
| `attribute_tools/` | 顶点组、Shape Key、UV、顶点颜色管理，视口覆盖绘制（see `attribute_tools/AGENTS.md`） |
| `other_tools/` | 杂项建模工具集，含八面体 UV、按材质分离、选择工具等（see `other_tools/AGENTS.md`） |
| `material_tools/` | 材质节点烘焙、批量重命名、快照、法线格式检测等节点编辑器工具（see `material_tools/AGENTS.md`） |
| `mapping_tools/` | 骨骼映射工作流、自动匹配、预设系统、ABP 节点生成器（see `mapping_tools/AGENTS.md`） |
| `general_tools/` | 通用模型整理工具，含材质清理、去重、姿态镜像等（see `general_tools/AGENTS.md`） |

## For AI Agents

### Working In This Directory
- 这是一个 Blender Python 插件项目，所有 UI 和逻辑都通过 `bpy` API 实现
- 入口文件是 `__init__.py`，每个子模块通过 `register()`/`unregister()` 模式注册
- UI 面板位于 3D 视口 N-panel 的 "XQFA" 标签下，通过 `panel.py` 中的枚举切换子面板
- 所有模块共享同一套 `bl_idname` 命名空间（`xqfa.*` 或 `object.*` 等），添加新 operator 时需确保不冲突

### Testing Requirements
- 在 Blender 4.5+ 中启用插件后，通过 N-panel 的 XQFA 标签访问各工具
- 修改骨骼工具后需在 Edit Armature / Pose Mode 下测试
- 修改材质工具后需在 Node Editor 中测试面板和操作
- 修改映射工具后需准备骨架和网格对象测试映射流程

### Common Patterns
- 每个工具模块包含一个 `__init__.py`（注册子模块）和若干功能 .py 文件
- UI Panel 类继承 `bpy.types.Panel`，通过 `bl_space_type = 'VIEW_3D'` + `bl_region_type = 'UI'` 显示在 N-panel
- 场景属性（`bpy.types.Scene.*`）用于跨 operator 传递状态
- 中英双语本地化通过 `bpy.app.translations` 实现
- Operator 的 `bl_idname` 使用 `xqfa.*` 或 `object.*` / `mesh.*` / `pose.*` 前缀

## Dependencies

### External
- Blender 4.5+ (`bpy` API)
- NumPy — 用于顶点组匹配、Shape Key 比较等高性能计算
- `texconv.exe` — Windows 纹理转换工具（用于 DDS/BCn 格式打包）

### Internal
- 各模块之间通过 `bl_idname` 字符串引用彼此的 operator（如 `xqfa.merge_to_parent`）
- `mapping_tools/modtoolkit.py` 的映射列表被 `bone_tools/mod_armature_replace.py` 和 `mapping_tools/abp_generator.py` 共享使用

<!-- MANUAL: -->
