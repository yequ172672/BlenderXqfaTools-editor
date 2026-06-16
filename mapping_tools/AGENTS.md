<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# mapping_tools

## Purpose
提供骨骼映射工作流和 UE 动画蓝图（ABP）约束节点生成工具。`modtoolkit` 模块实现了完整的顶点组重命名映射工作流，包括自动骨骼匹配、预设学习系统和 CSV 导出。`abp_generator` 模块根据映射列表自动生成 UE4/UE5 AnimGraphNode_Constraint 文本。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册 modtoolkit 和 abp_generator 子模块 |
| `modtoolkit.py` | 核心映射模块（~1530 行）：顶点组分配工作流、映射列表管理、自动骨骼匹配、预设系统、CSV 导出、杂项工具 |
| `abp_generator.py` | UE ABP 生成器（~452 行）：根据映射列表生成 UE4/UE5 AnimGraphNode_Constraint 节点文本 |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- `modtoolkit.py` 是最大的模块，包含完整的映射工作流（StartAssign → Next/Skip → Done）和自动匹配算法
- 自动骨骼匹配使用多因素评分：名称 Jaccard 相似度、层级路径相似度、空间位置相似度、预设历史匹配
- 预设存储在 `scripts/presets/yuinomodtools/` 目录下，使用 Blender 的 `AddPresetBase` 机制
- `abp_generator.py` 支持 UE4（4.26）和 UE5（5.3）两种节点格式，通过版本选择器切换
- 映射列表 `xbone_csv_data` 是共享数据，被 `bone_tools/mod_armature_replace.py` 和 `abp_generator.py` 同时使用
- 完整的中英双语本地化支持

### Testing Requirements
- 需要两个骨架对象（源和目标）测试自动匹配功能
- 映射列表需要通过分配工作流或手动添加测试数据
- ABP 生成需要有效的映射列表和资产路径
- 预设系统需要可写入的 `scripts/presets/` 目录

### Common Patterns
- 面板 `MyAddonPanel` 和 `ABPGeneratorPanel` 仅在 `active_xbone_subpanel == 'MappingTools'` 时显示
- 映射列表使用 `CollectionProperty` + `UIList` 实现
- 自动匹配结果存储在 `ListItem.vg` 和 `ListItem.bone` 属性中
- ABP 节点生成使用 GUID 唯一标识每个节点和引脚连接

## Dependencies

### Internal
- `abp_generator.py` 读取 `modtoolkit.py` 创建的映射列表（`xbone_csv_data`）
- `bone_tools/mod_armature_replace.py` 可读取此处导出的 CSV 数据
- 依赖根 `panel.py` 的子面板切换机制

### External
- 无额外第三方依赖，纯 Blender `bpy` API 实现
- ABP 生成的文本需要粘贴到 Unreal Engine 的 Animation Blueprint 编辑器中

<!-- MANUAL: -->
