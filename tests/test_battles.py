import pytest
from src.battles.service import BattlesService, PRESETS, DRAW_THRESHOLD


def score(dna, weights):
    svc = BattlesService.__new__(BattlesService)
    return svc._compute_score(dna, weights)


STRONG = {"avg_critic": 90, "avg_user_100": 85, "sales_score_100": 80}
WEAK   = {"avg_critic": 60, "avg_user_100": 55, "sales_score_100": 20}


def test_balanced_preset_exists():
    assert "BALANCED" in PRESETS
    assert abs(sum(PRESETS["BALANCED"].values()) - 1.0) < 0.01


def test_all_presets_sum_to_one():
    for name, weights in PRESETS.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 0.01, f"{name} weights don't sum to 1"


def test_balanced_strong_beats_weak():
    s = score(STRONG, PRESETS["BALANCED"])
    w = score(WEAK, PRESETS["BALANCED"])
    assert s > w


def test_critical_acclaim_weights_critic_most():
    weights = PRESETS["CRITICAL_ACCLAIM"]
    assert weights["critic"] > weights["user"]
    assert weights["critic"] > weights["sales"]


def test_peoples_choice_weights_user_most():
    weights = PRESETS["PEOPLES_CHOICE"]
    assert weights["user"] > weights["critic"]
    assert weights["user"] > weights["sales"]


def test_commercial_titans_weights_sales_most():
    weights = PRESETS["COMMERCIAL_TITANS"]
    assert weights["sales"] > weights["critic"]
    assert weights["sales"] > weights["user"]


def test_draw_threshold_value():
    assert DRAW_THRESHOLD == 0.5


def test_score_difference_triggers_winner():
    s = score(STRONG, PRESETS["BALANCED"])
    w = score(WEAK, PRESETS["BALANCED"])
    assert (s - w) > DRAW_THRESHOLD


def test_identical_squads_would_draw():
    s1 = score(STRONG, PRESETS["BALANCED"])
    s2 = score(STRONG, PRESETS["BALANCED"])
    assert abs(s1 - s2) < DRAW_THRESHOLD


def test_custom_weights_change_outcome():
    sales_heavy = {"critic": 0.1, "user": 0.1, "sales": 0.8}
    critic_heavy = {"critic": 0.8, "user": 0.1, "sales": 0.1}

    high_sales = {"avg_critic": 60, "avg_user_100": 60, "sales_score_100": 95}
    high_critic = {"avg_critic": 95, "avg_user_100": 60, "sales_score_100": 20}

    assert score(high_sales, sales_heavy) > score(high_critic, sales_heavy)
    assert score(high_critic, critic_heavy) > score(high_sales, critic_heavy)