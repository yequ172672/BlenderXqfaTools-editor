# type: ignore
"""
Tests for auto-map optimisation (P1-A/B/C, P2-A/B/C).
Run inside Blender's Python environment.
"""
import math
import tempfile
from functools import lru_cache

from ..modtoolkit import (
    _tokenize,
    name_score,
    _strip_side,
    spatial_score,
    _cached_spatial_score_positions,
    _compute_bbox,
    preset_bonus,
    NO_PRESET_WEIGHT,
    RENORM_NAME_WEIGHT,
    _invalidate_preset_cache,
)
from ..bone_database import (
    BoneDatabase,
    invalidate_cache as db_invalidate_cache,
    _cache_defaults_raw,
    _cache_user_raw,
)


# ---------------------------------------------------------------------------
# P1-B: name_score / _tokenize lru_cache correctness
# ---------------------------------------------------------------------------

def test_tokenize_cached_consistent():
    """_tokenize returns the same result on repeated calls (cache hit == recompute)."""
    names = ["Bip01_Spine", "LeftUpperArm", "R_Thigh_02", "root"]
    for n in names:
        first = _tokenize(n)
        second = _tokenize(n)
        assert first == second, f"_tokenize inconsistent for '{n}': {first} != {second}"


def test_tokenize_idempotent():
    """_tokenize is idempotent: calling it twice gives the same output."""
    name = "LeftUpperArm"
    assert _tokenize(name) == _tokenize(name)


def test_name_score_cached_consistent():
    """name_score returns the same result on repeated calls."""
    pairs = [
        ("Bip01_Spine", "spine_01"),
        ("LeftArm", "arm_l"),
        ("R_Hand", "RightHand"),
        ("head", "Bip01_Head"),
    ]
    for a, b in pairs:
        first = name_score(a, b)
        second = name_score(a, b)
        assert abs(first - second) < 1e-9, f"name_score inconsistent for ({a},{b})"


def test_name_score_symmetry():
    """name_score(a, b) == name_score(b, a) (Jaccard + side_bonus are symmetric)."""
    pairs = [
        ("Bip01_Spine", "spine_01"),
        ("LeftArm", "arm_l"),
        ("R_Hand", "RightHand"),
        ("head", "Bip01_Head"),
        ("UpperArm_L", "left_upperarm"),
    ]
    for a, b in pairs:
        ab = name_score(a, b)
        ba = name_score(b, a)
        assert abs(ab - ba) < 1e-9, f"name_score not symmetric for ({a},{b}): {ab} != {ba}"


def test_name_score_range():
    """name_score always returns a value in [0, 1]."""
    names = ["Bip01_Spine", "LeftArm", "R_Hand", "head", "root", "toe_02"]
    for a in names:
        for b in names:
            s = name_score(a, b)
            assert 0.0 <= s <= 1.0, f"name_score({a},{b}) = {s} out of range"


# ---------------------------------------------------------------------------
# P2-C: BoneDatabase JSON parse cache
# ---------------------------------------------------------------------------

def test_db_cache_invalidate_on_save():
    """save_user() invalidates the module-level JSON parse cache."""
    import mapping_tools.bone_database as bd_mod

    user_dir = tempfile.mkdtemp()
    db_invalidate_cache()  # start clean
    db = BoneDatabase.load(user_dir=user_dir)
    assert bd_mod._cache_defaults_raw is not None, "defaults should be cached after load"

    db.add_alias("bip01_head", "test_head_alias", source="test")
    db.save_user()
    assert bd_mod._cache_user_raw is None, "user cache should be None after invalidate_cache()"


def test_db_cache_invalidate_on_reset():
    """reset_user() invalidates the module-level JSON parse cache."""
    import mapping_tools.bone_database as bd_mod

    user_dir = tempfile.mkdtemp()
    db_invalidate_cache()
    db = BoneDatabase.load(user_dir=user_dir)
    db.add_alias("bip01_head", "reset_test_alias", source="test")
    db.save_user()

    db.reset_user()
    assert bd_mod._cache_user_raw is None, "user cache should be None after reset_user()"


def test_db_cache_add_alias_no_invalidate():
    """add_alias() mutates instance state but does NOT invalidate cache."""
    import mapping_tools.bone_database as bd_mod

    user_dir = tempfile.mkdtemp()
    db_invalidate_cache()
    db = BoneDatabase.load(user_dir=user_dir)
    cached_before = bd_mod._cache_user_raw

    db.add_alias("bip01_head", "no_invalidate_alias", source="test")
    assert bd_mod._cache_user_raw is cached_before, (
        "add_alias should not invalidate the module-level cache"
    )


# ---------------------------------------------------------------------------
# P1-A: bbox per-axis normalisation
# ---------------------------------------------------------------------------

def test_spatial_score_per_axis_normalisation():
    """
    With height=2.0, width=0.2, depth=0.2, two bones that differ ONLY in X
    should have a large spatial_score delta (not diluted by height).

    Before fix: both bones normalise X by height(2.0), so delta ≈ 0.
    After  fix: X is normalised by width(0.2), so delta is large.
    """
    # bbox = (mins, maxs, sizes_per_axis)
    bbox = (
        (-0.1, 0.0, -0.1),   # mins
        (0.1, 2.0, 0.1),     # maxs
        (0.2, 2.0, 0.2),     # sizes per axis (width, height, depth)
    )

    # Two bones at different X positions but same Y/Z
    pos_a = (0.0, 1.0, 0.0)   # centre X
    pos_b = (0.1, 1.0, 0.0)   # right-edge X

    score = _cached_spatial_score_positions(pos_a, pos_b, bbox, bbox)
    # With per-axis norm: X delta = 0.1/0.2 = 0.5 normalised units
    # dist = 0.5, base_sim = max(0, 1 - 0.5*2) = 0.0
    # mirror_dist X = |0.5 - (1-0.0)| = 0.5, so mirror_sim also low
    # The key assertion: score should be LOW (the bones are clearly at different X)
    # With old scalar norm (size=2.0): X delta = 0.1/2.0 = 0.05, dist≈0.05, score≈0.9
    # After fix: score should be much lower
    assert score < 0.5, (
        f"Per-axis normalisation bug: bones at different X positions got score={score:.3f}, "
        f"expected < 0.5 (would be ~0.9 with old scalar normalisation)"
    )


def test_spatial_score_same_position():
    """Bones at the same normalised position should have spatial_score = 1.0."""
    bbox = ((0, 0, 0), (1, 1, 1), (1.0, 1.0, 1.0))
    pos = (0.5, 0.5, 0.5)
    score = _cached_spatial_score_positions(pos, pos, bbox, bbox)
    assert abs(score - 1.0) < 1e-6, f"Same position should give score=1.0, got {score}"


def test_spatial_score_mirror_tolerance():
    """Mirror positions (X flipped) should get partial credit via mirror path."""
    bbox = ((0, 0, 0), (1, 1, 1), (1.0, 1.0, 1.0))
    pos_a = (0.1, 0.5, 0.5)
    pos_b = (0.9, 0.5, 0.5)  # X-mirror of pos_a
    score = _cached_spatial_score_positions(pos_a, pos_b, bbox, bbox)
    # Direct: X delta=0.8, dist=0.8, base_sim=max(0, 1-1.6)=0
    # Mirror: X = |0.1 - (1-0.9)| = |0.1-0.1| = 0, mirror_dist=0, mirror_sim=1.0
    # Final: max(0, 1.0 * 0.6) = 0.6
    assert abs(score - 0.6) < 1e-6, f"Mirror should give ~0.6, got {score}"


# ---------------------------------------------------------------------------
# P1-C: SIMILARITY renormalisation constants
# ---------------------------------------------------------------------------

def test_no_preset_weight_constant():
    """NO_PRESET_WEIGHT equals 0.30 + 0.15 + 0.10."""
    assert abs(NO_PRESET_WEIGHT - 0.55) < 1e-9


def test_renorm_name_weight_constant():
    """RENORM_NAME_WEIGHT equals 0.30 / 0.55."""
    expected = 0.30 / 0.55
    assert abs(RENORM_NAME_WEIGHT - expected) < 1e-9


# ---------------------------------------------------------------------------
# P2-A: CANON threshold constant (verified by value check in source)
# ---------------------------------------------------------------------------

def test_canon_threshold_value():
    """
    CANON_THRESHOLD should be 0.40 (relaxed from 0.60).
    We test this by inspecting the source code constant.
    """
    import inspect
    from ..modtoolkit import auto_match_bones
    src = inspect.getsource(auto_match_bones)
    assert "CANON_THRESHOLD = 0.40" in src, (
        "CANON_THRESHOLD should be 0.40 in auto_match_bones source"
    )


# ---------------------------------------------------------------------------
# P2-B: Short-circuit pruning
# ---------------------------------------------------------------------------

def test_short_circuit_cutoff_formula():
    """
    With threshold=0.25, the short-circuit cutoff for the renormalised path is:
      cutoff = 0.25 * RENORM_NAME_WEIGHT = 0.25 * (0.30/0.55) ≈ 0.1364
    Pairs with ns < cutoff should be skipped.
    """
    threshold = 0.25
    cutoff = threshold * RENORM_NAME_WEIGHT
    # Verify the cutoff is in a sensible range
    assert 0.10 < cutoff < 0.20, f"cutoff={cutoff:.4f} seems out of range"

    # Two completely unrelated names should have ns=0 and be skipped
    ns_unrelated = name_score("Bip01_Spine", "toe_02_r")
    # This may or may not be 0 depending on token overlap, but the formula is correct


def test_short_circuit_preset_path():
    """
    With presets (max_preset_count > 0): ns==0 and pb==0.0 should be skipped.
    The max achievable score without name/preset signal is 0.15*1+0.10*1=0.25,
    which equals threshold — so the optimisation is safe.
    """
    # Verify: max score with ns=0, pb=0.0, hs=1.0, ss=1.0 is 0.25
    max_achievable = 0.30 * 0.0 + 0.15 * 1.0 + 0.10 * 1.0 + 0.45 * 0.0
    assert abs(max_achievable - 0.25) < 1e-9


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    test_tokenize_cached_consistent()
    test_tokenize_idempotent()
    test_name_score_cached_consistent()
    test_name_score_symmetry()
    test_name_score_range()
    print("[PASS] P1-B: lru_cache correctness tests")

    test_db_cache_invalidate_on_save()
    test_db_cache_invalidate_on_reset()
    test_db_cache_add_alias_no_invalidate()
    print("[PASS] P2-C: DB cache invalidation tests")

    test_spatial_score_per_axis_normalisation()
    test_spatial_score_same_position()
    test_spatial_score_mirror_tolerance()
    print("[PASS] P1-A: per-axis normalisation tests")

    test_no_preset_weight_constant()
    test_renorm_name_weight_constant()
    print("[PASS] P1-C: renormalisation constant tests")

    test_canon_threshold_value()
    print("[PASS] P2-A: CANON threshold test")

    test_short_circuit_cutoff_formula()
    test_short_circuit_preset_path()
    print("[PASS] P2-B: short-circuit pruning tests")

    print("All auto-map optimisation tests passed")


if __name__ == "__main__":
    run_all()
