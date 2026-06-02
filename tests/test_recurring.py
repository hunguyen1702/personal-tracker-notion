from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from personal_tracker.notion.recurring import next_time_by_recurring_type

TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def dt(y, m, d, hh=9, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


@pytest.fixture
def now_2026_06_01():
    return dt(2026, 6, 1, 10, 0)


def test_daily_advances_one_day(now_2026_06_01):
    assert next_time_by_recurring_type(dt(2026, 6, 1, 9), "daily", now=now_2026_06_01) == dt(
        2026, 6, 2, 9
    )


def test_daily_skips_past_to_today(now_2026_06_01):
    # time_mark from a month ago; should be advanced to today or later.
    result = next_time_by_recurring_type(dt(2026, 5, 1, 9), "daily", now=now_2026_06_01)
    assert result is not None
    assert result.date() >= now_2026_06_01.date()


def test_weekly_jumps_to_same_weekday_next_week(now_2026_06_01):
    # 2026-06-01 is Monday.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "weekly", now=now_2026_06_01)
    assert result == dt(2026, 6, 8, 9)


def test_monthly():
    result = next_time_by_recurring_type(dt(2026, 1, 31, 9), "monthly", now=dt(2026, 1, 1))
    # relativedelta clamps Feb 31 -> Feb 28.
    assert result == dt(2026, 2, 28, 9)


def test_bi_daily(now_2026_06_01):
    assert next_time_by_recurring_type(dt(2026, 6, 1, 9), "bi-daily", now=now_2026_06_01) == dt(
        2026, 6, 3, 9
    )


def test_bi_daily_on_weekday_skips_weekend(now_2026_06_01):
    # 2026-06-04 Thu -> +2 = Sat -> +2 = Mon 2026-06-08.
    result = next_time_by_recurring_type(
        dt(2026, 6, 4, 9), "bi-daily-on-weekday", now=now_2026_06_01
    )
    assert result == dt(2026, 6, 8, 9)


def test_bi_daily_on_weekday_no_skip(now_2026_06_01):
    # 2026-06-01 Mon -> +2 = Wed.
    result = next_time_by_recurring_type(
        dt(2026, 6, 1, 9), "bi-daily-on-weekday", now=now_2026_06_01
    )
    assert result == dt(2026, 6, 3, 9)


def test_day_name_list_single_day(now_2026_06_01):
    # 2026-06-01 Mon -> next "wed" should be Wed 2026-06-03.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "wed", now=now_2026_06_01)
    assert result == dt(2026, 6, 3, 9)


def test_day_name_list_multi_day(now_2026_06_01):
    # 2026-06-01 Mon -> "tue-thu-sat": next is Tue 2026-06-02.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "tue-thu-sat", now=now_2026_06_01)
    assert result == dt(2026, 6, 2, 9)


def test_bi_weekly(now_2026_06_01):
    # +14 days, same weekday.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "bi-weekly", now=now_2026_06_01)
    assert result == dt(2026, 6, 15, 9)


def test_bi_monthly():
    result = next_time_by_recurring_type(dt(2026, 1, 15, 9), "bi-monthly", now=dt(2026, 1, 1))
    assert result == dt(2026, 3, 15, 9)


def test_annually(now_2026_06_01):
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "annually", now=now_2026_06_01)
    assert result == dt(2027, 6, 1, 9)


def test_yearly_alias(now_2026_06_01):
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "yearly", now=now_2026_06_01)
    assert result == dt(2027, 6, 1, 9)


def test_once_returns_input(now_2026_06_01):
    result = next_time_by_recurring_type(dt(2026, 5, 1, 9), "once", now=now_2026_06_01)
    assert result == dt(2026, 5, 1, 9)


def test_weekday_skips_weekend(now_2026_06_01):
    # 2026-06-05 Fri -> +1 = Sat (weekend) -> next Mon 2026-06-08, same time.
    result = next_time_by_recurring_type(dt(2026, 6, 5, 9, 30), "weekday", now=now_2026_06_01)
    assert result == dt(2026, 6, 8, 9, 30)


def test_weekday_no_skip(now_2026_06_01):
    # Mon -> Tue.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "weekday", now=now_2026_06_01)
    assert result == dt(2026, 6, 2, 9)


def test_weekend_jumps_to_saturday(now_2026_06_01):
    # Mon -> +1 = Tue (not weekend) -> Sat 2026-06-06.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9, 15), "weekend", now=now_2026_06_01)
    assert result == dt(2026, 6, 6, 9, 15)


def test_weekend_continues(now_2026_06_01):
    # Sat -> +1 = Sun (still weekend) -> stays Sun.
    result = next_time_by_recurring_type(dt(2026, 6, 6, 9), "weekend", now=now_2026_06_01)
    assert result == dt(2026, 6, 7, 9)


def test_every_n_days_keeps_ruby_off_by_one(now_2026_06_01):
    # "every 3 days" in Ruby code => +4 days. Preserve behavior.
    result = next_time_by_recurring_type(dt(2026, 6, 1, 9), "every 3 days", now=now_2026_06_01)
    assert result == dt(2026, 6, 5, 9)


def test_unknown_returns_none(now_2026_06_01):
    assert next_time_by_recurring_type(dt(2026, 6, 1), "nonsense", now=now_2026_06_01) is None
