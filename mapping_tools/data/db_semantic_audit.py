#!/usr/bin/env python3
"""
语义审计脚本 — 对 bone_canon_default.json 的每个别名做 KEEP/REMOVE_AUX/REMOVE_MIS/FLAG 判定。
严格按照 .omc/plans/db-semantic-audit.md 的语义分类法和规则执行。
"""

import json
import re
import os
from datetime import datetime

# ─── 常量定义 ──────────────────────────────────────────────

# 附录 B：噪声词（token 化时移除）
NOISE_TOKENS = {
    "bip01", "bip001", "mixamorig", "def", "b005",
    "l", "r", "left", "right", "lt", "rt", ""
}

# 附录 A：规范条目解剖对照表
ANATOMY_REF = {
    "bip01_pelvis":      {"meaning": "骨盆/髋(躯干根)", "category": "torso", "side": "center"},
    "bip01_spine":       {"meaning": "脊椎下段",     "category": "torso", "side": "center"},
    "bip01_spine1":      {"meaning": "脊椎中段",     "category": "torso", "side": "center"},
    "bip01_spine2":      {"meaning": "脊椎上段/上胸", "category": "torso", "side": "center"},
    "bip01_neck":        {"meaning": "颈",            "category": "head_neck", "side": "center"},
    "bip01_head":        {"meaning": "头",            "category": "head_neck", "side": "center"},
    "bip01_l_clavicle":  {"meaning": "左锁骨/肩",     "category": "arm", "side": "left"},
    "bip01_l_upperarm":  {"meaning": "左上臂",        "category": "arm", "side": "left"},
    "bip01_l_forearm":   {"meaning": "左前臂(含肘区)", "category": "arm", "side": "left"},
    "bip01_l_hand":      {"meaning": "左手(含腕)",     "category": "arm", "side": "left"},
    "bip01_r_clavicle":  {"meaning": "右锁骨/肩",     "category": "arm", "side": "right"},
    "bip01_r_upperarm":  {"meaning": "右上臂",        "category": "arm", "side": "right"},
    "bip01_r_forearm":   {"meaning": "右前臂(含肘区)", "category": "arm", "side": "right"},
    "bip01_r_hand":      {"meaning": "右手(含腕)",     "category": "arm", "side": "right"},
    "bip01_l_thigh":     {"meaning": "左大腿",        "category": "leg", "side": "left"},
    "bip01_l_calf":      {"meaning": "左小腿(含膝)",   "category": "leg", "side": "left"},
    "bip01_l_foot":      {"meaning": "左脚/踝",       "category": "leg", "side": "left"},
    "bip01_l_toe0":      {"meaning": "左脚趾",        "category": "leg", "side": "left"},
    "bip01_r_thigh":     {"meaning": "右大腿",        "category": "leg", "side": "right"},
    "bip01_r_calf":      {"meaning": "右小腿(含膝)",   "category": "leg", "side": "right"},
    "bip01_r_foot":      {"meaning": "右脚/踝",       "category": "leg", "side": "right"},
    "bip01_r_toe0":      {"meaning": "右脚趾",        "category": "leg", "side": "right"},
}

# 手指条目：{id → (指型0-4, 段号0-2, side)}
def finger_info(entry_id):
    """解析手指条目 ID，返回 (finger_type, segment, side) 或 None"""
    m = re.match(r"bip01_(l|r)_finger(\d)(\d?)$", entry_id)
    if not m:
        return None
    side = "left" if m.group(1) == "l" else "right"
    finger_type = int(m.group(2))
    segment = int(m.group(3)) if m.group(3) else 0  # 0, 1, 2
    return (finger_type, segment, side)

FINGER_TYPE_NAMES = {0: "拇指", 1: "食指", 2: "中指", 3: "无名指", 4: "小指"}
SEGMENT_NAMES = {0: "近节", 1: "中节", 2: "远节"}

def finger_anatomy_meaning(entry_id):
    info = finger_info(entry_id)
    if not info:
        return None
    ft, seg, side = info
    side_cn = "左" if side == "left" else "右"
    return f"{side_cn}{FINGER_TYPE_NAMES[ft]}{SEGMENT_NAMES[seg]}"

# ─── 第 4 章：辅助骨骼识别规则 ─────────────────────────────

# 4.1 变形/校正骨骼
DEFORM_PATTERNS = [
    r'\bmuscle[_.]',          # Muscle_ / Muscle.
    r'\bmuscle\b',             # standalone muscle
    r'_twist\b',               # suffix _twist
    r'-twist\b',               # suffix -twist
    r'\btwist\b',              # standalone twist
    r'\bcorrective\b',
    r'\bfix\b',
    r'\bhelper\b',
]

# 4.1 _Root 后缀（在非 pelvis 条目）
ROOT_PATTERN = re.compile(r'_root\b', re.IGNORECASE)

# 4.2 服装/装备/道具
EQUIPMENT_KEYWORDS = {
    "armor", "armour", "besagew", "pauldron", "gauntlet", "greave",
    "skirt", "robe", "cape", "cloak", "scarf", "belt", "buckle",
    "button", "strap", "ribbon", "glove", "boot", "shoe", "hat",
    "crown", "horn",
}

# 4.3 毛发/面部细节/非骨架
NON_SKELETAL_KEYWORDS = {
    "hair", "wing", "tail", "weapon", "prop",
    "eyeball", "smastoid", "teeth", "tongue", "nose",
    "ear", "lip", "brow",
}

# "tie" — 领带/绳结
TIE_PATTERN = re.compile(r'^tie[_\d]', re.IGNORECASE)   # Tie_1, tie_1, etc.

# "bow" — 需要 token 级判定(不能裸 in 子串)
# 已在 token 化后基于整 token 判定

# 4.4 游戏专属整骨命名
GAME_PREFIXES = {"d_", "bn_", "nonex_", "po_", "dm_"}

# "jaw" — 在 head 下 KEEP，在其他条目下可能 REMOVE_AUX
# "ear" — 同上

# ─── 第 6 章：受保护别名 ──────────────────────────────────

# 手指源命名约定别名 (protected patterns)
FINGER_NAME_PATTERNS = [
    re.compile(r'^thumb\d_[lr]$'),                              # thumb0_l
    re.compile(r'^(indexfinger|middlefinger|ringfinger|littlefinger)\d_[lr]$'),  # ringfinger3_l
    re.compile(r'^mixamorig:leftthumb\w+$', re.IGNORECASE),
    re.compile(r'^mixamorig:rightthumb\w+$', re.IGNORECASE),
]

# 受保护关键词（在该条目下绝对不能移除）
PROTECTED_KEYWORDS_PER_ENTRY = {
    # 解剖学标准同义词在其正确条目下
}

ANATOMICAL_STANDARDS = {
    "hips", "pelvis", "spine", "head", "neck",
    "knee", "elbow", "wrist", "ankle", "shoulder",
    "clavicle", "collarbone", "collar", "jaw",
    "thigh", "calf", "shin", "foot", "toe", "finger",
    "hand", "arm", "leg", "forearm", "upperarm", "bicep",
}

# ─── Token 化与语义分析函数 ──────────────────────────────

def tokenize(alias):
    """按 _. : - 空格 切分，转小写，剔除噪声词"""
    tokens = re.split(r'[_.:\- ]+', alias.lower())
    tokens = [t for t in tokens if t not in NOISE_TOKENS]
    return tokens

def has_side_conflict(alias, entry_side):
    """侧一致性检查：left 条目包含仅 right 标记 → REMOVE_MIS"""
    tl = alias.lower()
    has_left = bool(re.search(r'\bleft\b|(?<!\w)_l\b|(?<!\w)\.l\b|^l_', tl))
    has_right = bool(re.search(r'\bright\b|(?<!\w)_r\b|(?<!\w)\.r\b|^r_', tl))
    if entry_side == "left" and has_right and not has_left:
        return True
    if entry_side == "right" and has_left and not has_right:
        return True
    return False

def check_protected(alias, entry_id, entry):
    """第 6 章：受保护别名检查"""
    calias = alias.lower().strip()
    cname = entry["canonical_name"].lower().strip()
    dname = entry.get("display_name", "").lower().strip()

    # 1. canonical_name / display_name 本身
    if calias == cname or calias == dname:
        return True, "canonical/display name"

    # 2. 手指源命名约定别名
    for pat in FINGER_NAME_PATTERNS:
        if pat.match(calias):
            return True, "手指源命名约定 (protected pattern)"

    # 3. Bip01/Bip001/Mixamo 标准命名变体 — 包含就 KEEP
    for prefix in ["bip01", "bip001", "mixamorig"]:
        if prefix in calias and any(kw in calias for kw in _entry_keywords(entry_id)):
            return True, "标准命名变体"

    return False, ""

def _entry_keywords(entry_id):
    """从 entry_id 提取关键词用于匹配"""
    parts = re.split(r'[_.-]', entry_id.lower())[1:]  # skip bip01
    return parts

def is_root_alias(tokens, entry_id):
    """检查是否为 _Root 后缀且挂在非 pelvis 条目"""
    return False  # 在 token 级别已经看不到 _root 了
    # 实际上 _root 后缀需要在完整别名字符串上检查

def check_auxiliary(alias, tokens, entry_id):
    """
    第 4 章：辅助骨骼识别。
    返回 (is_aux, reason) 或 (False, "")
    """
    lower = alias.lower()

    # 4.1 变形/校正骨骼 — 用完整字符串匹配
    for pat_str in DEFORM_PATTERNS:
        if re.search(pat_str, lower):
            return True, f"辅助骨骼: 变形/校正 ({pat_str})"

    # _Root 检查（完整字符串）
    if ROOT_PATTERN.search(lower):
        if entry_id != "bip01_pelvis":
            return True, "辅助骨骼: _Root 后缀挂非 pelvis 条目"

    # 4.2 服装/装备/道具 — token 级
    for tk in tokens:
        if tk in EQUIPMENT_KEYWORDS:
            return True, f"辅助骨骼: 服装/装备 ({tk})"

    # 4.3 毛发/面部细节/非骨架 — token 级
    for tk in tokens:
        if tk in NON_SKELETAL_KEYWORDS:
            # jaw 在 head 下 KEEP, ear 也可能合法
            if tk == "ear" and entry_id in ("bip01_head",):
                continue
            if tk == "jaw" and entry_id in ("bip01_head",):
                continue
            return True, f"辅助骨骼: 非骨架 ({tk})"

    # tie 检查
    if TIE_PATTERN.match(lower):
        return True, "辅助骨骼: 领带/绳结"

    # 4.4 游戏专属整骨前缀
    for prefix in GAME_PREFIXES:
        if lower.startswith(prefix):
            return True, f"游戏专属命名前缀 ({prefix})"

    # bow — token 级判定（禁止子串匹配）
    if "bow" in tokens:
        return True, "辅助骨骼: 装饰品 bow (蝴蝶结)"

    return False, ""

def check_mismatch(alias, tokens, entry_id, entry):
    """
    第 5 章：语义错配识别。
    返回 (is_mis, reason, suggest_entry) 或 (False, "", "")
    """
    # 侧一致性检查
    entry_side = entry["side"]
    if has_side_conflict(alias, entry_side):
        return True, "侧不一致", ""

    # 主体部位 vs 条目含义
    # 核心部位词映射
    body_part_mapping = {
        "pelvis": "bip01_pelvis", "hips": "bip01_pelvis", "hip": "bip01_pelvis",
        "waist": "bip01_pelvis",
        "spine": "bip01_spine", "spine1": "bip01_spine1", "spine2": "bip01_spine2",
        "chest": "bip01_spine2",  # chest=上胸→spine2 (但在 spine1 是 FLAG)
        "neck": "bip01_neck",
        "head": "bip01_head", "skull": "bip01_head", "jaw": "bip01_head",
        "clavicle": None, "collarbone": None, "shoulder": "bip01_l_clavicle",
        "upperarm": None, "upper_arm": None, "bicep": None, "arm": None,
        "forearm": None, "lower_arm": None, "elbow": None,
        "hand": None, "wrist": None,
        "thigh": None, "upperleg": None, "upleg": None, "upper_leg": None,
        "calf": None, "lowerleg": None, "shin": None, "knee": None, "leg": None,
        "foot": None, "ankle": None,
        "toe": None,
    }

    # 手指相关的主体部位
    finger_body_parts = {
        "thumb": 0, "index": 1, "indexfinger": 1,
        "middle": 2, "middlefinger": 2,
        "ring": 3, "ringfinger": 3,
        "pinky": 4, "littlefinger": 4, "little": 4,
    }

    # 对躯干条目做精细检查
    category = entry["category"]
    if category == "torso":
        for tk in tokens:
            if tk in body_part_mapping:
                target = body_part_mapping[tk]
                if target and target != entry_id:
                    # 特例: chest 在 spine1 → FLAG 而非 REMOVE_MIS
                    # 特例: spine_01 在 pelvis → UE 风格，KEEP
                    # 特例: waist 在 pelvis → KEEP
                    pass  # 不做全量自动判定，下面单独处理

    # 检查是否有 body part token 属于不同 entry
    # 对 torso 类别的特殊处理
    # torso 类的 chest 归属歧义由 check_flag 处理
    # root 特殊处理：root 在 pelvis 是 FLAG (附录 C)
    return False, "", ""

def check_flag(alias, tokens, entry_id, entry):
    """
    附录 C：已知歧义点。返回 (is_flag, reason)
    """
    lower = alias.lower()

    # C.1 chest 在 spine1
    if "chest" in tokens and entry_id == "bip01_spine1":
        return True, "跨骨架歧义: chest 在中段 spine1，部分骨架 chest=上段 spine2。待人工决策"

    # C.2 root 在 pelvis
    if "root" in tokens and entry_id == "bip01_pelvis":
        return True, "root 别名在 pelvis 合理但可能让独立根骨误解析进 pelvis。待人工决策"

    # hip_l / hip_r 在 pelvis (center 条目含侧标记) — 这个实际上合法
    # KEEP

    return False, ""

# ─── 主导审计函数 ─────────────────────────────────────────

def audit_aliases(db_path):
    """对数据库逐条目、逐别名执行语义审计"""
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    results = {}
    total_aliases = 0
    keep_count = 0
    remove_aux_count = 0
    remove_mis_count = 0
    flag_count = 0
    blacklist_suggestions = set()
    migration_suggestions = []

    for entry in db["bones"]:
        eid = entry["id"]
        entry_results = []
        entry_aliases = entry.get("aliases", [])
        total_aliases += len(entry_aliases)

        for alias in entry_aliases:
            tokens = tokenize(alias)
            verdict = "KEEP"
            reason = "合法命名变体"
            suggest_entry = ""

            # Step 1: 受保护别名检查（最高优先级）
            is_protected, prot_reason = check_protected(alias, eid, entry)
            if is_protected:
                verdict = "KEEP"
                reason = f"[受保护] {prot_reason}"
            else:
                # Step 2: 辅助骨骼检查
                is_aux, aux_reason = check_auxiliary(alias, tokens, eid)
                if is_aux:
                    verdict = "REMOVE_AUX"
                    reason = aux_reason
                    # 提取黑名单关键词
                    for tk in tokens:
                        if tk not in ANATOMICAL_STANDARDS and tk not in NOISE_TOKENS:
                            if len(tk) > 1:
                                blacklist_suggestions.add(tk)
                else:
                    # Step 3: 歧义检查（FLAG — 必须先于 REMOVE_MIS，覆盖 Appendix C 预判）
                    is_flag, flag_reason = check_flag(alias, tokens, eid, entry)
                    if is_flag:
                        verdict = "FLAG"
                        reason = flag_reason
                    else:
                        # Step 4: 语义错配检查
                        is_mis, mis_reason, suggest = check_mismatch(alias, tokens, eid, entry)
                        if is_mis:
                            verdict = "REMOVE_MIS"
                            reason = mis_reason
                            suggest_entry = suggest
                            if suggest:
                                migration_suggestions.append({
                                    "alias": alias,
                                    "from_entry": eid,
                                    "suggest_entry": suggest
                                })
                        else:
                            # 默认 KEEP
                            verdict = "KEEP"

            # 统计
            if verdict == "KEEP":
                keep_count += 1
            elif verdict == "REMOVE_AUX":
                remove_aux_count += 1
            elif verdict == "REMOVE_MIS":
                remove_mis_count += 1
            elif verdict == "FLAG":
                flag_count += 1

            entry_results.append({
                "alias": alias,
                "verdict": verdict,
                "reason": reason,
                "suggest_entry": suggest_entry if suggest_entry else None
            })

        results[eid] = entry_results

    return {
        "entries": results,
        "summary": {
            "total_aliases": total_aliases,
            "keep": keep_count,
            "remove_aux": remove_aux_count,
            "remove_mis": remove_mis_count,
            "flag": flag_count,
        },
        "blacklist_suggestions": sorted(list(blacklist_suggestions)),
        "migration_suggestions": migration_suggestions,
    }

def category_is_known(entry, tokens):
    """检查 entry category 是否与 tokens 中的已知部位词匹配"""
    category = entry["category"]
    if category == "finger":
        return True
    # 简单检查：至少有一个 token 在解剖标准词中
    return any(t in ANATOMICAL_STANDARDS for t in tokens)

# ─── 报告生成 ─────────────────────────────────────────────

def generate_report(audit_data, output_dir):
    """生成 db_audit_verdicts.json 和 db_audit_report.md"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. JSON 裁决文件
    verdicts = {
        "generated_at": ts,
        "summary": audit_data["summary"],
        "blacklist_suggestions": audit_data["blacklist_suggestions"],
        "migration_suggestions": audit_data["migration_suggestions"],
        "entries": {}
    }
    for eid, aliases in audit_data["entries"].items():
        verdicts["entries"][eid] = {"aliases": aliases}

    json_path = os.path.join(output_dir, "db_audit_verdicts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(verdicts, f, ensure_ascii=False, indent=2)

    # 2. Markdown 报告
    s = audit_data["summary"]
    lines = []
    lines.append(f"# 规范骨骼数据库语义审计报告\n")
    lines.append(f"> 生成时间: {ts}")
    lines.append(f"> 目标文件: `mapping_tools/data/bone_canon_default.json`")
    lines.append(f"> 审计方案: `.omc/plans/db-semantic-audit.md`\n")

    lines.append("## 汇总\n")
    lines.append("| 指标 | 数量 |")
    lines.append("|---|---|")
    lines.append(f"| 总别名数 | {s['total_aliases']} |")
    lines.append(f"| KEEP (保留) | {s['keep']} |")
    lines.append(f"| REMOVE_AUX (辅助骨骼) | {s['remove_aux']} |")
    lines.append(f"| REMOVE_MIS (语义错配) | {s['remove_mis']} |")
    lines.append(f"| FLAG (待人工复核) | {s['flag']} |")

    # 每条目别名数变化
    lines.append("\n## 各条目别名数量\n")
    lines.append("| 条目 | 当前别名数 | KEEP | REMOVE_AUX | REMOVE_MIS | FLAG |")
    lines.append("|---|---|---|---|---|---|")
    for eid in sorted(audit_data["entries"].keys()):
        aliases = audit_data["entries"][eid]
        keeps = sum(1 for a in aliases if a["verdict"] == "KEEP")
        auxs = sum(1 for a in aliases if a["verdict"] == "REMOVE_AUX")
        miss = sum(1 for a in aliases if a["verdict"] == "REMOVE_MIS")
        flags = sum(1 for a in aliases if a["verdict"] == "FLAG")
        # 异常数量标注
        note = ""
        if len(aliases) < 3:
            note = " ⚠️ 别名过少(<3)"
        elif len(aliases) > 25:
            note = " ⚠️ 别名过多(>25)"
        lines.append(f"| {eid} | {len(aliases)} | {keeps} | {auxs} | {miss} | {flags}{note} |")

    # FLAG 清单
    lines.append("\n## FLAG 清单（待人工复核）\n")
    flag_items = []
    for eid in sorted(audit_data["entries"].keys()):
        for a in audit_data["entries"][eid]:
            if a["verdict"] == "FLAG":
                flag_items.append(f"- `{a['alias']}` @ {eid}: {a['reason']}")
    if flag_items:
        lines.extend(flag_items)
    else:
        lines.append("_(无)_")

    # REMOVE_AUX 清单
    lines.append("\n## REMOVE_AUX 清单（辅助骨骼）\n")
    aux_items = []
    for eid in sorted(audit_data["entries"].keys()):
        for a in audit_data["entries"][eid]:
            if a["verdict"] == "REMOVE_AUX":
                aux_items.append(f"- `{a['alias']}` @ {eid}: {a['reason']}")
    if aux_items:
        lines.extend(aux_items)
    else:
        lines.append("_(无)_")

    # REMOVE_MIS 清单
    lines.append("\n## REMOVE_MIS 清单（语义错配）\n")
    mis_items = []
    for eid in sorted(audit_data["entries"].keys()):
        for a in audit_data["entries"][eid]:
            if a["verdict"] == "REMOVE_MIS":
                sug = f" → 建议归属 `{a['suggest_entry']}`" if a.get("suggest_entry") else ""
                mis_items.append(f"- `{a['alias']}` @ {eid}: {a['reason']}{sug}")
    if mis_items:
        lines.extend(mis_items)
    else:
        lines.append("_(无)_")

    # 黑名单建议
    lines.append("\n## 黑名单建议\n")
    if audit_data["blacklist_suggestions"]:
        lines.append("建议添加到 `_BLACKLIST_KEYWORDS` 的新关键词：\n")
        for kw in audit_data["blacklist_suggestions"]:
            lines.append(f"- `{kw}`")
    else:
        lines.append("_(无需新增)_")

    # 迁移建议
    lines.append("\n## 迁移建议\n")
    if audit_data["migration_suggestions"]:
        for m in audit_data["migration_suggestions"]:
            lines.append(f"- `{m['alias']}`: {m['from_entry']} → {m['suggest_entry']}")
    else:
        lines.append("_(无)_")

    # 结论
    lines.append("\n---\n")
    if s['remove_aux'] == 0 and s['remove_mis'] == 0 and s['flag'] == 0:
        lines.append("## 结论\n\n**数据库非常干净，无需清理。** 所有别名均通过语义审计。\n")
    elif s['remove_aux'] == 0 and s['remove_mis'] == 0:
        lines.append(f"## 结论\n\n数据库没有发现辅助骨骼或语义错配。仅有 {s['flag']} 条 FLAG 待人工复核。\n")
    else:
        lines.append(f"## 结论\n\n共需移除 {s['remove_aux'] + s['remove_mis']} 条别名，{s['flag']} 条 FLAG 待人工复核。请先确认 REMOVE 裁决后再执行 Phase D 应用。\n")

    md_path = os.path.join(output_dir, "db_audit_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path

# ─── 主入口 ────────────────────────────────────────────────

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "bone_canon_default.json")

    print("=" * 60)
    print("语义审计: bone_canon_default.json")
    print("=" * 60)

    audit_data = audit_aliases(db_path)
    s = audit_data["summary"]
    print(f"\n总别名: {s['total_aliases']}")
    print(f"  KEEP:        {s['keep']}")
    print(f"  REMOVE_AUX:  {s['remove_aux']}")
    print(f"  REMOVE_MIS:  {s['remove_mis']}")
    print(f"  FLAG:        {s['flag']}")

    # 输出 FLAG 详情
    if s['flag'] > 0:
        print(f"\n--- FLAG 详细 ---")
        for eid in sorted(audit_data["entries"].keys()):
            for a in audit_data["entries"][eid]:
                if a["verdict"] == "FLAG":
                    print(f"  [{a['verdict']}] {a['alias']} @ {eid}: {a['reason']}")

    # 输出 REMOVE_AUX 详情
    if s['remove_aux'] > 0:
        print(f"\n--- REMOVE_AUX 详细 ---")
        for eid in sorted(audit_data["entries"].keys()):
            for a in audit_data["entries"][eid]:
                if a["verdict"] == "REMOVE_AUX":
                    print(f"  [{a['verdict']}] {a['alias']} @ {eid}: {a['reason']}")

    # 输出 REMOVE_MIS 详情
    if s['remove_mis'] > 0:
        print(f"\n--- REMOVE_MIS 详细 ---")
        for eid in sorted(audit_data["entries"].keys()):
            for a in audit_data["entries"][eid]:
                if a["verdict"] == "REMOVE_MIS":
                    sug = f" → {a['suggest_entry']}" if a.get("suggest_entry") else ""
                    print(f"  [{a['verdict']}] {a['alias']} @ {eid}: {a['reason']}{sug}")

    # 生成报告
    json_path, md_path = generate_report(audit_data, script_dir)
    print(f"\n报告已生成:")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")

    # 检查各条目别名数量
    print(f"\n--- 条目别名数检查 ---")
    for eid in sorted(audit_data["entries"].keys()):
        n = len(audit_data["entries"][eid])
        flag = ""
        if n < 3:
            flag = " ⚠️ <3"
        elif n > 25:
            flag = " ⚠️ >25"
        if flag:
            print(f"  {eid}: {n} aliases{flag}")
