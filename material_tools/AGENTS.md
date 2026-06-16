<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-06-16 | Updated: 2026-06-16 -->

# material_tools

## Purpose
提供材质节点编辑器相关的工具集，包括节点组批量烘焙（含通道打包和 DDS 转换）、材质批量重命名、材质快照（保存/恢复节点连接）、法线贴图格式检测等。所有工具在 Node Editor 侧边栏的 XQFA 标签下显示。

## Key Files

| File | Description |
|------|-------------|
| `__init__.py` | 包初始化，注册四个子模块 |
| `bake_node_groups.py` | 节点组批量烘焙（~562 行）：选择输出端口 → 逐个烘焙 → RGBA 通道打包 → DDS 转换 |
| `material.py` | 材质工具（~274 行）：法线格式检测（Sobel 算子）、添加打包图像、PBR 材质创建、批量创建材质 |
| `material_batch_rename.py` | 材质批量重命名（~340 行）：可选材质列表、查找替换、前缀后缀、自动同步依赖图 |
| `material_snapshot.py` | 材质快照（~261 行）：保存/恢复节点连接状态和节点 mute 状态 |

## Subdirectories

无子目录。

## For AI Agents

### Working In This Directory
- `bake_node_groups.py` 的核心是 `M_OT_BatchBakeModal` modal operator，它逐个烘焙输出端口并自动重连线
- 通道打包系统使用 `ChannelConfig` 和 `PackImageItem` PropertyGroup 定义 RGBA 通道映射
- DDS 转换通过调用外部 `texconv.exe` 实现（路径在插件偏好设置中配置）
- `material_batch_rename.py` 使用 depsgraph handler 自动同步材质列表（`_on_depsgraph_update`）
- `material_snapshot.py` 通过存储节点名称和 socket 名称/索引来序列化连接状态
- `material.py` 的法线检测使用 Sobel 算子分析图像数据，判断 OpenGL/DirectX 格式

### Testing Requirements
- 节点组烘焙需要带有多个输出端口的节点组
- 法线检测需要法线贴图图像节点
- 材质重命名需要带有多个材质槽的对象
- 材质快照需要带有复杂节点连接的材质

### Common Patterns
- 所有面板位于 Node Editor 侧边栏（`bl_space_type = 'NODE_EDITOR'`）
- Modal operator 使用 `context.window_manager.modal_handler_add(self)` 和 `timer` 驱动
- 属性组通过 `Scene.batch_bake_props` / `Scene.material_batch_rename_props` 等挂载
- 图像保存使用 `image.pack()` / `image.filepath_raw` 和 `bpy.ops.image.save_as()`

## Dependencies

### Internal
- `bake_node_groups.py` 依赖 `material.py` 中的一些辅助函数
- 依赖根 `panel.py` 的子面板切换机制

### External
- `texconv.exe` — Windows 纹理转换工具，用于 DDS/BCn 格式打包（路径在插件偏好设置中配置）

<!-- MANUAL: -->
