# type: ignore
import bpy
from bpy.props import (
    IntProperty,
    StringProperty,
    PointerProperty,
    CollectionProperty,
    BoolProperty,
)
from bpy.types import (
    PropertyGroup,
    UIList,
    Operator,
    Panel,
    Menu,
    Scene,
    Object,
)
from bpy.utils import register_class, unregister_class
from bl_operators.presets import AddPresetBase
import os
import json
import re
import math


class Localization:
    localizations = {
        "en": {
            # pointer panel
            "mainpanel.label": "Vertex Group Rename Tool",
            "mainpanel.armature_pointer": "select an armature:",
            "mainpanel.mesh_pointer": "select a mesh:",
            "mainpanel.start_assignment": "start assign",
            "mainpanel.start_assignment.tip": "start assign bones' name to vertex groups",
            "mainpanel.stop": "reset assign",
            "mainpanel.stop.tip": "stop and reset the assign process",
            "mainpanel.is_mid_start": "unused vertex groups only (experimental)",
            "mainpanel.is_mid_start.tip": "sort by bone hierarchy, and start rename with unused vertex groups",
            # vertex group assignment panel
            "mainpanel.vertex_group_string": "current vertex group: ",
            "mainpanel.next": "next",
            "mainpanel.next.tip": "add current selected bones and vertex group to rename list",
            "mainpanel.skip": "skip",
            "mainpanel.skip.tip": "skip assignment for current bone",
            "ul_list.vg.tip": "vertex group name",
            "ul_list.bone.tip": "target bone name",
            "my_list.new_item": "add",
            "my_list.new_item.tip": "add an item from list",
            "my_list.delete_item": "remove",
            "my_list.delete_item.tip": "Remove an item from list",
            "mainpanel.done": "start rename",
            "mainpanel.done.tip": "start rename for the current rename list",
            "mainpanel.ismerging": "enable merging (experimental)",
            "mainpanel.ismerging.tip": "merge with existed vertex group after rename",
            # presets panel
            "menu_presets": "presets",
            "presets.save": "save",
            "presets.delete": "delete",
            "presets.tip": "Save or delete preset from local",
            "presets.open_folder": "open presets folder",
            "presets.open_folder.tip": "Open presets folder in the explorer",
            # misc panel
            "miscpanel.label": "Misc",
            "miscpanel.remove_empty": "remove empty VG",
            "miscpanel.remove_empty.tip": "remove all empty vertex group for active mesh",
            "miscpanel.remove_unused": "remove unused VG",
            "miscpanel.remove_unused.tip": "remove all unused vertex group for active mesh",
            "miscpanel.merge_mats": "auto merge mats",
            "miscpanel.merge_mats.tip": "merge materials with same texture for active mesh",
            "miscpanel.select_seams": "select seams",
            "miscpanel.select_seams.tip": "select edges marked as seams for active mesh",
            # credit panel
            "creditpanel.label": "Credit",
            "creditpanel.github": "Github: 0w0-Yui",
            "creditpanel.bilibili": "bilibili: 0w0-Yui",
            # from bones
            "my_list.add_from_bones": "from bones",
            "my_list.add_from_bones.tip": "Add mappings from selected bones (active bone as target)",
            "my_list.reverse_mappings": "reverse",
            "my_list.reverse_mappings.tip": "Reverse all mappings in the list (swap source and target)",
            "my_list.sort_by_name": "sort by name",
            "my_list.sort_by_name.tip": "Sort mapping list alphabetically by source bone name",
            "my_list.sort_by_hierarchy": "sort by hierarchy",
            "my_list.sort_by_hierarchy.tip": "Sort mapping list by target bone hierarchy depth",
            # auto map
            "auto_map.label": "Auto Bone Mapping",
            "auto_map.src": "Source Armature",
            "auto_map.tgt": "Target Armature",
            "my_list.auto_map": "Auto Map",
            "my_list.auto_map.tip": "Automatically create core bone mappings from two armatures",
            "report.need_2_armatures": "Please select two different armatures!",
            "report.auto_map_done": "Auto mapping complete",
            "report.no_match": "No bone matches found",
            # report
            "report.no_active_mesh": "no active mesh!",
            "report.no_active_bone": "no bone selected",
            "report.no_active": "no armature/mesh selected",
            "report.no_armature": "no amature found for active mesh!",
            "report.active_not_mesh": "active object is not a mesh!",
            "report.not_weight_mode": "please enter weight paint mode!",
            "report.name_collision": "name collision found, details see command prompt!",
            "report.done": "done!",
            "report.not_pose_mode": "please enter pose mode!",
            "report.need_2_bones": "please select at least 2 bones!",
            "report.no_active_bone_pose": "no active bone found!",
            "report.reverse_done": "mappings reversed!",
        },
        "zh": {
            # pointer panel
            "mainpanel.label": "顶点组重命名工具",
            "mainpanel.armature_pointer": "选择目标骨架:",
            "mainpanel.mesh_pointer": "选择目标模型:",
            "mainpanel.start_assignment": "开始指定",
            "mainpanel.start_assignment.tip": "开始将骨骼名称指定给顶点组",
            "mainpanel.stop": "重置指定",
            "mainpanel.stop.tip": "停止并重置指定流程",
            "mainpanel.is_mid_start": "仅指定未使用顶点组 (实验性功能)",
            "mainpanel.is_mid_start.tip": "先按骨骼层级排序, 然后从骨骼未使用的顶点组开始指定",
            # vertex group assignment panel
            "mainpanel.vertex_group_string": "当前顶点组: ",
            "mainpanel.next": "下一个",
            "mainpanel.next.tip": "添加当前选中骨骼和顶点组到重命名列表并选择下一个顶点组",
            "mainpanel.skip": "跳过",
            "mainpanel.skip.tip": "跳过当前顶点组指定",
            "ul_list.vg.tip": "顶点组名称",
            "ul_list.bone.tip": "目标骨骼名称",
            "my_list.new_item": "添加",
            "my_list.new_item.tip": "添加一个重命名列表项",
            "my_list.delete_item": "删除",
            "my_list.delete_item.tip": "删除选中重命名列表项",
            "mainpanel.done": "开始重命名",
            "mainpanel.done.tip": "根据当前重命名列表开始批量重命名顶点组",
            "mainpanel.ismerging": "启用合并 (实验性功能)",
            "mainpanel.ismerging.tip": "重命名后会并入已有的顶点组",
            # presets panel
            "menu_presets": "重命名列表预设",
            "presets.save": "保存",
            "presets.delete": "删除",
            "presets.tip": "保存或删除当前重命名列表预设",
            "presets.open_folder": "打开预设文件夹",
            "presets.open_folder.tip": "用资源管理器打开预设存储文件夹",
            # misc panel
            "miscpanel.label": "杂项",
            "miscpanel.remove_empty": "移除空顶点组",
            "miscpanel.remove_empty.tip": "为选中模型移除空顶点组",
            "miscpanel.remove_unused": "移除未使用顶点组",
            "miscpanel.remove_unused.tip": "根据选中模型的骨架修改器移除未使用的顶点组",
            "miscpanel.merge_mats": "自动合并材质",
            "miscpanel.merge_mats.tip": "遍历选中模型材质列表并合并相同贴图项",
            "miscpanel.select_seams": "选中缝合边",
            "miscpanel.select_seams.tip": "选中当前模型缝合边",
            # credit panel
            "creditpanel.label": "作者",
            "creditpanel.github": "Github: 0w0-Yui",
            "creditpanel.bilibili": "B站: 0w0-Yui",
            # from bones
            "my_list.add_from_bones": "从骨骼添加",
            "my_list.add_from_bones.tip": "从选中的骨骼添加映射（活跃骨骼为目标，其余为源）",
            "my_list.reverse_mappings": "反转映射",
            "my_list.reverse_mappings.tip": "反转映射表中所有条目的源和目标",
            "my_list.sort_by_name": "按名称排序",
            "my_list.sort_by_name.tip": "按源骨骼名称字母顺序排序映射表",
            "my_list.sort_by_hierarchy": "按层级排序",
            "my_list.sort_by_hierarchy.tip": "按目标骨骼在骨架中的层级深度排序映射表",
            # auto map
            "auto_map.label": "自动骨骼映射",
            "auto_map.src": "源骨架",
            "auto_map.tgt": "目标骨架",
            "my_list.auto_map": "自动匹配",
            "my_list.auto_map.tip": "根据两个骨架自动创建核心骨骼映射",
            "report.need_2_armatures": "请选择两个不同的骨架",
            "report.auto_map_done": "自动匹配完成",
            "report.no_match": "未找到任何匹配",
            # report
            "report.no_active_mesh": "未选中模型",
            "report.no_active_bone": "未选中骨骼",
            "report.no_active": "未选中骨架或模型",
            "report.no_armature": "选中骨骼未找到正确的骨架修改器",
            "report.active_not_mesh": "选中物体不是模型",
            "report.not_weight_mode": "请进入权重模式",
            "report.name_collision": "名字冲突, 详情见控制台输出",
            "report.done": "完成! ",
            "report.not_pose_mode": "请进入姿态模式",
            "report.need_2_bones": "请至少选中2根骨骼",
            "report.no_active_bone_pose": "未找到活跃骨骼",
            "report.reverse_done": "映射已反转",
        },
    }

    def get_localization(context):
        lang = None
        current = context.preferences.view.language
        if current == "zh_CN" or current == "zh_TW":
            lang = Localization.localizations["zh"]
        else:
            lang = Localization.localizations["en"]
        return lang


LANG = Localization.get_localization(bpy.context)


# ===========================================================================
# Auto Bone Mapping - Core Functions
# ===========================================================================

# -- Bone filtering keywords --
_BLACKLIST_KEYWORDS = [
    # Physics
    "phys", "physics", "cloth", "hair", "skirt", "dress", "breast",
    "belly", "jiggle", "spring", "dynamic",
    # IK/FK helpers
    "ik_", "fk_", "pole", "twist", "roll", "stretch", "ik",
    # Auxiliary
    "helper", "dummy", "adj", "shadow", "driver", "mch", "def_", "copy", "tweak",
    # Decorative
    "weapon", "slot", "attach", "prop",
]

_WHITELIST_KEYWORDS = [
    # Torso
    "spine", "head", "neck", "pelvis", "hip", "root",
    # Arms / Hands
    "arm", "hand", "finger", "thumb",
    # Legs / Feet
    "leg", "foot", "toe", "thigh", "calf", "shin",
    # Shoulders
    "clavicle", "shoulder", "upperarm", "lowerarm",
    "upperleg", "lowerleg", "ball",
]


def is_core_bone(bone_name: str) -> bool:
    """Return True if bone_name belongs to the core skeleton (not physics/IK/aux)."""
    name_lower = bone_name.lower()
    # Whitelist takes priority: if any whitelist keyword matches -> keep
    for kw in _WHITELIST_KEYWORDS:
        if kw in name_lower:
            return True
    # Blacklist: if any blacklist keyword matches -> exclude
    for kw in _BLACKLIST_KEYWORDS:
        if kw in name_lower:
            return False
    # Default: keep (treat as core if ambiguous)
    return True


# -- Side-prefix/suffix stripping for name comparison --
_SIDE_PREFIXES = [
    "left_", "right_", "l_", "r_",
    "left", "right",
    "lt_", "rt_", "lt", "rt",
]

_SIDE_SUFFIXES = [
    "_left", "_right", ".left", ".right",
    "_l", "_r", ".l", ".r",
]


def _strip_side(name: str) -> str:
    """Remove leading/trailing side markers. Matches longest first to avoid short-match errors."""
    lower = name.lower()
    for prefix in sorted(_SIDE_PREFIXES, key=len, reverse=True):
        if lower.startswith(prefix):
            return lower[len(prefix):]
    for suffix in sorted(_SIDE_SUFFIXES, key=len, reverse=True):
        if lower.endswith(suffix):
            return lower[:-len(suffix)]
    return lower


def _tokenize(name: str) -> list:
    """Split bone name into tokens: camelCase, digits, and common separators (_ . , -)."""
    name = re.sub(r'([A-Z])', r'_\1', name)
    name = re.sub(r'(\d+)', r'_\1', name)
    return [t for t in re.split(r"[_. \-]", name.lower()) if t]


def name_score(name_a: str, name_b: str) -> float:
    """Compute name similarity between two bone names -> [0, 1]."""
    tokens_a = set(_tokenize(name_a))
    tokens_b = set(_tokenize(name_b))
    if not tokens_a or not tokens_b:
        return 0.0
    # Jaccard similarity on full tokens
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union) if union else 0.0

    # Side-stripped bonus: strip side at whole-name level first, then per token
    stripped_a = {
        s for t in _tokenize(_strip_side(name_a))
        for s in (_strip_side(t),) if s
    }
    stripped_b = {
        s for t in _tokenize(_strip_side(name_b))
        for s in (_strip_side(t),) if s
    }
    if stripped_a and stripped_b:
        s_inter = stripped_a & stripped_b
        s_union = stripped_a | stripped_b
        side_bonus = len(s_inter) / len(s_union) if s_union else 0.0
    else:
        side_bonus = 0.0

    return jaccard * 0.7 + side_bonus * 0.3


def _get_bone_path(bone) -> list:
    """Return list of bone names from root to this bone (inclusive)."""
    path = []
    b = bone
    while b is not None:
        path.append(b.name)
        b = b.parent
    path.reverse()
    return path


def hierarchy_score(bone_a, bone_b) -> float:
    """Compute hierarchy path similarity between two bones -> [0, 1]."""
    path_a = _get_bone_path(bone_a)
    path_b = _get_bone_path(bone_b)
    depth_a, depth_b = len(path_a), len(path_b)

    # Depth similarity penalty
    depth_sim = 1.0 - min(abs(depth_a - depth_b) * 0.2, 1.0)

    # Weighted average of per-level name similarity (higher weight near the bone itself)
    min_depth = min(depth_a, depth_b)
    if min_depth == 0:
        return depth_sim * 0.4

    total_weight = 0.0
    weighted_sum = 0.0
    for i in range(min_depth):
        weight = i + 1  # increasing weight towards the bone itself
        sim = name_score(path_a[i], path_b[i])
        weighted_sum += sim * weight
        total_weight += weight

    path_name_sim = weighted_sum / total_weight if total_weight > 0 else 0.0
    return path_name_sim * 0.6 + depth_sim * 0.4


def _get_bone_head_local(bone) -> tuple:
    """Get bone head position in armature-local space."""
    # bone.head_local is available in edit mode; for pose bones use bone.bone.head_local
    if hasattr(bone, "bone"):
        return tuple(bone.bone.head_local)
    return tuple(bone.head_local)


def _compute_bbox(armature_obj) -> tuple:
    """Compute bounding box of all bones in local space. Returns (min_coord, max_coord, size)."""
    coords = []
    for b in armature_obj.data.bones:
        coords.append(tuple(b.head_local))
    if not coords:
        return (0, 0, 0), (1, 1, 1), 1.0
    mins = [min(c[i] for c in coords) for i in range(3)]
    maxs = [max(c[i] for c in coords) for i in range(3)]
    size = max(maxs[i] - mins[i] for i in range(3))
    if size < 1e-6:
        size = 1.0
    return tuple(mins), tuple(maxs), size


def spatial_score(bone_a, bone_b, bbox_a, bbox_b) -> float:
    """Compute spatial position similarity -> [0, 1]."""
    pos_a = _get_bone_head_local(bone_a)
    pos_b = _get_bone_head_local(bone_b)

    # Normalize to [0,1] within each armature's bounding box
    norm_a = tuple((pos_a[i] - bbox_a[0][i]) / bbox_a[2] for i in range(3))
    norm_b = tuple((pos_b[i] - bbox_b[0][i]) / bbox_b[2] for i in range(3))

    # Euclidean distance in normalized space
    dist = math.sqrt(sum((norm_a[i] - norm_b[i]) ** 2 for i in range(3)))
    base_sim = max(0.0, 1.0 - dist * 2.0)

    # Left/right mirror tolerance: if X is mirrored but Y/Z are close, give partial credit
    mirror_dist = math.sqrt(
        (norm_a[0] - (1.0 - norm_b[0])) ** 2
        + (norm_a[1] - norm_b[1]) ** 2
        + (norm_a[2] - norm_b[2]) ** 2
    )
    mirror_sim = max(0.0, 1.0 - mirror_dist * 2.0)
    # Take the better of direct and mirror match, but mirror gets 60% credit
    return max(base_sim, mirror_sim * 0.6)


# ===========================================================================
# Preset Learning - Load historical mappings from saved presets
# ===========================================================================

_preset_cache = None       # cache: dict of {(vg_name, bone_name): count}
_preset_vg_index = None   # cache: {vg_name_lower: total_count}
_preset_bone_index = None # cache: {bone_name_lower: total_count}


def _get_preset_dir() -> str:
    """Return the preset directory path (dynamic, not hardcoded)."""
    return os.path.join(
        bpy.utils.resource_path("USER"), "scripts", "presets", "yuinomodtools"
    )


def load_preset_mappings() -> tuple:
    """
    Scan all .py preset files and extract (vg, bone) pair frequency.

    Returns:
        tuple: (pair_counts, vg_index, bone_index)
            pair_counts: {(vg_name_lower, bone_name_lower): occurrence_count}
            vg_index:    {vg_name_lower: total_occurrence_count}
            bone_index:  {bone_name_lower: total_occurrence_count}
    """
    global _preset_cache, _preset_vg_index, _preset_bone_index
    if _preset_cache is not None:
        return _preset_cache, _preset_vg_index, _preset_bone_index

    preset_dir = _get_preset_dir()
    pair_counts = {}
    vg_index = {}
    bone_index = {}

    if not os.path.isdir(preset_dir):
        print(f"[AutoMap] preset dir not found: {preset_dir}")
        _preset_cache = pair_counts
        _preset_vg_index = vg_index
        _preset_bone_index = bone_index
        return pair_counts, vg_index, bone_index

    # Regex with backreference: match item_sub_N.vg and item_sub_N.bone as a pair.
    # Handles other field assignments (e.g. .name) between .vg and .bone lines.
    item_pattern = re.compile(
        r'item_sub_(\d+)\.vg\s*=\s*[\'"]([^\'"]+)[\'"]'
        r'.*?'
        r'item_sub_\1\.bone\s*=\s*[\'"]([^\'"]+)[\'"]',
        re.DOTALL
    )

    file_count = 0
    for fname in os.listdir(preset_dir):
        if not fname.endswith(".py"):
            continue
        filepath = os.path.join(preset_dir, fname)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue

        for _, vg_name, bone_name in item_pattern.findall(content):
            key = (vg_name.lower(), bone_name.lower())
            pair_counts[key] = pair_counts.get(key, 0) + 1
            vg_index[vg_name.lower()] = vg_index.get(vg_name.lower(), 0) + 1
            bone_index[bone_name.lower()] = bone_index.get(bone_name.lower(), 0) + 1

        file_count += 1

    total_pairs = sum(pair_counts.values())
    print(f"[AutoMap] loaded {file_count} presets, {len(pair_counts)} unique pairs, {total_pairs} total mappings")
    _preset_cache = pair_counts
    _preset_vg_index = vg_index
    _preset_bone_index = bone_index
    return pair_counts, vg_index, bone_index


def _invalidate_preset_cache():
    """Call this when presets might have changed (e.g. after saving a preset)."""
    global _preset_cache, _preset_vg_index, _preset_bone_index
    _preset_cache = None
    _preset_vg_index = None
    _preset_bone_index = None


def preset_bonus(src_name: str, tgt_name: str, preset_data: dict,
                 vg_index: dict, bone_index: dict, max_count: int) -> float:
    """
    Return a bonus score [0, 1] based on historical preset data.

    Exact match: scale frequency ratio to [0.6, 1.0].
    Partial match: only when BOTH src and tgt are known (0.10).
      Single-side known → 0.0 (noise prevention: false positives are worse than no match).
    """
    if not preset_data or max_count == 0:
        return 0.0

    key = (src_name.lower(), tgt_name.lower())
    count = preset_data.get(key, 0)
    # Reverse lookup: bone name pairs are direction-agnostic.
    rev_count = preset_data.get((tgt_name.lower(), src_name.lower()), 0)
    count = max(count, rev_count)
    if count > 0:
        freq_score = min(count / max_count, 1.0)
        return 0.6 + freq_score * 0.4

    # Partial match: O(1) index lookup
    src_lower = src_name.lower()
    tgt_lower = tgt_name.lower()
    src_as_vg = vg_index.get(src_lower, 0)
    tgt_as_bone = bone_index.get(tgt_lower, 0)

    if src_as_vg > 0 and tgt_as_bone > 0:
        return 0.10   # both sides known, weak signal
    return 0.0        # only one side known, no bonus (avoid noise)


def auto_match_bones(src_armature_obj, tgt_armature_obj, threshold=0.25):
    """
    Automatically match core bones between two armatures.

    Returns:
        (matched_pairs, unmatched_src, unmatched_tgt)
        matched_pairs: list of (src_bone_name, tgt_bone_name, score)
        unmatched_src: list of src bone names with no match
        unmatched_tgt: list of tgt bone names with no match
    """
    src_bones = [b for b in src_armature_obj.data.bones if is_core_bone(b.name)]
    tgt_bones = [b for b in tgt_armature_obj.data.bones if is_core_bone(b.name)]

    bbox_src = _compute_bbox(src_armature_obj)
    bbox_tgt = _compute_bbox(tgt_armature_obj)

    # Load preset knowledge (now returns 3-tuple)
    preset_data, vg_index, bone_index = load_preset_mappings()
    max_preset_count = max(preset_data.values()) if preset_data else 0

    # Pre-compute bone paths and positions (avoid repeated recursion in double loop)
    src_paths = {b.name: _get_bone_path(b) for b in src_bones}
    tgt_paths = {b.name: _get_bone_path(b) for b in tgt_bones}
    src_positions = {b.name: _get_bone_head_local(b) for b in src_bones}
    tgt_positions = {b.name: _get_bone_head_local(b) for b in tgt_bones}

    print(f"[AutoMap] source core bones: {len(src_bones)}, target core bones: {len(tgt_bones)}")

    # --- Cached internal scoring helpers (use pre-computed data) ---

    def _cached_hierarchy_score(sb, tb):
        path_a = src_paths[sb.name]
        path_b = tgt_paths[tb.name]
        depth_a, depth_b = len(path_a), len(path_b)
        depth_sim = 1.0 - min(abs(depth_a - depth_b) * 0.2, 1.0)
        min_depth = min(depth_a, depth_b)
        if min_depth == 0:
            return depth_sim * 0.4
        total_weight = 0.0
        weighted_sum = 0.0
        for i in range(min_depth):
            weight = i + 1
            sim = name_score(path_a[i], path_b[i])
            weighted_sum += sim * weight
            total_weight += weight
        path_name_sim = weighted_sum / total_weight if total_weight > 0 else 0.0
        return path_name_sim * 0.6 + depth_sim * 0.4

    def _cached_spatial_score(sb, tb):
        pos_a = src_positions[sb.name]
        pos_b = tgt_positions[tb.name]
        norm_a = tuple((pos_a[i] - bbox_src[0][i]) / bbox_src[2] for i in range(3))
        norm_b = tuple((pos_b[i] - bbox_tgt[0][i]) / bbox_tgt[2] for i in range(3))
        dist = math.sqrt(sum((norm_a[i] - norm_b[i]) ** 2 for i in range(3)))
        base_sim = max(0.0, 1.0 - dist * 2.0)
        mirror_dist = math.sqrt(
            (norm_a[0] - (1.0 - norm_b[0])) ** 2
            + (norm_a[1] - norm_b[1]) ** 2
            + (norm_a[2] - norm_b[2]) ** 2
        )
        mirror_sim = max(0.0, 1.0 - mirror_dist * 2.0)
        return max(base_sim, mirror_sim * 0.6)

    # Build score matrix with preset bonus
    scores = []
    for sb in src_bones:
        for tb in tgt_bones:
            ns = name_score(sb.name, tb.name)
            hs = _cached_hierarchy_score(sb, tb)
            ss = _cached_spatial_score(sb, tb)
            pb = preset_bonus(sb.name, tb.name, preset_data, vg_index, bone_index, max_preset_count)
            # Hybrid score: preset knowledge has highest weight
            # Pairs seen in multiple presets get strongest boost
            total = 0.30 * ns + 0.15 * hs + 0.10 * ss + 0.45 * pb
            scores.append((total, sb.name, tb.name))

    # Sort by score descending
    scores.sort(key=lambda x: x[0], reverse=True)

    # Greedy matching
    matched_src = set()
    matched_tgt = set()
    matched_pairs = []

    for score, src_name, tgt_name in scores:
        if score < threshold:
            break
        if src_name in matched_src or tgt_name in matched_tgt:
            continue
        matched_pairs.append((src_name, tgt_name, score))
        matched_src.add(src_name)
        matched_tgt.add(tgt_name)
        print(f"  [Match] {src_name} -> {tgt_name}  score={score:.3f}")

    unmatched_src = [b.name for b in src_bones if b.name not in matched_src]
    unmatched_tgt = [b.name for b in tgt_bones if b.name not in matched_tgt]

    if unmatched_src:
        print(f"  [Unmatched source] {unmatched_src}")
    if unmatched_tgt:
        print(f"  [Unmatched target] {unmatched_tgt}")

    return matched_pairs, unmatched_src, unmatched_tgt


class ListItem(PropertyGroup):
    vg_tip = LANG["ul_list.vg.tip"]
    bone_tip = LANG["ul_list.bone.tip"]

    vg: StringProperty(name="vg", description=vg_tip, default="")
    bone: StringProperty(name="bone", description=bone_tip, default="")


class MY_UL_List(UIList):
    bl_idname = "mainpanel.ul_list"

    def draw_item(
        self, context, layout, data, item, icon, active_data, active_propname, index
    ):
        custom_icon = "FORWARD"
        mesh_obj = context.scene.mesh_pointer
        armature_obj = context.scene.armature_pointer
        if mesh_obj is None or armature_obj is None:
            layout.label(text="--")
            return
        mesh = bpy.data.objects.get(mesh_obj.name)
        armature = bpy.data.objects.get(armature_obj.name)
        if mesh is None or armature is None:
            layout.label(text="--")
            return
        layout.prop_search(item, "vg", mesh, "vertex_groups", text="")
        layout.label(text=item.name, icon=custom_icon)
        layout.prop_search(item, "bone", armature.data, "bones", text="")


class LIST_OT_NewItem(Operator):
    bl_idname = "my_list.new_item"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        context.scene.my_list.add()

        return {"FINISHED"}


class LIST_OT_AddFromBones(Operator):
    bl_idname = "my_list.add_from_bones"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == "ARMATURE" and obj.mode == "POSE"

    def execute(self, context):
        selected = context.selected_pose_bones
        active = context.active_pose_bone

        if not selected or len(selected) < 2:
            Kit.report(LANG["report.need_2_bones"])
            return {"FINISHED"}

        if active is None:
            Kit.report(LANG["report.no_active_bone_pose"])
            return {"FINISHED"}

        target_name = active.name
        source_bones = [b for b in selected if b.name != target_name]

        if not source_bones:
            Kit.report(LANG["report.need_2_bones"])
            return {"FINISHED"}

        my_list = context.scene.my_list
        for src_bone in source_bones:
            item = my_list.add()
            item.vg = src_bone.name
            item.bone = target_name
            print(f"{item.vg} -> {item.bone} added (from bones)")

        self.report({"INFO"}, f"added {len(source_bones)} mapping(s)")
        return {"FINISHED"}


class LIST_OT_ReverseMappings(Operator):
    bl_idname = "my_list.reverse_mappings"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    @classmethod
    def poll(cls, context):
        return len(context.scene.my_list) > 0

    def execute(self, context):
        my_list = context.scene.my_list
        for item in my_list:
            item.vg, item.bone = item.bone, item.vg
        self.report({"INFO"}, LANG["report.reverse_done"])
        return {"FINISHED"}


class LIST_OT_SortByName(Operator):
    bl_idname = "my_list.sort_by_name"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    @classmethod
    def poll(cls, context):
        return len(context.scene.my_list) > 1

    def execute(self, context):
        my_list = context.scene.my_list
        # Collect all items into a list of dicts
        items = [{"vg": item.vg, "bone": item.bone} for item in my_list]
        # Sort alphabetically by vg (source name)
        items.sort(key=lambda x: x["vg"].lower())
        # Write back
        for i, item in enumerate(my_list):
            item.vg = items[i]["vg"]
            item.bone = items[i]["bone"]
        self.report({"INFO"}, "sorted by name")
        return {"FINISHED"}


class LIST_OT_SortByHierarchy(Operator):
    bl_idname = "my_list.sort_by_hierarchy"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    @classmethod
    def poll(cls, context):
        return (len(context.scene.my_list) > 1
                and context.scene.armature_pointer is not None)

    def execute(self, context):
        my_list = context.scene.my_list
        armature_obj = context.scene.armature_pointer
        arm_data = armature_obj.data

        # Build depth lookup: bone_name -> hierarchy depth
        def get_depth(bone_name):
            bone = arm_data.bones.get(bone_name)
            if bone is None:
                return 999
            depth = 0
            b = bone
            while b.parent is not None:
                depth += 1
                b = b.parent
            return depth

        # Collect items with depth info
        items = []
        for item in my_list:
            depth = get_depth(item.bone)
            items.append({"vg": item.vg, "bone": item.bone, "depth": depth})

        # Sort by depth first (root bones first), then by name within same depth
        items.sort(key=lambda x: (x["depth"], x["bone"].lower()))

        # Write back
        for i, item in enumerate(my_list):
            item.vg = items[i]["vg"]
            item.bone = items[i]["bone"]
        self.report({"INFO"}, "sorted by hierarchy")
        return {"FINISHED"}


class AutoMapBones(Operator):
    bl_idname = "my_list.auto_map"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        scene = context.scene
        src_obj = scene.auto_src_armature
        tgt_obj = scene.auto_tgt_armature

        # Refresh preset cache each time for latest data
        _invalidate_preset_cache()

        # Validate inputs
        if src_obj is None or tgt_obj is None:
            Kit.report(LANG["report.need_2_armatures"])
            return {"FINISHED"}
        if src_obj == tgt_obj:
            Kit.report(LANG["report.need_2_armatures"])
            return {"FINISHED"}

        # Resolve actual objects from bpy.data
        src_arm = bpy.data.objects.get(src_obj.name)
        tgt_arm = bpy.data.objects.get(tgt_obj.name)
        if src_arm is None or tgt_arm is None:
            Kit.report(LANG["report.need_2_armatures"])
            return {"FINISHED"}

        matched, unmatched_src, unmatched_tgt = auto_match_bones(src_arm, tgt_arm)

        if not matched:
            Kit.report(LANG["report.no_match"])
            return {"FINISHED"}

        # Append results to my_list (do not clear existing entries)
        my_list = scene.my_list
        for src_name, tgt_name, score in matched:
            item = my_list.add()
            item.vg = src_name
            item.bone = tgt_name

        msg = (
            f"{LANG['report.auto_map_done']}: "
            f"{len(matched)} matched, "
            f"{len(unmatched_src)} unmatched source, "
            f"{len(unmatched_tgt)} unmatched target"
        )
        self.report({"INFO"}, msg)
        print(f"[AutoMap] {msg}")
        return {"FINISHED"}


class LIST_OT_DeleteItem(Operator):
    bl_idname = "my_list.delete_item"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    @classmethod
    def poll(cls, context):
        return context.scene.my_list

    def execute(self, context):
        my_list = context.scene.my_list
        index = context.scene.list_index

        my_list.remove(index)
        context.scene.list_index = min(max(0, index - 1), len(my_list) - 1)

        return {"FINISHED"}


class menu_presets(Menu):
    bl_idname = "menu_presets"
    bl_label = LANG[bl_idname]
    bl_icon = "PRESET"

    preset_subdir = "yuinomodtools"
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class add_presets(AddPresetBase, Operator):
    bl_idname = "menu.add_preset"
    bl_sub_idname = "presets"
    bl_label = ""
    bl_description = LANG[bl_sub_idname + ".tip"]
    preset_menu = "menu_presets"

    # variable used for all preset values
    preset_defines = ["s = bpy.context.scene"]

    # properties to store in the preset
    preset_values = ["s.my_list"]

    # where to store the preset
    preset_subdir = "yuinomodtools"


class CreditPanel(Panel):
    bl_idname = "creditpanel"
    bl_label = LANG[bl_idname + ".label"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'MappingTools'

    def draw(self, context):
        layout = self.layout
        name = "0w0-Yui"
        op = layout.operator("wm.url_open", text=LANG["creditpanel.github"])
        op.url = "https://github.com/0w0-Yui"
        op1 = layout.operator("wm.url_open", text=LANG["creditpanel.bilibili"])
        op1.url = "https://space.bilibili.com/276237700"


class RemoveUnused(Operator):
    bl_idname = "miscpanel.remove_unused"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        object = bpy.context.object
        skeleton = object.find_armature()
        if object.type != "MESH":
            Kit.report(LANG["report.no_active_mesh"])
            return {"FINISHED"}
        if skeleton is None:
            Kit.report(LANG["report.no_armature"])
            return {"FINISHED"}
        if object.type == "MESH" and len(object.vertex_groups) > 0:
            # 先收集需要移除的索引，再倒序删除，避免遍历中修改集合
            remove_indices = []
            for idx, vGroup in enumerate(object.vertex_groups):
                if skeleton.data.bones.get(vGroup.name) is None:
                    print(f"{vGroup.name} removed")
                    remove_indices.append(idx)
            for idx in reversed(remove_indices):
                object.vertex_groups.remove(object.vertex_groups[idx])
        return {"FINISHED"}


class RemoveEmpty(Operator):
    bl_idname = "miscpanel.remove_empty"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        obj = bpy.context.object
        if obj.type != "MESH":
            Kit.report(LANG["report.no_active_mesh"])
            return {"FINISHED"}
        try:
            vertex_groups = obj.vertex_groups
            groups = {r: None for r in range(len(vertex_groups))}

            for vert in obj.data.vertices:
                for vg in vert.groups:
                    i = vg.group
                    if i in groups:
                        del groups[i]

            lis = [k for k in groups]
            lis.sort(reverse=True)
            for i in lis:
                print(f"{vertex_groups[i].name} removed")
                vertex_groups.remove(vertex_groups[i])
        except Exception as e:
            print(e)
        return {"FINISHED"}


class MergeTextureMaterial(Operator):
    bl_idname = "miscpanel.merge_mats"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        obj = bpy.context.object
        bpy.ops.object.material_slot_remove_unused()
        mat_dict = {}
        if obj.type == "MESH":
            for mat_slot in obj.material_slots:
                if mat_slot.material:
                    if mat_slot.material.node_tree:
                        # print("material:" + str(mat_slot.material.name))
                        for x in mat_slot.material.node_tree.nodes:
                            if x.type == "TEX_IMAGE":
                                # print(" texture: "+str(x.image.name))
                                if mat_slot.slot_index in mat_dict:
                                    mat_dict[mat_slot.slot_index].append(x.image.name)
                                else:
                                    mat_dict[mat_slot.slot_index] = [x.image.name]
        # print(mat_dict)
        flipped = {}
        for key, value in mat_dict.items():
            value = tuple(value)
            value = tuple(
                [item for index, item in enumerate(value) if item not in value[:index]]
            )
            if value not in flipped:
                flipped[value] = [key]
            else:
                flipped[value].append(key)

        # print(flipped)
        # print(flipped.items())

        data_face = {}

        print("getting polygons data")
        polygons = obj.data.polygons
        for f in polygons:
            index_face = f
            index_mat = f.material_index
            if index_mat in data_face:
                data_face[index_mat].append(index_face)
            else:
                data_face[index_mat] = [index_face]
            # print("face", f.index, "material_index", f.material_index)

        # print(data_face)
        # print(flipped)
        # return {"FINISHED"}

        for key, value in flipped.items():
            # print(key, value)
            for index in value[1:]:
                print(f"{index} merge into {value[0]}")
                # continue
                for face in data_face[index]:
                    # print(faces)
                    face.material_index = value[0]
        bpy.ops.object.material_slot_remove_unused()

        return {"FINISHED"}


class SelectSeams(Operator):
    bl_idname = "miscpanel.select_seams"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        obj = bpy.context.active_object
        if obj.type != "MESH":
            Kit.report(LANG["report.active_not_mesh"])
            return {"FINISHED"}
        bpy.ops.object.mode_set(mode="OBJECT")
        for e in obj.data.edges:
            e.select = e.use_seam
        return {"FINISHED"}


class MiscPanel(Panel):
    bl_idname = "miscpanel"
    bl_label = LANG[bl_idname + ".label"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'MappingTools'

    def draw(self, context):
        layout = self.layout
        layout.operator(RemoveEmpty.bl_idname, text=RemoveEmpty.bl_label)
        layout.operator(RemoveUnused.bl_idname, text=RemoveUnused.bl_label)
        layout.operator(
            MergeTextureMaterial.bl_idname, text=MergeTextureMaterial.bl_label
        )
        layout.operator(SelectSeams.bl_idname, text=SelectSeams.bl_label)


class OpenPresetFolder(Operator):
    bl_idname = "presets.open_folder"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        preset_dir = os.path.join(
            bpy.utils.resource_path("USER"), "scripts", "presets", "yuinomodtools"
        )
        # 确保目录存在
        os.makedirs(preset_dir, exist_ok=True)
        bpy.ops.wm.path_open(filepath=preset_dir)
        return {"FINISHED"}


class MyAddonPanel(Panel):
    bl_idname = "mainpanel"
    bl_label = LANG[bl_idname + ".label"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = 'XQFA'

    @classmethod
    def poll(cls, context):
        return getattr(context.scene, 'active_xbone_subpanel', '') == 'MappingTools'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        armature = scene.armature_pointer
        mesh = scene.mesh_pointer

        box = layout.box()
        box.label(text=LANG[self.bl_idname + ".armature_pointer"])
        box.prop(scene, "armature_pointer", text="", icon="ARMATURE_DATA")
        box.label(text=LANG[self.bl_idname + ".mesh_pointer"])
        box.prop(scene, "mesh_pointer", text="", icon="MESH_DATA")

        msg = Kit.check_pointer(mesh, armature)

        if msg == "":
            row = box.row(align=True)
            row.operator(StartAssign.bl_idname, text=StartAssign.bl_label)
            row.operator(Stop.bl_idname, text=Stop.bl_label)

            box1 = layout.box()

            box1.label(text=context.scene.vertex_group_string)

            row = box1.row(align=True)
            row.operator(Next.bl_idname, text=Next.bl_label)
            row.operator(Skip.bl_idname, text=Skip.bl_label)
            box1.prop(scene, "is_mid_start")

            row = box1.row()
            row.template_list(
                MY_UL_List.bl_idname, "The_List", scene, "my_list", scene, "list_index"
            )

            row1 = box1.row(align=True)
            row1.operator(LIST_OT_NewItem.bl_idname, text=LIST_OT_NewItem.bl_label)
            row1.operator(
                LIST_OT_DeleteItem.bl_idname, text=LIST_OT_DeleteItem.bl_label
            )

            row2 = box1.row(align=True)
            row2.operator(
                LIST_OT_AddFromBones.bl_idname, text=LIST_OT_AddFromBones.bl_label
            )
            row2.operator(
                LIST_OT_ReverseMappings.bl_idname,
                text=LIST_OT_ReverseMappings.bl_label,
            )

            row_sort = box1.row(align=True)
            row_sort.operator(
                LIST_OT_SortByName.bl_idname, text=LIST_OT_SortByName.bl_label, icon="SORTALPHA"
            )
            row_sort.operator(
                LIST_OT_SortByHierarchy.bl_idname,
                text=LIST_OT_SortByHierarchy.bl_label, icon="OUTLINER",
            )

            box1.operator(Done.bl_idname, text=Done.bl_label)
            box1.prop(scene, "is_merging")

            # 自动骨骼映射
            box_auto = layout.box()
            box_auto.label(text=LANG["auto_map.label"], icon="BONE_DATA")
            box_auto.prop(scene, "auto_src_armature", text=LANG["auto_map.src"], icon="ARMATURE_DATA")
            box_auto.prop(scene, "auto_tgt_armature", text=LANG["auto_map.tgt"], icon="ARMATURE_DATA")
            box_auto.operator(AutoMapBones.bl_idname, text=AutoMapBones.bl_label, icon="FILE_REFRESH")

            box2 = layout.box()
            row = box2.row()
            row.menu(
                menu_presets.bl_idname,
                text=menu_presets.bl_label,
                icon=menu_presets.bl_icon,
            )
            row1 = box2.row(align=True)
            row1.operator(
                add_presets.bl_idname, text=LANG[add_presets.bl_sub_idname + ".save"]
            )
            row1.operator(
                add_presets.bl_idname, text=LANG[add_presets.bl_sub_idname + ".delete"]
            ).remove_active = True
            row1 = box2.row(align=True)
            row1.operator(OpenPresetFolder.bl_idname, text=OpenPresetFolder.bl_label)

            # 导出到骨骼工具
            box3 = layout.box()
            box3.label(text="导出到骨骼工具", icon="EXPORT")
            if hasattr(scene, 'xbone_csv_data') and scene.xbone_csv_data:
                box3.label(text="骨骼工具已有CSV数据，导出将覆盖", icon="INFO")
            row = box3.row(align=True)
            row.prop(scene, "export_key_col", text="源列")
            row.prop(scene, "export_val_col", text="目标列")
            box3.operator(ExportToCSVData.bl_idname, text="从映射列表导出", icon="FILE_TICK")
        else:
            layout.label(text=msg, icon="ERROR")


class Kit(Operator):
    def check_pointer(obj, armature):
        if obj is None or armature is None:
            return LANG["report.no_active"]
        arm_obj = bpy.data.objects.get(armature.name)
        if arm_obj is None:
            return f'armature "{armature.name}" not found in scene'
        # 遍历每个修改器
        for modifier in obj.modifiers:
            # 判断修改器是否是骨骼修改器
            if modifier.type == "ARMATURE":
                if modifier.object == arm_obj:
                    return ""
        return f'no modifier for "{armature.name}" found in "{obj.name}"'

    def add_armature_modifier(obj, armature):
        obj = bpy.context.selected_objects[0]
        # 遍历每个修改器
        for modifier in obj.modifiers:
            # 判断修改器是否是骨骼修改器
            if modifier.type == "ARMATURE":
                # 移除修改器
                obj.modifiers.remove(modifier)
        armature_modifier = obj.modifiers.new(name="Armature", type="ARMATURE")
        armature_modifier.object = bpy.data.objects[armature.name]

    def select(obj):
        bpy.data.objects[obj.name].select_set(True)

    def mode_set(mode):
        bpy.ops.object.mode_set(mode=mode)

    def report(message, title="INFO", icon="INFO"):
        def draw(self, context):
            self.layout.label(text=message)

        bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

    def get_all_vg(obj):
        vg_list = []
        for vg in obj.vertex_groups:
            # 获取顶点组的名称和索引
            vg_list.append({"name": vg.name, "index": vg.index})
        return vg_list

    def select_vg(name):
        bpy.ops.object.vertex_group_set_active(group=name)

    def update_label_vg(string):
        context = bpy.context
        context.scene.vertex_group_string = (
            LANG["mainpanel.vertex_group_string"] + f"{string}"
        )
        return context.scene.vertex_group_string

    def is_mesh(scene, obj):
        return obj.type == "MESH"

    def is_armature(scene, obj):
        return obj.type == "ARMATURE"


class StartAssign(Operator):
    bl_idname = "mainpanel.start_assignment"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        if bpy.context.object.mode != "WEIGHT_PAINT":
            Kit.report(LANG["report.not_weight_mode"])
            return {"FINISHED"}
        vg_list = []
        selected_mesh = context.scene.mesh_pointer
        scene = context.scene
        object = context.object
        skeleton = object.find_armature()
        print("start quick assign")
        if object.type != "MESH":
            Kit.report(LANG["report.no_active_mesh"])
            return {"FINISHED"}
        if skeleton is None:
            Kit.report(LANG["report.no_armature"])
            return {"FINISHED"}
        if scene.is_mid_start:
            bpy.ops.object.vertex_group_sort(sort_type="BONE_HIERARCHY")
            if object.type == "MESH" and len(object.vertex_groups) > 0:
                for vGroup in object.vertex_groups:
                    if skeleton.data.bones.get(vGroup.name) is None:
                        scene.assign_index = object.vertex_groups.find(vGroup.name)
                        break
        else:
            scene.assign_index = 0
        vg_list = Kit.get_all_vg(selected_mesh)
        Kit.select_vg(vg_list[scene.assign_index]["name"])
        Kit.update_label_vg(vg_list[scene.assign_index]["name"])
        return {"FINISHED"}


class Next(Operator):
    bl_idname = "mainpanel.next"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        if bpy.context.object.mode != "WEIGHT_PAINT":
            Kit.report(LANG["report.not_weight_mode"])
            return {"FINISHED"}
        selected_mesh = context.scene.mesh_pointer
        selected_bone = bpy.context.selected_pose_bones
        list = context.scene.my_list
        index = context.scene.assign_index
        vg_list = Kit.get_all_vg(selected_mesh)
        if len(selected_bone) == 0:
            Kit.report(LANG["report.no_active_bone"])
            return {"FINISHED"}
        if index >= 0 and index < len(vg_list):
            item = list.add()
            item.vg = vg_list[index]["name"]
            item.bone = selected_bone[0].name
            print(f"{item.vg} -> {item.bone} added")
            index += 1
        if index < len(vg_list):
            Kit.select_vg(vg_list[index]["name"])
            Kit.update_label_vg(vg_list[index]["name"])
        else:
            Kit.update_label_vg(str(None))
        context.scene.assign_index = index
        return {"FINISHED"}


class Skip(Operator):
    bl_idname = "mainpanel.skip"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        if bpy.context.object.mode != "WEIGHT_PAINT":
            Kit.report(LANG["report.not_weight_mode"])
            return {"FINISHED"}
        selected_mesh = context.scene.mesh_pointer
        index = context.scene.assign_index
        vg_list = Kit.get_all_vg(selected_mesh)
        if index >= 0 and index < len(vg_list):
            name = vg_list[index]["name"]
            print(f"{name} skipped")
            index += 1
        if index < len(vg_list):
            Kit.select_vg(vg_list[index]["name"])
            Kit.update_label_vg(vg_list[index]["name"])
        else:
            Kit.update_label_vg(str(None))
        context.scene.assign_index = index
        return {"FINISHED"}


class Stop(Operator):
    bl_idname = "mainpanel.stop"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        index = 0
        Kit.update_label_vg(str(None))
        context.scene.assign_index = index
        print("stop quick assign")
        return {"FINISHED"}


class Done(Operator):
    bl_idname = "mainpanel.done"
    bl_label = LANG[bl_idname]
    bl_description = LANG[bl_idname + ".tip"]

    def execute(self, context):
        print("starting...")
        if bpy.context.object.mode != "WEIGHT_PAINT":
            Kit.report(LANG["report.not_weight_mode"])
            return {"FINISHED"}
        scene = context.scene
        mesh = bpy.data.objects[context.scene.mesh_pointer.name]
        my_list = context.scene.my_list
        vg_list = Kit.get_all_vg(mesh)
        vertex_groups = mesh.vertex_groups
        duplicates_dict = {}
        added_list = []
        # 用临时列表收集需要追加的项，避免迭代 my_list 时同时修改它
        pending_merge_items = []
        for i in my_list:
            for vg in vg_list:
                if vg["name"] == i.bone:
                    old_name = vg["name"]
                    if scene.is_merging:
                        if old_name not in added_list and i.vg != i.bone:
                            pending_merge_items.append({"vg": old_name, "bone": i.bone})
                            added_list.append(old_name)
                        continue
                    print(
                        f"Vertex Group: {old_name} and Bone: {i.bone} is the same, Please change the vertex group name"
                    )
                    Kit.report(LANG["report.name_collision"])
                    return {"FINISHED"}
        # 迭代结束后统一追加到 my_list
        for pending in pending_merge_items:
            item = my_list.add()
            item.vg = pending["vg"]
            item.bone = pending["bone"]

        for i, item in enumerate(my_list):
            if item.bone in duplicates_dict:
                duplicates_dict[item.bone].append(i)
            else:
                duplicates_dict[item.bone] = [i]

        # 从字典中提取出所有重复的键值对，即重复的bone属性的值和它们的位置
        duplicates = [[k, v] for k, v in duplicates_dict.items() if len(v) > 1]

        for dup in duplicates:
            merged_group_name = dup[0]
            my_list_index = dup[1]
            vertex_group_names = []
            for i in my_list_index:
                is_exist = False
                for vg in vg_list:
                    if my_list[i].vg == vg["name"]:
                        is_exist = True
                if not is_exist:
                    print(f'No vertex group found with name "{[my_list[i].vg]}"')
                    continue
                vertex_group_names.append(my_list[i].vg)

            if merged_group_name in vertex_group_names:
                vertex_group = vertex_groups.get(merged_group_name)
                new_suffix = ".old"
                new_name = merged_group_name + new_suffix
                if vertex_group is not None:
                    vertex_group.name = new_name
                    vertex_group_names[vertex_group_names.index(merged_group_name)] = (
                        new_name
                    )
                    print(f"{[merged_group_name]} -> {new_name} renamed")

            vertex_group = mesh.vertex_groups.new(name=merged_group_name)
            # vertex_group += merging_groups

            vertex_weights = {}
            for vert in mesh.data.vertices:
                if len(vert.groups):
                    for item in vert.groups:
                        vg = mesh.vertex_groups[item.group]
                        if vg.name in vertex_group_names:
                            if vert.index in vertex_weights:
                                vertex_weights[vert.index] += vg.weight(vert.index)
                            else:
                                vertex_weights[vert.index] = vg.weight(vert.index)
                            if vertex_weights[vert.index] > 1.0:
                                vertex_weights[vert.index] = 1.0

            # add the values to the group
            for key, value in vertex_weights.items():
                vertex_group.add([key], value, "REPLACE")  # 'ADD','SUBTRACT'
            print(f"{[vertex_group_names]} -> {merged_group_name} renamed")
        # print(f"{vg_list}")
        for item in my_list:
            is_dup = False
            for dup in duplicates:
                if item.bone == dup[0]:
                    is_dup = True
            if is_dup:
                continue
            old_name = item.vg
            new_name = item.bone
            is_exist = False
            for vg in vg_list:
                if old_name == vg["name"]:
                    is_exist = True
            if not is_exist:
                print(f'No vertex group found with name "{[old_name]}"')
                continue
            Kit.select_vg(old_name)
            bpy.ops.object.vertex_group_copy()
            vertex_groups[-1].name = new_name
            print(f"{[old_name]} -> {new_name} renamed")
        Kit.report(LANG["report.done"])
        print("done!")
        return {"FINISHED"}


class ExportToCSVData(Operator):
    bl_idname = "my_list.export_to_csv"
    bl_label = "从映射列表导出"
    bl_description = "将当前映射列表导出为骨骼工具可用的CSV数据格式"

    def execute(self, context):
        scene = context.scene
        my_list = scene.my_list
        if len(my_list) == 0:
            self.report({'WARNING'}, "映射列表为空，无法导出")
            return {'CANCELLED'}

        key_col = scene.export_key_col
        val_col = scene.export_val_col
        max_col = max(key_col, val_col)

        # 构造与 CSV 导入兼容的表格数据
        # 第一行是标题行
        header = [""] * (max_col + 1)
        header[key_col] = "source"
        header[val_col] = "target"
        rows = [header]

        exported = 0
        for item in my_list:
            if item.vg and item.bone:
                row = [""] * (max_col + 1)
                row[key_col] = item.vg
                row[val_col] = item.bone
                rows.append(row)
                exported += 1

        # 写入与骨骼工具兼容的 JSON 字符串
        scene["xbone_csv_data"] = json.dumps(rows)

        self.report({'INFO'}, f"已导出 {exported} 条映射到骨骼工具")
        print(f"[ExportToCSVData] exported {exported} items, key_col={key_col}, val_col={val_col}")
        return {'FINISHED'}


classes = (
    MyAddonPanel,
    StartAssign,
    Next,
    Done,
    ListItem,
    MY_UL_List,
    LIST_OT_NewItem,
    LIST_OT_DeleteItem,
    menu_presets,
    add_presets,
    RemoveUnused,
    RemoveEmpty,
    MergeTextureMaterial,
    SelectSeams,
    MiscPanel,
    CreditPanel,
    OpenPresetFolder,
    Stop,
    Skip,
    ExportToCSVData,
    LIST_OT_AddFromBones,
    LIST_OT_ReverseMappings,
    LIST_OT_SortByName,
    LIST_OT_SortByHierarchy,
    AutoMapBones,
)


def register():
    for cls in classes:
        register_class(cls)

    Scene.armature_pointer = PointerProperty(type=Object, poll=Kit.is_armature)
    Scene.mesh_pointer = PointerProperty(type=Object, poll=Kit.is_mesh)
    Scene.my_list = CollectionProperty(type=ListItem)
    Scene.list_index = IntProperty(name="list index", default=0)
    Scene.assign_index = IntProperty(name="global index", default=-1)
    Scene.vertex_group_string = StringProperty(
        name="vertex_group_string",
        default=LANG["mainpanel.vertex_group_string"] + str(None),
    )
    Scene.is_merging = BoolProperty(
        name=LANG["mainpanel.ismerging"],
        description=LANG["mainpanel.ismerging" + ".tip"],
        default=False,
    )
    Scene.is_mid_start = BoolProperty(
        name=LANG["mainpanel.is_mid_start"],
        description=LANG["mainpanel.is_mid_start" + ".tip"],
        default=False,
    )
    Scene.export_key_col = IntProperty(
        name="源列",
        description="导出时源骨骼名称所在的列索引",
        default=0,
        min=0,
    )
    Scene.export_val_col = IntProperty(
        name="目标列",
        description="导出时目标骨骼名称所在的列索引",
        default=1,
        min=0,
    )
    Scene.auto_src_armature = PointerProperty(type=Object, poll=Kit.is_armature)
    Scene.auto_tgt_armature = PointerProperty(type=Object, poll=Kit.is_armature)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.armature_pointer
    del Scene.mesh_pointer
    del Scene.my_list
    del Scene.list_index
    del Scene.assign_index
    del Scene.vertex_group_string
    del Scene.is_merging
    del Scene.is_mid_start
    del Scene.export_key_col
    del Scene.export_val_col
    del Scene.auto_src_armature
    del Scene.auto_tgt_armature
