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
