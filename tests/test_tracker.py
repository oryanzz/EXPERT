import pytest

from maple_exp.parse import Reading
from maple_exp.tracker import Tracker


def make(exp, pct, level=30):
    return Reading(exp=exp, pct=pct, level=level)


def test_same_level_session():
    t = Tracker(0, make(1000, 10.0))
    assert t.add(600, make(3000, 30.0))
    s = t.summary(600)
    assert s.exp_gained == 2000
    assert s.minutes == 10
    assert s.exp_per_min == 200
    assert s.exp_per_hour == 12000
    assert s.pct_gained == pytest.approx(20.0)
    assert s.levels_gained == 0
    assert s.exp_to_level == 7000
    assert s.eta_minutes == pytest.approx(35)


def test_level_up_counts_rest_of_old_level_plus_new_exp():
    t = Tracker(0, make(28524, 98.43, level=22))
    assert t.add(60, make(400, 1.17, level=23))
    s = t.summary(60)
    # level 22 total = 28524 / 98.43% = 28979 -> 455 left + 400 into level 23
    assert s.exp_gained == 855
    assert s.levels_gained == 1
    assert s.level == 23


def test_level_up_detected_without_level_reading():
    t = Tracker(0, make(9800, 98.0, level=None))
    assert t.add(60, make(100, 0.8, level=None))
    s = t.summary(60)
    assert s.levels_gained == 1
    assert s.exp_gained == 300


def test_death_counts_as_net_loss():
    t = Tracker(0, make(5000, 50.0))
    assert t.add(60, make(4500, 45.0))
    assert t.summary(60).exp_gained == -500


def test_inconsistent_reading_is_rejected():
    t = Tracker(0, make(1000, 10.0))
    assert not t.add(60, make(30001, 30.0))  # extra digit: implies a 100k level
    assert t.summary(60).exp_gained == 0


def test_misread_higher_level_with_consistent_exp_is_accepted():
    # live bug 2026-10-11: OCR read "LV.23" as 30 on the end shot; the EXP was fine
    t = Tracker(0, make(12571, 36.63, level=23))
    assert t.add(60, make(12696, 36.99, level=30))
    s = t.summary(60)
    assert s.exp_gained == 125
    assert s.levels_gained == 0
    assert s.level == 23


def test_misread_lower_level_with_consistent_exp_is_accepted():
    t = Tracker(0, make(1000, 10.0, level=30))
    assert t.add(60, make(2000, 20.0, level=20))
    assert t.summary(60).level == 30


def test_level_up_counted_even_if_level_misread_as_same():
    t = Tracker(0, make(9800, 98.0, level=30))
    assert t.add(60, make(100, 0.8, level=30))
    s = t.summary(60)
    assert (s.exp_gained, s.levels_gained, s.level) == (300, 1, 31)


def test_missing_start_level_is_filled_in_later():
    t = Tracker(0, make(1000, 10.0, level=None))
    t.add(60, make(2000, 20.0, level=23))
    assert t.summary(60).level == 23


def test_gains_accumulate_across_samples():
    t = Tracker(0, make(1000, 10.0))
    t.add(300, make(2000, 20.0))
    t.add(600, make(3000, 30.0))
    assert t.summary(600).exp_gained == 2000


def test_level_total_uses_most_precise_sample():
    t = Tracker(0, make(50, 0.5))  # 0.5% rounds badly: 10000 +-1%
    t.add(60, make(5000, 50.0))
    assert t.summary(60).exp_to_level == 5000


def test_zero_elapsed_has_no_rate_or_eta():
    s = Tracker(0, make(1000, 10.0)).summary(0)
    assert s.exp_per_min == 0
    assert s.eta_minutes is None


def test_eta_none_when_not_gaining():
    t = Tracker(0, make(5000, 50.0))
    t.add(60, make(4500, 45.0))
    assert t.summary(60).eta_minutes is None


def test_misread_first_level_is_outvoted():
    t = Tracker(0, make(1000, 10.0, level=30))  # misread; really level 23
    t.add(10, make(1100, 11.0, level=23))
    t.add(20, make(1200, 12.0, level=23))
    assert t.summary(20).level == 23
