# 自动骨骼映射（auto map）算法优化方案

> 状态：`pending approval`（共识评审 REVISE → 已合并 Architect/Critic 全部反馈，待 Critic 复审）
> 范围：`mapping_tools/modtoolkit.py` + `mapping_tools/bone_database.py`
> 分支：`feature/skeleton-mapping-compat`
> 编写日期：2026-06-17
> 评审：Planner（RALPLAN-DR）→ Architect（架构评审）→ Critic（REVISE）→ 本修订版

---

## 〇、Architect 修订裁定（强制，优先级高于正文任何冲突处）

以下 5 处修订为执行契约的强制组成部分。正文若与裁定冲突，以本节为准。

| # | 修订 | 强制级别 | 落点 |
|---|------|---------|------|
| 1 | P1-A 的 `sizes` 必须用 `tuple(maxs[i]-mins[i] for i in range(3))`，**不得用生成器表达式**——`bbox[2][i]` 下标对生成器会抛 `TypeError: 'generator' object is not subscriptable`，导致 `spatial_score`（`modtoolkit.py:416`）与 `_cached_spatial_score_positions`（`modtoolkit.py:576`）运行时崩溃 | **CRITICAL** | P1-A |
| 2 | P1-B 直接用 `functools.lru_cache(maxsize=8192)` 包裹 `_tokenize` 与 `name_score`，**取代手写 dict**。`name_score(a,b)` 对称（Jaccard `modtoolkit.py:327-329` + side_bonus `modtoolkit.py:332-345` 均对称），lru_cache 的 C 级实现开销远低于 regex `_tokenize` 的两次 `re.sub`（`modtoolkit.py:315-316`） | 采纳 | P1-B |
| 3 | P2-B 短路条件用常量命名：`RENORM_NAME_WEIGHT = 0.30/0.55`，短路判断 `ns < threshold * RENORM_NAME_WEIGHT` | 采纳 | P2-B |
| 4 | P1-C 重归一化触发条件从 per-pair `pb == 0.0` 改为全局 `max_preset_count == 0`（`modtoolkit.py:632`）。区分 `preset_bonus` 返回 0.0 的两种语义：`modtoolkit.py:529` 真无历史（应触发）vs `modtoolkit.py:549` 单侧未知（不应触发——预设存在，0.45 权重槽保留为空作为"本对缺乏预设确认"的惩罚） | 采纳并扩展 | P1-C |
| 5 | 验收 #2 聚焦根因：bbox 单标量归一化 bug（`modtoolkit.py:404`）与 mirror 容差（`modtoolkit.py:580-586` 已独立处理）是两套机制，验收不得混淆 | 采纳 | 验收 #2 |

**实施顺序裁定**：以 Architect 合成路径（4 Phase）为权威执行顺序，原第六节顺序**作废**。P2-C 与其他项无依赖，置于 Phase 1（与 P1-B 同批纯缓存改动）；P2-B→P1-C 硬依赖（方案原 line 125 + P2-B 短路公式依赖重归一化基数）经源码确认真实，P2-B 必须在 P1-C 之后。

---

## 一、Principles（指导原则，5 条）

1. **接口契约不可变**：`auto_match_bones(src, tgt, threshold=0.25)` 签名与 `(matched_pairs, unmatched_src, unmatched_tgt)` 返回结构（`modtoolkit.py:614-623`、`modtoolkit.py:738`）不变；`ListItem.bone` 的 `_on_list_bone_updated` 学习回调（`modtoolkit.py:741-759`）行为不变。所有优化限制在内部评分层。
2. **零外部依赖**：不引入 scipy 等非 Blender 内置包；记忆化只用标准库 `functools.lru_cache`（P1-B）。
3. **准确率缺陷优先于性能、性能优先于召回补强**：先修确定性失真（P1-A bbox、P1-C 重归一化），再性能（P1-B），再召回（P2-A），最后工程化（P2-C）。例外：P1-B 因零行为变化可前置。
4. **分数语义一致性**：重归一化（P1-C）、短路剪枝（P2-B）、CANON 阈值松弛（P2-A）后，分数须仍 ∈ [0,1] 且与末端全局 `threshold=0.25`（`modtoolkit.py:614`、`modtoolkit.py:721`）可比；不得引入新的隐式阈值。**已知权衡**：P1-C 会使"无预设"路径的绝对分数从上限 0.55 升至 1.0，属可接受的有意漂移，须通过验收 #1 扩展的 score 直方图显式记录（见验收 #1、#8），不可隐式发生。
5. **增量可回退 + 回归门禁**：每 Phase 可独立 revert，≥8 预设样本（验收 #1）作为门禁，退化即止步。

## 二、Decision Drivers（top 3）

1. **准确率缺陷的根因确定性**：`_compute_bbox` 取 `size = max(三轴跨度)`（`modtoolkit.py:404`），`spatial_score` / `_cached_spatial_score_positions` 用单一标量 `bbox[2]` 归一化全部三轴（`modtoolkit.py:416-417`、`modtoolkit.py:576-577`）。人形骨架高度 ≫ 宽度/深度导致横向差异被稀释——确定性 bug。驱动 **P1-A 必须独立先行（Phase 2）**。
2. **行为变化风险梯度**：P1-B（纯缓存，零行为变化）< P1-A（分数值变化但语义不变）< P1-C / P2-A（分数分布与 matched_pairs 可能变）< P2-B（短路可能漏匹配）。驱动分批：零风险项聚合（Phase 1），行为变化项单步（Phase 2/3/4）。
3. **实现依赖耦合**：P2-B 短路条件 `ns < threshold·RENORM_NAME_WEIGHT` 依赖 P1-C 重归一化的 `0.30/0.55` 基数；P2-B 触发判断须与 P1-C 的 `max_preset_count==0` 同步（短路仅在重归一化激活路径生效）。驱动顺序约束：**P2-B 不得先于 P1-C**。

## 三、需求摘要

对 `auto_match_bones`（`modtoolkit.py:614`）双模式自动骨骼映射算法优化。SIMILARITY 分支（`modtoolkit.py:701-710`）全矩阵 `0.30·name+0.15·hier+0.10·spatial+0.45·preset`；CANON 分支（`modtoolkit.py:657-700`）按 canonical id 分组 `0.40·alias+0.25·side+0.20·hier+0.15·spatial`（**无 preset，P1-C 不触及 CANON 分支**）。末端贪心（`modtoolkit.py:713-728`），全局 `threshold=0.25`。

目标：提升匹配准确率、降低大骨架耗时、增强无历史预设场景召回。接口契约不变。

## 四、Viable Options 与否决依据

### 选项 A（6 步串行，原方案）
顺序 P1-A→P1-B→P1-C→P2-A→P2-B→P2-C。
- Pros：每步单一根因，回归二分清晰；回退粒度最细。
- Cons：6 次 Blender 重载测试周期，dev 周期长。

### 选项 B（3 批聚类，Planner 初版推荐）— **已否决**
- Pros：测试周期减半。
- Cons（否决依据，经源码核实）：(a) `P2-B→P1-C` 硬依赖使同批落地不可行，跨批退化为串行；(b) Blender 单线程 Python 无并行吞吐收益；(c) 批次边界非回退边界，违反 Principle #5；(d) 批内多根因，退化时二分困难。

### 选项 C（Synthesis，Architect 推荐，**采纳**）
Serial-A 为骨架 + Phase-1 内聚纯缓存改动：

| Phase | 含步骤 | 验证范围 | 回退边界 |
|-------|--------|----------|----------|
| **Phase 1** | P1-B + P2-C | 缓存契约单元测试（验收 #4）+ DB 缓存失效测试（覆盖 4 个 mutator） | 整体（TDD 守护） |
| **Phase 2** | P1-A 单独 | spatial_score 分布（验收 #2 量化） | 单步 |
| **Phase 3** | P1-C 单独 | matched_pairs 数量 + score 直方图（验收 #1、#8） | 单步 |
| **Phase 4** | P2-A → P2-B 串行 | matched_pairs + 候选集合大小 | 各自单步 |

### 被否决替代：Hungarian 最优二分匹配（invalidation rationale）
1. **依赖风险**：scipy 在 Blender 4.x bundled Python 不保证可用，自实现匈牙利算法 ~80 行增广路径代码，违反 Principle 2。
2. **收益未量化**：贪心按分数降序取最高未匹配对（`modtoolkit.py:713-728`），实际错配率未测。Hungarian 仅在"多个高分对竞争同一骨骼"时优于贪心，须先用 P1/P2 落地后回归数据量化该场景频率。
3. **契约冲突**：Hungarian 产出全局最优解可能改变既有样本 matched_pairs（贪心局部最优 ≠ 全局最优），与验收 #1"一致或更优"的"一致"硬约束冲突。在未建立"更优"量化判据前引入会破坏回归可比性。
结论：作为 P1/P2 落地后的独立后续方案，待错配率数据评估。本阶段否决。

## 五、验收标准（可测试，量化）

1. **回归无破坏**：对现有预设样本（`bip001-mmd.py`、`daz-standard.py`、`fbx-standard.py`、`bip01sb-cats.py`、`humanik-standard.py`、`dmc5-mmd.py`、`daz-mixamo.py`、`fbx-mixamo.py` 共 ≥8 个）执行 auto map，matched_pairs 数量 ≥ 优化前基线，且**对全部"新增匹配对"（优化后有、优化前无）逐一人工核验正确**（不止抽检 5 对，闭合 Critic 指出的质量退化盲区）。
2. **bbox 归一化修复（量化）**：构造 height=2.0、width=0.2、depth=0.2 的骨架，取两块仅 X 坐标不同（Y/Z 相同）的骨骼，断言修复前两者 spatial_score 差 < 0.05（被 height 稀释），修复后差 ≥ 0.15。同侧正确对 spatial_score ≥ 0.5，跨侧错误对 ≤ 0.35（mirror 已有 0.6 折扣，`modtoolkit.py:431`）。
3. **性能**：对 ≥150 核心骨骼的骨架对，SIMILARITY 模式 `auto_match_bones` 端到端耗时下降 ≥ 40%。基线测量方法：`time.perf_counter` 包裹 `auto_match_bones`，对同一骨架对跑 5 次取中位数；优化前基线取本分支 P1-B 落地前的 git commit（记录 commit hash 到测试报告）。骨架数据来源：现有 `.blend` 测试文件或脚本生成的对称骨架。
4. **记忆化正确性**：`name_score` / `_tokenize` 经 lru_cache 命中后返回值与未缓存一致（单元测试断言）；`name_score(a,b) == name_score(b,a)`（对称性）。
5. **CANON 阈值松弛**：构造 alias_score=0.55 的唯一同组候选，断言 P2-A 后进入 matched_pairs（P2-A 前 CANON_THRESHOLD=0.60 会丢弃）。
6. **新骨架召回**：`_invalidate_preset_cache()` 后对无历史预设骨架对，matched_pairs 数量 ≥ 基线。**召回权衡边界**（P1-C 触发条件 `max_preset_count==0` 的已知局限）：本验收覆盖"完全无历史"场景；对"有历史但本骨架所有对 pb 均为 0"的边缘场景，name 仍占 0.30 权重 + 全局 threshold=0.25 兜底，召回损失可接受（见 P1-C 权衡说明）。
7. **接口不变**：`auto_match_bones(src, tgt, threshold)` 签名与返回结构不变；`ListItem.bone` 的 `update` 回调行为不变；CANON 模式学习回调（`modtoolkit.py:741-759`）正常持久化。
8. **分数分布显式记录**：Phase 2 完成时同步记录一次 score 直方图作为 Phase 3 对比基线；Phase 3 落地后，对 ≥8 预设样本记录每对 matched 的 score 直方图（min/p50/p90/max + 计数），对比 Phase 2 基线。允许漂移但须写入测试报告，禁止隐式发生。

## 六、实施步骤

### Phase 1：P1-B + P2-C（纯缓存，TDD 先行）

**P1-B：`name_score` / `_tokenize` lru_cache 记忆化**
- `@lru_cache(maxsize=8192)` 包裹 `_tokenize`（`modtoolkit.py:313`，入参 str 可哈希，安全）。
- `@lru_cache(maxsize=8192)` 包裹 `name_score`（`modtoolkit.py:320`）。对称性天然支持（a,b)/(b,a) 分别缓存，命中率足够；不强制交换律 key（lru_cache C 级开销远低于 regex）。
- 模块级可见：`name_score` 被 `bone_database.resolve_fuzzy`（`bone_database.py:91` 懒导入）跨模块调用，缓存必须模块级，**不得放闭包内**。
- 生命周期：lru_cache 是进程级，Blender 重启 / Reload Scripts 后重建为空，无需手动失效。骨骼名纯函数输入（`modtoolkit.py:313-347` 无 `bpy.context`、无时间依赖、无模块可变状态），骨架切换无需失效。
- 隐式状态确认：`_strip_side`（`modtoolkit.py:286-310`）依赖模块常量 `_SIDE_SUFFIXES`/`_SIDE_TOKENS`，实现时 grep 确认无运行时写入点（本次评审未发现）。
- 循环导入：`modtoolkit.py:658` 与 `bone_database.py:91` 现有延迟导入已规避，lru_cache 包裹不引入新循环导入风险。
- 风险：maxsize=8192 对 `resolve_fuzzy`（200 entries × 5 aliases × 200 src = 20 万 distinct key）命中率有限——但 lru_cache LRU 驱逐 + C 级实现，即便命中率不高也比每次 regex 重算快；且 `auto_match` 主路径 distinct key 数远小于此（src×tgt 核心骨骼通常 <100²=1万）。

**P2-C：BoneDatabase 缓存（缓存解析结果，非实例）**
- **设计裁定（采纳 Critic 简化方案，否决 Architect 的 mutator-invalidate 过度设计）**：`load()` 保持 classmethod 每次新建 `BoneDatabase` 实例不变（`bone_database.py:33-38`），仅缓存"JSON 解析结果"（默认模板 `entries` 原始 dict 列表 + user_aliases dict）为模块级不可变快照。每次 `load()` 新建实例时复用解析快照、跳过 `open()/json.load()`。
- **无共享可变状态**：实例的 `user_aliases` 在 `add_alias`/`import_user` 时 mutate 的是该实例私有 dict（从快照浅拷贝而来），不影响其他实例或缓存快照。`reset_user` 清空实例私有状态，不影响快照。
- **失效**：`save_user()`/`import_user()` 写盘后调用 `invalidate_cache()` 丢弃解析快照，下次 `load()` 重新读盘重建。`reset_user()` 删盘后同样 invalidate。
- **收益边界**：`_on_list_bone_updated`（`modtoolkit.py:741-759`）受 `modtoolkit.py:743-745` 守卫（仅 CANON 模式 + 非空字段触发），实际低频；auto_match（`modtoolkit.py:659`）一次性。P2-C 主要省 JSON 解析 IO，对交互路径收益有限但无 correctness 风险。Critic 建议 profile load() 实际耗时再决定是否值得——本方案保留 P2-C 但标注为低优先，若 Phase 1 profile 显示 load() 耗时可忽略可跳过。

### Phase 2：P1-A（bbox 每轴归一化）
- `_compute_bbox`（`modtoolkit.py:395-407`）：第三元素由标量 `size` 改为每轴 `sizes = tuple(maxs[i]-mins[i] for i in range(3))`，每轴 < 1e-6 回退 1.0。**必须 tuple，不得生成器**（裁定 #1）。
- `_cached_spatial_score_positions`（`modtoolkit.py:574-586`）：归一化用每轴 `bbox[2][i]`。
- `spatial_score`（`modtoolkit.py:410-431`）：同步每轴归一化，保持公共函数契约。
- 消费点确认：全仓仅 `_cached_spatial_score_positions` 与 `spatial_score` 消费 bbox，均在 `modtoolkit.py` 内。

### Phase 3：P1-C（SIMILARITY 无预设重归一化）
- 触发条件：`max_preset_count == 0`（裁定 #4，`modtoolkit.py:632`）时对全部 SIMILARITY 对重归一化：`total = (0.30·ns + 0.15·hs + 0.10·ss) / 0.55`。
- `max_preset_count > 0`（有历史预设）时保持原式 `0.30·ns + 0.15·hs + 0.10·ss + 0.45·pb`。
- **不触及 CANON 分支**（`modtoolkit.py:657-700`，权重不同无 preset）。
- **召回权衡说明**（Critic Major #3）：`max_preset_count==0` 覆盖典型新骨架场景；对"有历史但本骨架完全不在历史中"的边缘场景不触发重归一化，此时 name 占 0.30 权重 + 全局 threshold=0.25 兜底，召回损失可接受。若需更精确可双循环外预计算 `any_pair_has_preset` 标志，本阶段不做（复杂度收益比不足）。

### Phase 4：P2-A → P2-B（串行）

**P2-A：CANON 阈值松弛**
- `CANON_THRESHOLD` 从 0.60 降至 0.40（`modtoolkit.py:660`，当前为函数内局部变量）。**保持代码内常量（局部或模块级均可），不改为场景属性**（避免新增 PropertyGroup/register 改动，闭合 Critic 指出的 UI 范围歧义）。
- 仍保留预过滤避免全矩阵爆炸；CANON 已按 canonical id 分组，组内候选极少，放宽影响可忽略。

**P2-B：SIMILARITY 短路剪枝（依赖 P1-C）**
- 常量 `RENORM_NAME_WEIGHT = 0.30/0.55`（裁定 #3）。
- 短路逻辑（仅在重归一化激活路径，即 `max_preset_count==0` 时生效）：先算 `ns`，若 `ns < threshold * RENORM_NAME_WEIGHT` 则跳过 `hs`/`ss`（赋 0）。
- `max_preset_count > 0` 路径：先算 `ns`+`pb`，若 `0.30·ns + 0.45·pb < threshold` 且 `ns == 0` 跳过 `hs`/`ss`。
- 等价简化（Planner 修订 #3）：`preset_bonus` 返回值仅 {0.0, 0.10, [0.6,1.0]}（`modtoolkit.py:539`/`548`/`549`），故 `max_preset_count>0` 路径短路实际等价"ns==0 且 pb∈{0.0,0.10} 时跳过"。单元测试覆盖此边界。

## 七、Pre-mortem（3 失败场景）

1. **重归一化导致既有样本回归退化**：P1-C 使"无预设"路径分数普遍升高，原本低于 threshold 的对越过阈值，matched_pairs 数量增加但含错误对。**缓解**：验收 #1 对全部新增匹配对逐一人工核验（不止抽检）；验收 #8 score 直方图显式记录漂移。若退化即回退 Phase 3。
2. **lru_cache 在 Blender 长会话内存累积**：maxsize=8192 限制上限，LRU 自动驱逐。骨骼名集合有限（核心骨骼通常 <200），distinct key 数远小于上限，内存可控。**缓解**：maxsize 硬上限 + 纯函数值不变，无脏数据风险。
3. **P2-C 缓存快照陈旧导致 CANON 学到旧别名**：用户外部编辑 `bone_canon_user.json` 后缓存未失效。**缓解**：`save_user`/`import_user`/`reset_user` 全路径调用 `invalidate_cache()`；缓存仅存解析结果非实例，无共享可变状态；提供 `invalidate_cache()` 公开方法供数据库重置 UI 显式调用。

## 八、验证步骤（unit / 集成 / e2e / observability）

**Unit**（`mapping_tools/tests/`，Blender 内运行）：
- `test_spatial_per_axis.py`：构造 height=2.0/width=0.2 骨架，断言修复前后 spatial_score 差（验收 #2 量化值）。
- `test_name_score_cache.py`：lru_cache 命中值 == 重算值；`name_score(a,b)==name_score(b,a)`；`_tokenize` 幂等。
- `test_canon_threshold.py`：alias_score=0.55 唯一候选断言进入 matched_pairs。
- `test_similarity_renormalize.py`：`_invalidate_preset_cache()` 后断言无预设时 name 主导且 matched_pairs ≥ 基线。
- `test_db_cache.py`：3 个写盘 mutator（`save_user`/`reset_user`/`import_user`）后 `invalidate_cache()` 被调用；`add_alias` 仅 mutate 实例私有 dict 不触发 invalidate。缓存命中返回的实例私有 mutate 不影响快照。
- `test_short_circuit.py`：覆盖 ns==0 且 pb∈{0.0,0.10} 短路边界；重归一化路径 `ns < threshold·RENORM_NAME_WEIGHT` 短路。

**集成 / 回归**：对 ≥8 预设样本逐个跑 auto map，记录优化前/后 matched_pairs + score 直方图，对全部新增匹配对人工核验。

**e2e**：在 Blender 4.5 中启用插件，N-panel XQFA → MappingTools，分别测 SIMILARITY / CANON 两模式完整流程，确认 UI 行为与 `_on_list_bone_updated` 学习回调持久化正常；导出 CSV 与 ABP 生成器联调（`mapping_tools/abp_generator.py` 消费 `xbone_csv_data`）。

**observability**：现有 `[AutoMap]` print 日志（`modtoolkit.py:640`/`677`/`728`/`734`/`736`）保留；Phase 3 后补充分数分布 dump（每对 matched 的 score 写入日志或测试报告），便于回归对比。

## 九、风险与缓解

| 风险 | 缓解 |
|------|------|
| bbox 结构变更影响未知消费点 | grep 全仓确认仅 modtoolkit.py 内 `_cached_spatial_score_positions` + `spatial_score` 消费 |
| lru_cache 在 Blender 长进程无界增长 | `maxsize=8192` + LRU 自动驱逐；进程级生命周期，重启重建 |
| 权重重归一化改变既有样本结果 | 验收 #1 全部新增对人工核验 + 验收 #8 直方图；退化即回退 |
| CANON 阈值放宽引入误匹配 | 最终贪心 + 全局 threshold 兜底；CANON 分组隔离保证只匹配同 canonical 条目 |
| 短路剪枝漏掉边界匹配 | `test_short_circuit.py` 覆盖；ns==0 时 hs 几乎不可能高（name=0 路径相似度极低） |
| P2-C 缓存快照陈旧 | mutator 全路径 invalidate；纯解析快照无共享可变状态；提供公开 invalidate 方法 |
| P2-C 过度设计/收益不足 | 采纳 Critic 简化方案（缓存解析结果非实例）；Phase 1 profile load() 耗时，可忽略则跳过 P2-C |

## 十、实施顺序（权威，替代原第六节）

1. **Phase 1**：P1-B（必做）+ P2-C（条件性：Phase 1 内先 profile `load()` 耗时，显著则做 P2-C，可忽略则跳过）。TDD 先行：缓存正确性单元测试。
2. **Phase 2**：P1-A 单独（spatial_score 量化验收）。
3. **Phase 3**：P1-C 单独（matched_pairs + score 直方图验收）。
4. **Phase 4**：P2-A → P2-B 串行（P2-B 依赖 P1-C 稳定）。

每 Phase 完成即运行对应单元测试 + ≥8 样本回归，再进入下一 Phase。

## 十一、不在本方案范围

- **Hungarian 最优二分匹配**：依赖风险、收益未量化、契约冲突，待 P1/P2 落地后用回归数据评估。
- 预设正则解析、ABP 生成器、骨骼数据库模板内容维护。

## 十二、AGENTS.md 同步

按全局 MANDATORY 规则，P1/P2 落地后同步 `mapping_tools/AGENTS.md`：
- Key Files 表 `modtoolkit.py` / `bone_database.py` 描述更新（lru_cache 记忆化、每轴归一化、重归一化、CANON 阈值 0.40、DB 解析快照缓存）。
- Common Patterns 补充：SIMILARITY 重归一化触发条件、CANON 阈值常量、DB 缓存 invalidate 契约。
- 不涉及新增/删除文件，Subdirectories 表无需改动。

---

## ADR（共识决策记录）

- **Decision**：采纳选项 C（Serial-A + Phase-1 聚类合成路径），4 Phase 落地 6 项改动。
- **Drivers**：bbox 确定性 bug 优先、行为变化风险梯度、P2-B→P1-C 硬依赖。
- **Alternatives considered**：选项 A（6 步串行，dev 周期长 2x）、选项 B（3 批聚类，否决：硬依赖+无并行收益+二分性损失）、Hungarian（否决：依赖+契约冲突+收益未量化）。
- **Why chosen**：选项 C 保留 A 的回归二分性（每 Phase 单一根因），在 Phase 1 安全聚合 P1-B/P2-C 纯缓存改动减少一次 Blender 重载周期；P1-C 触发收紧为 `max_preset_count==0` 保护有预设场景；P2-C 采用缓存解析结果避免共享可变状态 correctness 风险。
- **Consequences**：分数绝对分布漂移（P1-C 无预设路径 0.55→1.0）须通过验收 #8 显式记录；P1-C 对"有历史但本骨架无信号"边缘场景召回有限（已文档化权衡）；P2-C 对交互路径收益有限（已文档化，可跳过）。
- **Follow-ups**：P1/P2 落地后用回归数据评估 Hungarian 错配率；profile load() 决定 P2-C 是否保留；评估"本骨架无信号"场景是否需 `any_pair_has_preset` 精确标志。

## 评审 Changelog

- **v1**（初版）：6 步串行，P1-A→P1-B→P1-C→P2-A→P2-B→P2-C。
- **v2（本版，REVISE 后）**：合并 Architect 5 处修订（含 P1-A 生成器→tuple CRITICAL fix、P1-B lru_cache、P1-C 触发条件收紧、P2-B 常量命名、验收 #2 聚焦根因）；采纳选项 C 合成路径，原第六节顺序作废；验收 #2 量化（≥0.15 差值）；验收 #1 扩展为全部新增对人工核验 + 验收 #8 score 直方图；P2-C 改为缓存解析结果非实例（否决 mutator-invalidate 过度设计）；补 Principles 全文、Pre-mortem 3 场景、e2e/observability 验证、ADR、P1-C 召回权衡说明、P2-A 保持常量不引入 UI 改动、性能基线测量方法、lru_cache 生命周期、循环导入确认。
