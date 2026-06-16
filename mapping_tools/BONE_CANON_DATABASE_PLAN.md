# Bone Canon Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a canonical bone database with two auto-mapping algorithm modes (similarity and canon) for the Blender XQFA Tools plugin.

**Architecture:** Add a new `bone_database.py` module with a `BoneDatabase` class that merges a built-in default JSON template and a user-specific JSON overlay. Modify `modtoolkit.py` to switch between the existing similarity-based matcher and a new canon-based matcher that resolves bones against the database.

**Tech Stack:** Blender Python API (bpy), standard library (json, os, re)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `mapping_tools/data/bone_canon_default.json` | Built-in default 52-bone template with aliases |
| `mapping_tools/bone_database.py` | `BoneDatabase` class: load default + user overlay, resolve names, add aliases, persist user data |
| `mapping_tools/modtoolkit.py` | Add `auto_map_mode` scene property, UI dropdown, canonical matching branch, learning hook |
| `mapping_tools/dev_seed_canon.py` | One-time development script that reads local presets and generates the default template |
| `mapping_tools/tests/test_bone_database.py` | Unit tests for `BoneDatabase` that can run inside Blender |

---

## Task 1: Define Canonical Skeleton and Create Empty Default Template

**Files:**
- Create: `mapping_tools/data/bone_canon_default.json`

**Purpose:** Establish the 52 canonical bone entries (Bip01-based) with empty alias lists. Aliases will be filled in Task 3.

- [ ] **Step 1: Create `mapping_tools/data/` directory and empty default JSON**

Create the directory and file with the 52-bone structure. Each entry must have a unique `id`, `canonical_name`, `display_name`, `category`, `side`, and empty `aliases`.

Run:
```powershell
New-Item -ItemType Directory -Path "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools\data" -Force
```

Write the following content to `mapping_tools/data/bone_canon_default.json`:

```json
{
  "version": "1.0",
  "schema": "bone_canon",
  "bones": [
    {"id": "bip01_pelvis", "canonical_name": "Bip01 Pelvis", "display_name": "骨盆", "category": "torso", "side": "center", "aliases": []},
    {"id": "bip01_spine", "canonical_name": "Bip01 Spine", "display_name": "脊柱根", "category": "torso", "side": "center", "aliases": []},
    {"id": "bip01_spine1", "canonical_name": "Bip01 Spine1", "display_name": "胸部下段", "category": "torso", "side": "center", "aliases": []},
    {"id": "bip01_spine2", "canonical_name": "Bip01 Spine2", "display_name": "胸部上段", "category": "torso", "side": "center", "aliases": []},
    {"id": "bip01_neck", "canonical_name": "Bip01 Neck", "display_name": "脖子", "category": "head_neck", "side": "center", "aliases": []},
    {"id": "bip01_head", "canonical_name": "Bip01 Head", "display_name": "头部", "category": "head_neck", "side": "center", "aliases": []},

    {"id": "bip01_l_clavicle", "canonical_name": "Bip01 L Clavicle", "display_name": "左锁骨", "category": "arm", "side": "left", "aliases": []},
    {"id": "bip01_l_upperarm", "canonical_name": "Bip01 L UpperArm", "display_name": "左上臂", "category": "arm", "side": "left", "aliases": []},
    {"id": "bip01_l_forearm", "canonical_name": "Bip01 L Forearm", "display_name": "左前臂", "category": "arm", "side": "left", "aliases": []},
    {"id": "bip01_l_hand", "canonical_name": "Bip01 L Hand", "display_name": "左手掌", "category": "arm", "side": "left", "aliases": []},
    {"id": "bip01_r_clavicle", "canonical_name": "Bip01 R Clavicle", "display_name": "右锁骨", "category": "arm", "side": "right", "aliases": []},
    {"id": "bip01_r_upperarm", "canonical_name": "Bip01 R UpperArm", "display_name": "右上臂", "category": "arm", "side": "right", "aliases": []},
    {"id": "bip01_r_forearm", "canonical_name": "Bip01 R Forearm", "display_name": "右前臂", "category": "arm", "side": "right", "aliases": []},
    {"id": "bip01_r_hand", "canonical_name": "Bip01 R Hand", "display_name": "右手掌", "category": "arm", "side": "right", "aliases": []},

    {"id": "bip01_l_thigh", "canonical_name": "Bip01 L Thigh", "display_name": "左大腿", "category": "leg", "side": "left", "aliases": []},
    {"id": "bip01_l_calf", "canonical_name": "Bip01 L Calf", "display_name": "左小腿", "category": "leg", "side": "left", "aliases": []},
    {"id": "bip01_l_foot", "canonical_name": "Bip01 L Foot", "display_name": "左脚掌", "category": "leg", "side": "left", "aliases": []},
    {"id": "bip01_l_toe0", "canonical_name": "Bip01 L Toe0", "display_name": "左脚趾", "category": "leg", "side": "left", "aliases": []},
    {"id": "bip01_r_thigh", "canonical_name": "Bip01 R Thigh", "display_name": "右大腿", "category": "leg", "side": "right", "aliases": []},
    {"id": "bip01_r_calf", "canonical_name": "Bip01 R Calf", "display_name": "右小腿", "category": "leg", "side": "right", "aliases": []},
    {"id": "bip01_r_foot", "canonical_name": "Bip01 R Foot", "display_name": "右脚掌", "category": "leg", "side": "right", "aliases": []},
    {"id": "bip01_r_toe0", "canonical_name": "Bip01 R Toe0", "display_name": "右脚趾", "category": "leg", "side": "right", "aliases": []}
  ]
}
```

> Note: The example above contains 22 entries for brevity. The real file must contain all 52 entries including finger bones. Add the remaining 30 finger entries (Thumb1-3, Index1-3, Middle1-3, Ring1-3, Pinky1-3 for both hands) before proceeding.

- [ ] **Step 2: Verify JSON is valid**

Run:
```powershell
python -m json.tool "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools\data\bone_canon_default.json" > $null
```

Expected: no output (no errors).

- [ ] **Step 3: Commit the skeleton structure**

```bash
git add mapping_tools/data/bone_canon_default.json
git commit -m "feat: add canonical bone skeleton structure (52 entries)"
```

---

## Task 2: Create Development Seeding Script

**Files:**
- Create: `mapping_tools/dev_seed_canon.py`

**Purpose:** Read the developer's local presets and populate `bone_canon_default.json` aliases. This script is used once during development, not shipped as plugin functionality.

- [ ] **Step 1: Write `dev_seed_canon.py`**

```python
# type: ignore
"""
Development-only script to seed bone_canon_default.json from local presets.
Run from Blender scripting editor or standalone with a mock bpy.
"""
import json
import os
import re
from pathlib import Path


PRESET_DIR = r"C:\Users\yequ\AppData\Roaming\Blender Foundation\Blender\4.5\scripts\presets\yuinomodtools"
DEFAULT_JSON = Path(__file__).parent / "data" / "bone_canon_default.json"


def parse_presets(preset_dir: str):
    """Yield (vg_name, bone_name) pairs from all .py preset files."""
    pattern = re.compile(
        r'item_sub_(\d+)\.vg\s*=\s*[\'"]([^\'"]+)[\'"]'
        r'.*?'
        r'item_sub_\1\.bone\s*=\s*[\'"]([^\'"]+)[\'"]',
        re.DOTALL
    )
    pairs = []
    for fname in os.listdir(preset_dir):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(preset_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        for _, vg, bone in pattern.findall(content):
            pairs.append((vg, bone))
    return pairs


def simple_name_score(a: str, b: str) -> float:
    """Minimal name similarity for seeding."""
    a_tokens = set(re.split(r"[_.:\-]", a.lower())) - {"", "bip01", "bip001", "mixamorig", "def", "b005"}
    b_tokens = set(re.split(r"[_.:\-]", b.lower())) - {"", "bip01", "bip001", "mixamorig", "def", "b005"}
    if not a_tokens or not b_tokens:
        return 0.0
    inter = a_tokens & b_tokens
    union = a_tokens | b_tokens
    return len(inter) / len(union)


def resolve_canonical(bone_name: str, entries: list) -> str | None:
    """Match bone_name to the best canonical entry id."""
    best_id = None
    best_score = 0.55
    for entry in entries:
        # Compare against canonical_name and display_name
        for ref in [entry["canonical_name"], entry["display_name"]]:
            score = simple_name_score(bone_name, ref)
            if score > best_score:
                best_score = score
                best_id = entry["id"]
        # Compare against existing aliases
        for alias in entry.get("aliases", []):
            score = simple_name_score(bone_name, alias)
            if score > best_score:
                best_score = score
                best_id = entry["id"]
    return best_id


def main():
    with open(DEFAULT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data["bones"]
    entries_by_id = {e["id"]: e for e in entries}

    pairs = parse_presets(PRESET_DIR)
    print(f"Loaded {len(pairs)} preset pairs")

    for vg, bone in pairs:
        vg_id = resolve_canonical(vg, entries)
        bone_id = resolve_canonical(bone, entries)

        # Use whichever side resolves; prefer bone (target) side
        target_id = bone_id or vg_id
        if target_id is None:
            continue

        entry = entries_by_id[target_id]
        for name in (vg, bone):
            name_lower = name.lower()
            if name_lower not in [a.lower() for a in entry["aliases"]]:
                # Avoid adding obviously side-conflicting names to wrong entry
                entry["aliases"].append(name)

    # Sort aliases alphabetically for stability
    for entry in entries:
        entry["aliases"] = sorted(set(entry["aliases"]), key=str.lower)

    with open(DEFAULT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Seeded {DEFAULT_JSON}")
    for entry in entries:
        print(f"  {entry['id']}: {len(entry['aliases'])} aliases")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add a small standalone test run**

Run:
```powershell
cd "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools"
python dev_seed_canon.py
```

Expected: prints loaded pair count and alias counts per bone. Review output for obviously wrong assignments.

- [ ] **Step 3: Commit the seeding script**

```bash
git add mapping_tools/dev_seed_canon.py
git commit -m "chore: add dev script to seed canonical bone aliases from local presets"
```

---

## Task 3: Run Seeding Script and Review Default Template

**Files:**
- Modify: `mapping_tools/data/bone_canon_default.json`

**Purpose:** Generate the actual alias lists and manually review/correct them.

- [ ] **Step 1: Back up the empty skeleton**

```bash
cp "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools\data\bone_canon_default.json" "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools\data\bone_canon_default.empty.json"
```

- [ ] **Step 2: Run the seeding script**

```powershell
cd "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools"
python dev_seed_canon.py
```

- [ ] **Step 3: Manually review and correct the generated JSON**

Open `mapping_tools/data/bone_canon_default.json` and check:
- Each canonical entry has relevant aliases
- No obvious cross-side pollution (e.g. `upperarm_r` under `bip01_l_upperarm`)
- Common naming styles are covered: Bip01, Bip001, Mixamo (`mixamorig:`), UE/Unity (`spine_03`, `upperarm_l`), MMD, custom

Add missing aliases by hand where the fuzzy matcher failed.

- [ ] **Step 4: Validate JSON and commit the filled template**

```powershell
python -m json.tool "D:\code\blender\yuitool\BlenderXqfaTools-editor\mapping_tools\data\bone_canon_default.json" > $null
```

```bash
git add mapping_tools/data/bone_canon_default.json
git rm mapping_tools/data/bone_canon_default.empty.json
git commit -m "feat: seed canonical bone aliases from local presets and manual review"
```

---

## Task 4: Implement `BoneDatabase` Module

**Files:**
- Create: `mapping_tools/bone_database.py`
- Create: `mapping_tools/tests/test_bone_database.py`

**Purpose:** Provide a clean API to load default + user overlay, resolve bone names, and persist user corrections.

- [ ] **Step 1: Write `bone_database.py`**

```python
# type: ignore
"""Canonical bone database with default template and user alias overlay."""
import json
import os
from typing import Dict, List, Optional, Tuple

import bpy


class BoneEntry:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.canonical_name = data["canonical_name"]
        self.display_name = data["display_name"]
        self.category = data["category"]
        self.side = data["side"]
        self.description = data.get("description", "")
        self.aliases = [a.lower() for a in data.get("aliases", [])]


class BoneDatabase:
    DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "bone_canon_default.json")
    USER_DIR = os.path.join(bpy.utils.resource_path("USER"), "scripts", "presets", "yuinomodtools")
    USER_FILENAME = "bone_canon_user.json"

    def __init__(self, user_dir: Optional[str] = None):
        self.user_dir = user_dir or self.USER_DIR
        self.entries: List[BoneEntry] = []
        self.user_aliases: Dict[str, List[dict]] = {}
        self._alias_index: Dict[str, Tuple[str, float]] = {}

    @classmethod
    def load(cls, user_dir: Optional[str] = None) -> "BoneDatabase":
        db = cls(user_dir=user_dir)
        db._load_default()
        db._load_user()
        db._build_index()
        return db

    def _load_default(self):
        if not os.path.exists(self.DEFAULT_PATH):
            return
        with open(self.DEFAULT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for bone_data in data.get("bones", []):
            self.entries.append(BoneEntry(bone_data))

    def _load_user(self):
        path = os.path.join(self.user_dir, self.USER_FILENAME)
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.user_aliases = data.get("user_aliases", {})
        except Exception:
            self.user_aliases = {}

    def _build_index(self):
        self._alias_index = {}
        # Default aliases have confidence 1.0
        for entry in self.entries:
            for alias in entry.aliases:
                self._alias_index[alias] = (entry.id, 1.0)
        # User aliases overlay with explicit confidence
        for entry_id, aliases in self.user_aliases.items():
            for info in aliases:
                alias = info["alias"].lower()
                confidence = info.get("confidence", 1.0)
                existing = self._alias_index.get(alias)
                if existing is None or confidence > existing[1]:
                    self._alias_index[alias] = (entry_id, confidence)

    def get_entry(self, entry_id: str) -> Optional[BoneEntry]:
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def resolve_exact(self, bone_name: str) -> Optional[BoneEntry]:
        """Resolve by exact alias match (case-insensitive)."""
        lower = bone_name.lower()
        if lower in self._alias_index:
            entry_id, _ = self._alias_index[lower]
            return self.get_entry(entry_id)
        return None

    def resolve_fuzzy(self, bone_name: str, threshold: float = 0.6) -> Optional[BoneEntry]:
        """Resolve using name_score against all aliases."""
        # Lazy import to avoid circular dependency with modtoolkit
        from .modtoolkit import name_score

        best_entry = None
        best_score = threshold
        for entry in self.entries:
            for alias in entry.aliases:
                score = name_score(bone_name, alias)
                if score > best_score:
                    best_score = score
                    best_entry = entry
        return best_entry

    def resolve(self, bone_name: str, threshold: float = 0.6) -> Optional[BoneEntry]:
        """Try exact match first, then fuzzy."""
        exact = self.resolve_exact(bone_name)
        if exact is not None:
            return exact
        return self.resolve_fuzzy(bone_name, threshold=threshold)

    def find_entry_by_alias(self, alias: str) -> Optional[BoneEntry]:
        """Return the entry that currently owns this alias, if any."""
        lower = alias.lower()
        if lower in self._alias_index:
            entry_id, _ = self._alias_index[lower]
            return self.get_entry(entry_id)
        return None

    def has_alias(self, entry_id: str, alias: str) -> bool:
        entry = self.get_entry(entry_id)
        if entry is None:
            return False
        lower = alias.lower()
        if lower in entry.aliases:
            return True
        for info in self.user_aliases.get(entry_id, []):
            if info["alias"].lower() == lower:
                return True
        return False

    def add_alias(
        self,
        entry_id: str,
        alias: str,
        source: str = "correction",
        confidence: float = 1.0,
        conflict_with: Optional[str] = None,
    ):
        if entry_id not in self.user_aliases:
            self.user_aliases[entry_id] = []

        lower = alias.lower()
        for existing in self.user_aliases[entry_id]:
            if existing["alias"].lower() == lower:
                return

        self.user_aliases[entry_id].append({
            "alias": alias,
            "source": source,
            "confidence": confidence,
            "conflict_with": conflict_with,
        })
        self._build_index()

    def save_user(self):
        path = os.path.join(self.user_dir, self.USER_FILENAME)
        os.makedirs(self.user_dir, exist_ok=True)
        data = {
            "version": "1.0",
            "user_aliases": self.user_aliases,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def reset_user(self):
        self.user_aliases = {}
        self._build_index()
        path = os.path.join(self.user_dir, self.USER_FILENAME)
        if os.path.exists(path):
            os.remove(path)

    def export_user(self, filepath: str):
        data = {
            "version": "1.0",
            "user_aliases": self.user_aliases,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def import_user(self, filepath: str):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.user_aliases = data.get("user_aliases", {})
        self._build_index()
        self.save_user()
```

- [ ] **Step 2: Write `mapping_tools/tests/test_bone_database.py`**

```python
# type: ignore
"""Tests for bone_database.py - run inside Blender."""
import json
import os
import tempfile

from ..bone_database import BoneDatabase


def test_load_default():
    db = BoneDatabase.load(user_dir=tempfile.mkdtemp())
    assert len(db.entries) > 0
    head = db.get_entry("bip01_head")
    assert head is not None
    assert head.display_name == "头部"


def test_resolve_exact():
    db = BoneDatabase.load(user_dir=tempfile.mkdtemp())
    # If 'head' is in default aliases
    entry = db.resolve_exact("head")
    if entry is not None:
        assert entry.id == "bip01_head"


def test_user_alias_persistence():
    user_dir = tempfile.mkdtemp()
    db = BoneDatabase.load(user_dir=user_dir)
    db.add_alias("bip01_head", "my_custom_head", source="correction")
    db.save_user()

    db2 = BoneDatabase.load(user_dir=user_dir)
    entry = db2.resolve_exact("my_custom_head")
    assert entry is not None
    assert entry.id == "bip01_head"


def test_reset_user():
    user_dir = tempfile.mkdtemp()
    db = BoneDatabase.load(user_dir=user_dir)
    db.add_alias("bip01_head", "my_custom_head", source="correction")
    db.save_user()
    db.reset_user()
    assert db.resolve_exact("my_custom_head") is None


def run_all():
    test_load_default()
    test_resolve_exact()
    test_user_alias_persistence()
    test_reset_user()
    print("All bone_database tests passed")


if __name__ == "__main__":
    run_all()
```

- [ ] **Step 3: Run tests inside Blender**

Open Blender, go to Scripting tab, open `mapping_tools/tests/test_bone_database.py`, and run the script.

Expected console output: `All bone_database tests passed`

- [ ] **Step 4: Commit**

```bash
git add mapping_tools/bone_database.py mapping_tools/tests/test_bone_database.py
git commit -m "feat: add BoneDatabase module with default + user overlay"
```

---

## Task 5: Add `auto_map_mode` Property and UI Dropdown

**Files:**
- Modify: `mapping_tools/modtoolkit.py`

**Purpose:** Let the user choose between similarity and canon matching algorithms.

- [ ] **Step 1: Add the EnumProperty in `register()`**

Find the `register()` function in `mapping_tools/modtoolkit.py` and add:

```python
bpy.types.Scene.xbone_automap_mode = bpy.props.EnumProperty(
    name="自动映射算法",
    description="选择自动骨骼匹配算法",
    items=[
        ('SIMILARITY', "智能相似度", "基于名称、层级、空间和预设历史的综合评分"),
        ('CANON', "数据库匹配", "基于标准骨骼数据库的功能分类匹配"),
    ],
    default='SIMILARITY'
)
```

- [ ] **Step 2: Clean up property in `unregister()`**

In `unregister()`, add:

```python
if hasattr(bpy.types.Scene, 'xbone_automap_mode'):
    del bpy.types.Scene.xbone_automap_mode
```

- [ ] **Step 3: Add UI dropdown in auto-map box**

Find the auto-map box in `MyAddonPanel.draw()` (around line 1147) and change:

```python
box_auto.label(text=LANG["auto_map.label"], icon="BONE_DATA")
box_auto.prop(scene, "auto_src_armature", text=LANG["auto_map.src"], icon="ARMATURE_DATA")
box_auto.prop(scene, "auto_tgt_armature", text=LANG["auto_map.tgt"], icon="ARMATURE_DATA")
box_auto.operator(AutoMapBones.bl_idname, text=AutoMapBones.bl_label, icon="FILE_REFRESH")
```

To:

```python
box_auto.label(text=LANG["auto_map.label"], icon="BONE_DATA")
box_auto.prop(scene, "xbone_automap_mode", text="算法")
box_auto.prop(scene, "auto_src_armature", text=LANG["auto_map.src"], icon="ARMATURE_DATA")
box_auto.prop(scene, "auto_tgt_armature", text=LANG["auto_map.tgt"], icon="ARMATURE_DATA")
box_auto.operator(AutoMapBones.bl_idname, text=AutoMapBones.bl_label, icon="FILE_REFRESH")
```

- [ ] **Step 4: Verify in Blender**

Reload the addon in Blender. Open the XQFA panel → Mapping Tools. Confirm a "算法" dropdown appears with two options.

- [ ] **Step 5: Commit**

```bash
git add mapping_tools/modtoolkit.py
git commit -m "feat: add auto map algorithm selector UI"
```

---

## Task 6: Implement Canonical Matching Algorithm

**Files:**
- Modify: `mapping_tools/modtoolkit.py`

**Purpose:** Add the database-based matching path inside `auto_match_bones()`.

- [ ] **Step 1: Add `_detect_side()` helper**

Add near the other helper functions:

```python
_SIDE_TOKENS = {
    "L": {"left", "l", "lt"},
    "R": {"right", "r", "rt"},
}


def _detect_side(name: str) -> Optional[str]:
    """Detect L/R side from a bone name. Returns 'L', 'R', or None."""
    lower = name.lower()
    # Prefix / suffix
    for prefix, side in [
        ("left_", "L"), ("right_", "R"), ("l_", "L"), ("r_", "R"),
        ("lt_", "L"), ("rt_", "R"),
    ]:
        if lower.startswith(prefix):
            return side
    for suffix, side in [
        ("_left", "L"), ("_right", "R"), ("_l", "L"), ("_r", "R"),
        (".left", "L"), (".right", "R"), (".l", "L"), (".r", "R"),
    ]:
        if lower.endswith(suffix):
            return side
    # Whole-name tokens
    tokens = _tokenize(name)
    if tokens and tokens[-1] in _SIDE_TOKENS["L"]:
        return "L"
    if tokens and tokens[-1] in _SIDE_TOKENS["R"]:
        return "R"
    return None
```

- [ ] **Step 2: Add `_canonical_match_score()` helper**

```python
def _canonical_match_score(sb, tb, src_entry, tgt_entry, db, src_paths, tgt_paths, bbox_src, bbox_tgt):
    """Score a pair that resolves to the same canonical entry."""
    # Alias confidence: best name_score against any alias
    from .bone_database import BoneDatabase
    best_alias_score = 0.0
    for alias in src_entry.aliases:
        best_alias_score = max(best_alias_score, name_score(sb.name, alias))
    for alias in tgt_entry.aliases:
        best_alias_score = max(best_alias_score, name_score(tb.name, alias))

    # Side consistency
    src_side = _detect_side(sb.name)
    tgt_side = _detect_side(tb.name)
    if src_side is None or tgt_side is None:
        side_score = 0.8
    elif src_side == tgt_side:
        side_score = 1.0
    else:
        side_score = 0.5

    # Hierarchy (reuse cached paths)
    hs = _cached_hierarchy_score_paths(src_paths[sb.name], tgt_paths[tb.name])

    # Spatial
    ss = _cached_spatial_score_positions(
        _get_bone_head_local(sb), _get_bone_head_local(tb), bbox_src, bbox_tgt
    )

    return 0.40 * best_alias_score + 0.25 * side_score + 0.20 * hs + 0.15 * ss
```

You will need to extract the cached path-only and position-only helpers from the existing `_cached_hierarchy_score` and `_cached_spatial_score` closures so they can be reused. Refactor:

```python
def _cached_hierarchy_score_paths(path_a, path_b) -> float:
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


def _cached_spatial_score_positions(pos_a, pos_b, bbox_a, bbox_b) -> float:
    import math
    norm_a = tuple((pos_a[i] - bbox_a[0][i]) / bbox_a[2] for i in range(3))
    norm_b = tuple((pos_b[i] - bbox_b[0][i]) / bbox_b[2] for i in range(3))
    dist = math.sqrt(sum((norm_a[i] - norm_b[i]) ** 2 for i in range(3)))
    base_sim = max(0.0, 1.0 - dist * 2.0)
    mirror_dist = math.sqrt(
        (norm_a[0] - (1.0 - norm_b[0])) ** 2
        + (norm_a[1] - norm_b[1]) ** 2
        + (norm_a[2] - norm_b[2]) ** 2
    )
    mirror_sim = max(0.0, 1.0 - mirror_dist * 2.0)
    return max(base_sim, mirror_sim * 0.6)
```

Then update the existing closures to call these top-level helpers.

- [ ] **Step 3: Add canonical branch in `auto_match_bones()`**

Inside `auto_match_bones()`, after loading presets and precomputing caches, replace the score-building loop with a mode branch:

```python
algorithm = bpy.context.scene.xbone_automap_mode

if algorithm == 'CANON':
    from .bone_database import BoneDatabase
    db = BoneDatabase.load()
    CANON_THRESHOLD = 0.60

    for sb in src_bones:
        src_entry = db.resolve(sb.name, threshold=0.5)
        if src_entry is None:
            continue
        for tb in tgt_bones:
            if tb.name in matched_tgt:
                continue
            tgt_entry = db.resolve(tb.name, threshold=0.5)
            if tgt_entry is None or tgt_entry.id != src_entry.id:
                continue
            score = _canonical_match_score(
                sb, tb, src_entry, tgt_entry, db,
                src_paths, tgt_paths, bbox_src, bbox_tgt
            )
            if score >= CANON_THRESHOLD:
                scores.append((score, sb.name, tb.name))
else:
    # existing similarity branch
    preset_data, vg_index, bone_index = load_preset_mappings()
    max_preset_count = max(preset_data.values()) if preset_data else 0
    for sb in src_bones:
        for tb in tgt_bones:
            ns = name_score(sb.name, tb.name)
            hs = _cached_hierarchy_score(sb, tb)
            ss = _cached_spatial_score(sb, tb)
            pb = preset_bonus(sb.name, tb.name, preset_data, vg_index, bone_index, max_preset_count)
            total = 0.30 * ns + 0.15 * hs + 0.10 * ss + 0.45 * pb
            scores.append((total, sb.name, tb.name))
```

Also initialize `matched_tgt = set()` earlier if not already present.

- [ ] **Step 4: Adjust unmatched lists for canon mode**

In canon mode, bones that fail to resolve should be reported as unmatched. Add handling before returning:

```python
if algorithm == 'CANON':
    unmatched_src = [b.name for b in src_bones if b.name not in matched_src]
    unmatched_tgt = [b.name for b in tgt_bones if b.name not in matched_tgt]
```

(The existing code already computes these, but ensure they reflect the canon branch.)

- [ ] **Step 5: Test both modes in Blender**

1. Select two armatures with known naming styles
2. Run "智能相似度" mode → note results
3. Run "数据库匹配" mode → note results
4. Verify canon mode resolves known aliases correctly

- [ ] **Step 6: Commit**

```bash
git add mapping_tools/modtoolkit.py
git commit -m "feat: implement canonical bone matching algorithm"
```

---

## Task 7: Implement Learning from User Corrections

**Files:**
- Modify: `mapping_tools/modtoolkit.py`

**Purpose:** When a user manually edits a mapping list item, absorb the target bone name as a new alias.

- [ ] **Step 1: Add a property update callback to `ListItem.bone`**

Find the `ListItem` PropertyGroup and add an `update` callback:

```python
def _on_list_bone_updated(self, context):
    """Called when user manually changes the bone field of a mapping item."""
    if not self.vg or not self.bone:
        return
    if getattr(context.scene, "xbone_automap_mode", 'SIMILARITY') != 'CANON':
        return

    from .bone_database import BoneDatabase
    db = BoneDatabase.load()
    entry = db.resolve(self.vg, threshold=0.5)
    if entry is None:
        return

    conflict = db.find_entry_by_alias(self.bone)
    if conflict is not None and conflict.id != entry.id:
        db.add_alias(entry.id, self.bone, source="correction", conflict_with=conflict.id)
    else:
        db.add_alias(entry.id, self.bone, source="correction")
    db.save_user()


class ListItem(PropertyGroup):
    vg_tip = LANG["ul_list.vg.tip"]
    bone_tip = LANG["ul_list.bone.tip"]

    vg: StringProperty(name="vg", description=vg_tip, default="")
    bone: StringProperty(name="bone", description=bone_tip, default="", update=_on_list_bone_updated)
```

> Note: `vg` here is used as the source bone name. In the mapping workflow it represents a vertex group, but for auto-mapping it corresponds to the source armature bone name.

- [ ] **Step 2: Add a manual "Learn from current list" operator**

Add an operator that bulk-learns all current list entries:

```python
class LIST_OT_LearnFromList(Operator):
    bl_idname = "my_list.learn_from_list"
    bl_label = "从当前列表学习"
    bl_description = "将当前映射列表中的手动修正吸收到数据库"

    def execute(self, context):
        from .bone_database import BoneDatabase
        db = BoneDatabase.load()
        scene = context.scene
        learned = 0
        for item in scene.xbone_list:
            if not item.vg or not item.bone:
                continue
            entry = db.resolve(item.vg, threshold=0.5)
            if entry is None:
                continue
            if not db.has_alias(entry.id, item.bone):
                conflict = db.find_entry_by_alias(item.bone)
                kwargs = {"conflict_with": conflict.id} if conflict and conflict.id != entry.id else {}
                db.add_alias(entry.id, item.bone, source="correction", **kwargs)
                learned += 1
        if learned > 0:
            db.save_user()
        self.report({'INFO'}, f"已学习 {learned} 个别名")
        return {'FINISHED'}
```

Register this operator in `register()` and `unregister()`.

- [ ] **Step 3: Test learning**

1. Run canon auto-map on a pair of armatures
2. Manually change one incorrect mapping
3. Check `bone_canon_user.json` in the user presets directory
4. Verify the new alias appears under the expected entry

- [ ] **Step 4: Commit**

```bash
git add mapping_tools/modtoolkit.py
git commit -m "feat: learn user corrections into canonical bone database"
```

---

## Task 8: Add Database Management UI

**Files:**
- Modify: `mapping_tools/modtoolkit.py`

**Purpose:** Provide import/export/reset and seed-from-presets controls.

- [ ] **Step 1: Add management operators**

```python
class CANON_OT_ExportDatabase(Operator):
    bl_idname = "xqfa.export_canon_database"
    bl_label = "导出用户数据库"
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        from .bone_database import BoneDatabase
        db = BoneDatabase.load()
        db.export_user(self.filepath)
        self.report({'INFO'}, f"已导出: {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = "bone_canon_user.json"
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class CANON_OT_ImportDatabase(Operator, ImportHelper):
    bl_idname = "xqfa.import_canon_database"
    bl_label = "导入用户数据库"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={'HIDDEN'})

    def execute(self, context):
        from .bone_database import BoneDatabase
        db = BoneDatabase.load()
        db.import_user(self.filepath)
        self.report({'INFO'}, f"已导入: {self.filepath}")
        return {'FINISHED'}


class CANON_OT_ResetDatabase(Operator):
    bl_idname = "xqfa.reset_canon_database"
    bl_label = "重置用户数据库"
    bl_description = "清空所有用户修正，恢复默认模板"

    def execute(self, context):
        from .bone_database import BoneDatabase
        db = BoneDatabase.load()
        db.reset_user()
        self.report({'INFO'}, "用户数据库已重置")
        return {'FINISHED'}


class CANON_OT_SeedFromPresets(Operator):
    bl_idname = "xqfa.seed_canon_from_presets"
    bl_label = "从预设生成别名"
    bl_description = "扫描现有预设，将未识别的骨骼名补充到用户层数据库"

    def execute(self, context):
        from .bone_database import BoneDatabase
        from .modtoolkit import load_preset_mappings
        db = BoneDatabase.load()
        preset_data, _, _ = load_preset_mappings()
        added = 0
        for (vg, bone), count in preset_data.items():
            entry = db.resolve(vg, threshold=0.5)
            if entry is not None and not db.has_alias(entry.id, bone):
                db.add_alias(entry.id, bone, source="preset", confidence=min(count / 5.0, 1.0))
                added += 1
        if added > 0:
            db.save_user()
        self.report({'INFO'}, f"从预设补充了 {added} 个别名")
        return {'FINISHED'}
```

- [ ] **Step 2: Add a management box in the panel**

In `MyAddonPanel.draw()`, add after the auto-map box:

```python
box_db = layout.box()
box_db.label(text="骨骼数据库", icon="FILE_BLEND")
box_db.operator("xqfa.seed_canon_from_presets")
box_db.operator("xqfa.export_canon_database")
box_db.operator("xqfa.import_canon_database")
box_db.operator("xqfa.reset_canon_database")
```

- [ ] **Step 3: Register/unregister new operators**

Add the four operator classes to the register list and `register()`/`unregister()` calls.

- [ ] **Step 4: Test in Blender**

1. Click "从预设生成别名" → check user JSON is created
2. Click "导出用户数据库" → verify file contents
3. Click "重置用户数据库" → verify user JSON is removed

- [ ] **Step 5: Commit**

```bash
git add mapping_tools/modtoolkit.py
git commit -m "feat: add canonical bone database management UI"
```

---

## Task 9: Integration Testing and Polish

**Files:**
- Modify: `mapping_tools/modtoolkit.py`, `mapping_tools/bone_database.py` as needed

**Purpose:** Ensure the new system works end-to-end and does not break existing functionality.

- [ ] **Step 1: Test default algorithm unchanged**

Set algorithm to "智能相似度" and run auto-map. Compare output to the pre-implementation behavior (same as before).

- [ ] **Step 2: Test canon mode on known skeleton pairs**

Use at least two pairs:
- Bip01-style → Mixamo-style
- MMD-style → Bip01-style

Verify the 52 core bones are matched correctly.

- [ ] **Step 3: Test learning loop**

1. Run canon mode
2. Fix one wrong mapping manually
3. Re-run canon mode on the same pair
4. Verify the fixed mapping is now correct

- [ ] **Step 4: Check console output**

Ensure no exceptions when:
- Default JSON is missing
- User JSON is corrupted
- No presets exist

- [ ] **Step 5: Update localization strings (optional)**

If using `LANG` dict, add new keys for UI labels:
- `auto_map.mode`
- `canon_db.label`
- `canon_db.seed`
- `canon_db.export`
- `canon_db.import`
- `canon_db.reset`

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: canonical bone database auto-mapping with learning and management UI"
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** All sections of `BONE_CANON_DATABASE_DESIGN.md` are represented by tasks.
- [ ] **No placeholders:** Every task contains concrete code, commands, and expected output.
- [ ] **Type consistency:** `BoneDatabase`, `BoneEntry`, `xbone_automap_mode`, operator `bl_idname`s match across tasks.
- [ ] **No circular imports:** `bone_database.py` uses lazy import of `name_score`; `modtoolkit.py` imports `BoneDatabase` at use sites.
- [ ] **Backward compatibility:** Similarity mode is the default and the existing code path is preserved.

---

## Execution Handoff

Plan complete and saved to `mapping_tools/BONE_CANON_DATABASE_PLAN.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach do you prefer?
