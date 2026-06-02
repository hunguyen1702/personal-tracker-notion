"""Port of `Task#next_recurring_time_of` from `app/models/task.rb`."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

DAY_ABBR_TO_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

DAYS_PATTERN = re.compile(
    r"^(?P<days>(mon|tue|wed|thu|fri|sat|sun)(-(mon|tue|wed|thu|fri|sat|sun))*)$",
    re.IGNORECASE,
)
EVERY_N_DAYS_PATTERN = re.compile(r"^every (?P<number>\d) days$")


def _is_weekend(dt: datetime) -> bool:
    return dt.weekday() >= 5


def _next_week_same_weekday(dt: datetime) -> datetime:
    # Ruby's `next_week(:weekday_name, same_time: true)`: jump to the same weekday
    # in the *following* ISO week (Monday-based).
    days_until_next_monday = 7 - dt.weekday()
    next_monday = dt + timedelta(days=days_until_next_monday)
    return next_monday + timedelta(days=dt.weekday())


def _next_recurring_time_of(input_time: datetime, recurring_type: str) -> datetime | None:
    rtype = recurring_type
    rtype_lower = rtype.lower() if isinstance(rtype, str) else rtype

    if rtype == "daily":
        return input_time + timedelta(days=1)

    if rtype == "weekly":
        return _next_week_same_weekday(input_time)

    if rtype == "monthly":
        return input_time + relativedelta(months=+1)

    if rtype == "bi-daily":
        return input_time + timedelta(days=2)

    if rtype == "bi-daily-on-weekday":
        nxt = input_time + timedelta(days=2)
        if _is_weekend(nxt):
            nxt = nxt + timedelta(days=2)
        return nxt

    days_match = DAYS_PATTERN.match(rtype_lower) if isinstance(rtype_lower, str) else None
    if days_match:
        wanted = {DAY_ABBR_TO_INDEX[d] for d in days_match.group("days").lower().split("-")}
        nxt = input_time + timedelta(days=1)
        iterate_count = 0
        # Replicate Ruby: at most 7 iterations; condition combines weekday match + not-in-past.
        # We don't have a "now" reference here (Ruby used Time.zone.now); the outer wrapper
        # handles the "advance past today" loop. So we just look for the next matching weekday.
        while nxt.weekday() not in wanted and iterate_count < 7:
            iterate_count += 1
            nxt = nxt + timedelta(days=1)
        return nxt

    if rtype == "bi-weekly":
        return _next_week_same_weekday(_next_week_same_weekday(input_time))

    if rtype == "bi-monthly":
        return input_time + relativedelta(months=+2)

    if rtype in ("annually", "yearly"):
        return input_time + relativedelta(years=+1)

    if rtype == "once":
        return input_time

    if rtype == "weekday":
        nxt = input_time + timedelta(days=1)
        if _is_weekend(nxt):
            # Jump to next Monday at original input_time's time-of-day.
            days_until_next_monday = 7 - nxt.weekday()
            nxt = (nxt + timedelta(days=days_until_next_monday)).replace(
                hour=input_time.hour,
                minute=input_time.minute,
                second=input_time.second,
                microsecond=input_time.microsecond,
            )
        return nxt

    if rtype == "weekend":
        nxt = input_time + timedelta(days=1)
        if not _is_weekend(nxt):
            # Jump to next Saturday at original input_time's time-of-day.
            days_until_saturday = (5 - nxt.weekday()) % 7
            if days_until_saturday == 0:
                days_until_saturday = 7
            nxt = (nxt + timedelta(days=days_until_saturday)).replace(
                hour=input_time.hour,
                minute=input_time.minute,
                second=input_time.second,
                microsecond=input_time.microsecond,
            )
        return nxt

    every_match = EVERY_N_DAYS_PATTERN.match(rtype) if isinstance(rtype, str) else None
    if every_match:
        # Preserves Ruby behavior: +N+1 (not +N).
        return input_time + timedelta(days=int(every_match.group("number")) + 1)

    return None


def next_time_by_recurring_type(
    time_mark: datetime,
    recurring_type: str,
    *,
    now: datetime,
) -> datetime | None:
    """Advance `time_mark` until its date is >= today's date in the same tz."""
    nxt = _next_recurring_time_of(time_mark, recurring_type)
    if nxt is None or recurring_type == "once":
        return nxt

    today = now.date()
    while nxt.date() < today:
        nxt = _next_recurring_time_of(nxt, recurring_type)
        if nxt is None:
            return None
    return nxt
