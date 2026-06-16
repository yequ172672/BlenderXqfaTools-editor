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
