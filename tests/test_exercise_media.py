"""Direct characterization of exercise-media fallback and fuzzy matching."""

import utils.exercise_media as exercise_media


def _clear_caches() -> None:
    exercise_media._load_catalog_media_entries.cache_clear()
    exercise_media._load_fallback_media_map.cache_clear()
    exercise_media._resolve_fuzzy_media_path.cache_clear()


def setup_function():
    _clear_caches()


def teardown_function():
    _clear_caches()


def test_match_key_normalizes_phrases_drops_noise_and_singularizes():
    assert (
        exercise_media._match_key(" Dumbbell Pull-Ups — 45 Degrees Supported ")
        == "dumbbell pull ups"
    )
    assert exercise_media._match_key(None) == ""


def test_score_candidate_requires_two_shared_tokens_and_rewards_exact_match():
    assert exercise_media._score_candidate(["bench"], "bench press") == 0.0
    assert exercise_media._score_candidate(["bench", "press"], "bench press") == 1.0
    partial = exercise_media._score_candidate(
        ["incline", "dumbbell", "press"], "incline dumbbell bench press"
    )
    assert exercise_media.MIN_FUZZY_SCORE <= partial < 1.0


def test_valid_database_media_path_wins_without_loading_fallbacks(monkeypatch):
    def unexpected_load():
        raise AssertionError("fallback lookup should not run")

    monkeypatch.setattr(exercise_media, "_load_fallback_media_map", unexpected_load)

    assert (
        exercise_media.resolve_exercise_media_path(
            "Anything", "Existing_Reviewed_Path/0.jpg"
        )
        == "Existing_Reviewed_Path/0.jpg"
    )


def test_invalid_database_path_uses_exact_reviewed_fallback(monkeypatch):
    monkeypatch.setattr(
        exercise_media,
        "_load_fallback_media_map",
        lambda: {"barbell bench press": "Bench_Press/0.jpg"},
    )

    assert (
        exercise_media.resolve_exercise_media_path(
            "  Barbell BENCH Press ", "../unsafe.jpg"
        )
        == "Bench_Press/0.jpg"
    )


def test_fuzzy_fallback_selects_best_catalog_candidate(monkeypatch):
    monkeypatch.setattr(exercise_media, "_load_fallback_media_map", lambda: {})
    monkeypatch.setattr(
        exercise_media,
        "_load_catalog_media_entries",
        lambda: (
            ("Incline Dumbbell Bench Press", "incline dumbbell bench press", "Incline/0.jpg"),
            ("Seated Cable Row", "seated cable row", "Row/0.jpg"),
        ),
    )

    assert (
        exercise_media.resolve_exercise_media_path("Incline Dumbbell Press")
        == "Incline/0.jpg"
    )


def test_fuzzy_fallback_returns_none_below_threshold(monkeypatch):
    monkeypatch.setattr(exercise_media, "_load_fallback_media_map", lambda: {})
    monkeypatch.setattr(
        exercise_media,
        "_load_catalog_media_entries",
        lambda: (("Seated Cable Row", "seated cable row", "Row/0.jpg"),),
    )

    assert exercise_media.resolve_exercise_media_path("Barbell Curl") is None
