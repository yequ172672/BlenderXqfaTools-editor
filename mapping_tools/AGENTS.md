<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-17 -->

# mapping_tools

## Purpose
提供骨骼映射工作流和 UE 动画蓝图（ABP）约束节点生成工具。`modtoolkit` 模块实现了完整的顶点组重命名映射工作流，包括自动骨骼匹配（相似度/数据库双模式）、预设学习系统和 CSV 导出。`bone_database` 模块提供规范骨骼数据库，支持默认模板 + 用户别名覆盖。`abp_generator` 模块根据映射列表自动生成 UE4/UE5 AnimGraphNode_Constraint 文本。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册 modtoolkit 和 abp_generator 子模块 |
| `modtoolkit.py` | 核心映射模块（~1820 行）：顶点组分配工作流、映射列表管理、自动骨骼匹配（双模式）、预设系统、CSV 导出、数据库管理 UI、杂项工具 |
| `bone_database.py` | 规范骨骼数据库（~180 行）：BoneDatabase 类，加载默认模板 + 用户覆盖层，精确/模糊解析，别名持久化 |
| `abp_generator.py` | UE ABP 生成器（~452 行）：根据映射列表生成 UE4/UE5 AnimGraphNode_Constraint 节点文本 |
| `dev_seed_canon.py` | 开发用种子脚本：从本地预设读取映射对，填充 bone_canon_default.json 的别名 |
| `data/bone_canon_default.json` | 默认骨骼模板（52 条 Bip01 规范骨骼，含别名列表） |

## Subdirectories

| Directory | Description |
|-----------|-------------|
| `data/` | 存放骨骼数据库 JSON 模板文件 |
| `tests/` | 单元测试（需在 Blender 内运行） |
| `backup/` | 设计文档备份 |

## For AI Agents

### Working In This Directory
- `modtoolkit.py` 是最大的模块，包含完整的映射工作流（StartAssign → Next/Skip → Done）和自动匹配算法
- 自动骨骼匹配支持两种算法模式：`SIMILARITY`（多因素评分）和 `CANON`（规范数据库匹配），通过 `xbone_automap_mode` 属性切换
- `bone_database.py` 提供规范骨骼数据库，使用延迟导入避免循环依赖（`from .bone_database import BoneDatabase`）
- 数据库支持精确匹配（别名索引 O(1)）和模糊匹配（name_score 阈值），用户修正自动持久化到 `bone_canon_user.json`
- 预设存储在 `scripts/presets/yuinomodtools/` 目录下，使用 Blender 的 `AddPresetBase` 机制
- `abp_generator.py` 支持 UE4（4.26）和 UE5（5.3）两种节点格式，通过版本选择器切换
- 映射列表 `xbone_csv_data` 是共享数据，被 `bone_tools/mod_armature_replace.py` 和 `abp_generator.py` 同时使用
- 完整的中英双语本地化支持

### Testing Requirements
- 需要两个骨架对象（源和目标）测试自动匹配功能
- 映射列表需要通过分配工作流或手动添加测试数据
- ABP 生成需要有效的映射列表和资产路径
- 预设系统需要可写入的 `scripts/presets/` 目录
- 骨骼数据库测试需在 Blender 内运行 `tests/test_bone_database.py`

### Common Patterns
- 面板 `MyAddonPanel` 和 `ABPGeneratorPanel` 仅在 `active_xbone_subpanel == 'MappingTools'` 时显示
- 映射列表使用 `CollectionProperty` + `UIList` 实现
- 自动匹配结果存储在 `ListItem.vg` 和 `ListItem.bone` 属性中
- `ListItem.bone` 有 `update=_on_list_bone_updated` 回调，CANON 模式下自动学习用户修正
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
