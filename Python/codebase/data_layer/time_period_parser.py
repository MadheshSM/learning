"""Parse natural language time period references into structured date ranges."""
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class TimePeriodContext:
    """Structured time period for date-range queries."""
    period_type: str       # week, month, quarter, year, custom
    period_label: str      # e.g. "Q1 2025", "March 2025", "Week of 2025-03-10"
    start_date: str        # YYYY-MM-DD
    end_date: str          # YYYY-MM-DD


# Month name -> number
_MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}


def _quarter_range(q: int, year: int):
    """Return (start, end) dates for a quarter."""
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    sm, sd = starts[q]
    em, ed = ends[q]
    return datetime(year, sm, sd), datetime(year, em, ed)


def _week_range(ref: datetime):
    """Return Monday–Sunday range for the week containing `ref`."""
    monday = ref - timedelta(days=ref.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def parse_time_period(query: str) -> Optional[TimePeriodContext]:
    """Attempt to extract a time period from a natural language query.

    Returns None if no recognizable time period is found.
    """
    if not query:
        return None

    q = query.lower().strip()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # --- "this week" / "current week" ---
    if re.search(r"\b(this|current)\s+week\b", q):
        start, end = _week_range(today)
        return TimePeriodContext("week", f"This week ({start:%b %d} – {end:%b %d, %Y})",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "next week" / "upcoming week" / "coming week" ---
    if re.search(r"\b(next|upcoming|coming)\s+week\b", q):
        next_mon = today + timedelta(days=(7 - today.weekday()))
        start, end = _week_range(next_mon)
        return TimePeriodContext("week", f"Next week ({start:%b %d} – {end:%b %d, %Y})",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "last week" / "previous week" ---
    if re.search(r"\b(last|previous)\s+week\b", q):
        prev_day = today - timedelta(days=7)
        start, end = _week_range(prev_day)
        return TimePeriodContext("week", f"Last week ({start:%b %d} – {end:%b %d, %Y})",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "this month" / "current month" ---
    if re.search(r"\b(this|current)\s+month\b", q):
        start = today.replace(day=1)
        if today.month == 12:
            end = datetime(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
        label = f"{start:%B %Y}"
        return TimePeriodContext("month", label,
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "next month" ---
    if re.search(r"\bnext\s+month\b", q):
        if today.month == 12:
            start = datetime(today.year + 1, 1, 1)
        else:
            start = datetime(today.year, today.month + 1, 1)
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(start.year, start.month + 1, 1) - timedelta(days=1)
        return TimePeriodContext("month", f"{start:%B %Y}",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "last month" / "previous month" ---
    if re.search(r"\b(last|previous)\s+month\b", q):
        first_of_current = today.replace(day=1)
        end = first_of_current - timedelta(days=1)
        start = end.replace(day=1)
        return TimePeriodContext("month", f"{start:%B %Y}",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "Q1 2025" / "quarter 2 2025" ---
    m = re.search(r"\bq([1-4])\s*(\d{4})\b", q)
    if m:
        qn, yr = int(m.group(1)), int(m.group(2))
        start, end = _quarter_range(qn, yr)
        return TimePeriodContext("quarter", f"Q{qn} {yr}",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "this quarter" ---
    if re.search(r"\b(this|current)\s+quarter\b", q):
        qn = (today.month - 1) // 3 + 1
        start, end = _quarter_range(qn, today.year)
        return TimePeriodContext("quarter", f"Q{qn} {today.year}",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "March 2025", "march 2025" ---
    m = re.search(r"\b(" + "|".join(_MONTH_MAP.keys()) + r")\s+(\d{4})\b", q)
    if m:
        mn = _MONTH_MAP[m.group(1)]
        yr = int(m.group(2))
        start = datetime(yr, mn, 1)
        if mn == 12:
            end = datetime(yr + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(yr, mn + 1, 1) - timedelta(days=1)
        return TimePeriodContext("month", f"{start:%B %Y}",
                                start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

    # --- "2025" (bare year) ---
    m = re.search(r"\b(20\d{2})\b", q)
    if m:
        yr = int(m.group(1))
        # Only treat as year if it looks intentional (not just a random number)
        if any(kw in q for kw in ["year", "annual", "in " + m.group(1), "for " + m.group(1)]):
            return TimePeriodContext("year", str(yr),
                                    f"{yr}-01-01", f"{yr}-12-31")

    return None
