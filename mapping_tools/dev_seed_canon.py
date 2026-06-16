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
    a_tokens = set(re.split(r"[_.:\-\s]", a.lower())) - {"", "bip01", "bip001", "mixamorig", "def", "b005"}
    b_tokens = set(re.split(r"[_.:\-\s]", b.lower())) - {"", "bip01", "bip001", "mixamorig", "def", "b005"}
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
