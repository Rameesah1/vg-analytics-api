import pytest
from src.insights.service import AnalyticsService


def make_verdict(critic, user, sales):
    svc = AnalyticsService.__new__(AnalyticsService)
    return svc._compute_verdict(critic, user, sales)


def test_all_time_classic():
    v = make_verdict(95, 9.2, 15.0)
    assert v["verdict"] == "All-Time Classic"
    assert v["confidence"] == "high"


def test_cult_classic():
    v = make_verdict(60, 8.5, 0.5)
    assert v["verdict"] == "Cult Classic"


def test_critic_darling():
    v = make_verdict(85, 5.0, 2.0)
    assert v["verdict"] == "Critic Darling"


def test_overhyped():
    v = make_verdict(60, 6.0, 18.0)
    assert v["verdict"] == "Overhyped"


def test_hidden_gem():
    v = make_verdict(72, 8.0, 0.2)
    assert v["verdict"] == "Hidden Gem"


def test_commercial_hit():
    v = make_verdict(75, 7.5, 12.0)
    assert v["verdict"] == "Commercial Hit"


def test_divisive():
    v = make_verdict(75, 4.5, 1.0)
    assert v["verdict"] == "Divisive"


def test_great_game():
    v = make_verdict(82, 8.0, 3.0)
    assert v["verdict"] == "Great Game"


def test_solid_title():
    v = make_verdict(70, 7.0, 2.0)
    assert v["verdict"] == "Solid Title"


def test_unrated_no_scores():
    v = make_verdict(None, None, None)
    assert v["verdict"] == "Unrated"
    assert v["confidence"] == "low"


def test_unrated_missing_user():
    v = make_verdict(85, None, 5.0)
    assert v["verdict"] == "Unrated"


def test_confidence_medium_no_sales():
    v = make_verdict(82, 8.0, None)
    assert v["confidence"] == "medium"


def test_confidence_high_all_data():
    v = make_verdict(95, 9.2, 15.0)
    assert v["confidence"] == "high"


def test_scores_scaled_correctly():
    v = make_verdict(80, 8.0, 0.0)
    assert v["scores"]["user"] == 80.0
    assert v["scores"]["critic"] == 80.0


def test_sales_capped_at_100():
    v = make_verdict(85, 8.5, 100.0)
    assert v["scores"]["sales"] == 100


def test_zero_sales_does_not_crash():
    v = make_verdict(85, 8.0, 0.0)
    assert v["verdict"] is not None


def test_divergence_calculated():
    v = make_verdict(90, 5.0, 1.0)
    assert v["scores"]["divergence"] == 40