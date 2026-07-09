"""Drill-down follow-up question generator for time-based queries."""
from typing import Dict, Any, List
from data_layer.time_period_parser import TimePeriodContext
from datetime import datetime, timedelta


class DrillDownTools:
    """Generate time drill-down follow-up questions at the next granularity level.

    Hierarchy: year -> quarter -> month -> week -> day
    """

    # Next-level granularity map
    _DRILL_MAP = {
        "year": "quarter",
        "quarter": "month",
        "month": "week",
        "week": "day",
    }

    def generate_drill_down_followups(
        self,
        entity: str,
        period: TimePeriodContext,
    ) -> Dict[str, Any]:
        """Return a list of follow-up questions at the next granularity."""
        next_level = self._DRILL_MAP.get(period.period_type)
        if not next_level:
            return {"follow_up_questions": []}

        try:
            start = datetime.fromisoformat(period.start_date)
            end = datetime.fromisoformat(period.end_date)
        except (ValueError, TypeError):
            return {"follow_up_questions": []}

        questions: List[str] = []

        if next_level == "quarter":
            # Break year into quarters
            year = start.year
            for q in range(1, 5):
                questions.append(f"Show {entity} in Q{q} {year}")

        elif next_level == "month":
            # Break quarter/period into months
            current = start.replace(day=1)
            while current <= end:
                questions.append(f"Show {entity} in {current:%B %Y}")
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

        elif next_level == "week":
            # Break month into weeks
            current = start
            week_num = 1
            while current <= end:
                week_end = min(current + timedelta(days=6), end)
                questions.append(
                    f"Show {entity} for week of {current:%b %d} – {week_end:%b %d, %Y}"
                )
                current = current + timedelta(days=7)
                week_num += 1
                if week_num > 5:
                    break

        elif next_level == "day":
            # Break week into days (limit to 7)
            current = start
            while current <= end and (current - start).days < 7:
                questions.append(f"Show {entity} on {current:%Y-%m-%d}")
                current += timedelta(days=1)

        # Limit to 3 questions
        return {"follow_up_questions": questions[:3]}
