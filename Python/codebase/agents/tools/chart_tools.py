"""Chart generation tools for agents"""
from typing import List, Dict, Any, Optional
import pandas as pd

from data_layer.query_engine import QueryEngine


class ChartTools:
    """Tools for generating chart configurations"""

    # Color palettes for charts
    COLORS = {
        "primary": [
            "rgba(59, 130, 246, 0.8)",   # Blue
            "rgba(16, 185, 129, 0.8)",   # Green
            "rgba(245, 158, 11, 0.8)",   # Amber
            "rgba(239, 68, 68, 0.8)",    # Red
            "rgba(139, 92, 246, 0.8)",   # Purple
            "rgba(236, 72, 153, 0.8)",   # Pink
            "rgba(20, 184, 166, 0.8)",   # Teal
            "rgba(249, 115, 22, 0.8)",   # Orange
        ],
        "status": {
            "open": "rgba(239, 68, 68, 0.8)",      # Red
            "in_progress": "rgba(245, 158, 11, 0.8)",  # Amber
            "resolved": "rgba(16, 185, 129, 0.8)",    # Green
            "closed": "rgba(107, 114, 128, 0.8)",    # Gray
            "draft": "rgba(59, 130, 246, 0.8)",     # Blue
            "answered": "rgba(16, 185, 129, 0.8)",   # Green
        },
        "priority": {
            "critical": "rgba(239, 68, 68, 0.9)",   # Red
            "high": "rgba(249, 115, 22, 0.8)",      # Orange
            "medium": "rgba(245, 158, 11, 0.8)",    # Amber
            "low": "rgba(16, 185, 129, 0.8)",       # Green
        },
        "severity": {
            "critical": "rgba(239, 68, 68, 0.9)",
            "severe": "rgba(249, 115, 22, 0.8)",
            "moderate": "rgba(245, 158, 11, 0.8)",
            "minor": "rgba(16, 185, 129, 0.8)",
        }
    }

    def __init__(self, query_engine: QueryEngine):
        self.qe = query_engine

    def create_bar_chart(
        self,
        labels: List[str],
        data: List[float],
        title: str,
        dataset_label: str = "Count",
        horizontal: bool = False
    ) -> Dict:
        """Create a bar chart configuration"""
        colors = self._get_colors(labels)

        return {
            "type": "bar",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": dataset_label,
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": [c.replace("0.8", "1") for c in colors],
                    "borderWidth": 1
                }]
            },
            "options": {
                "indexAxis": "y" if horizontal else "x",
                "responsive": True,
                "plugins": {
                    "legend": {"display": False}
                }
            }
        }

    def create_pie_chart(
        self,
        labels: List[str],
        data: List[float],
        title: str
    ) -> Dict:
        """Create a pie chart configuration"""
        colors = self._get_colors(labels)

        return {
            "type": "pie",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": "rgba(255, 255, 255, 1)",
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "legend": {"position": "right"}
                }
            }
        }

    def create_doughnut_chart(
        self,
        labels: List[str],
        data: List[float],
        title: str,
        center_text: Optional[str] = None
    ) -> Dict:
        """Create a doughnut chart configuration"""
        colors = self._get_colors(labels)

        config = {
            "type": "doughnut",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [{
                    "data": data,
                    "backgroundColor": colors,
                    "borderColor": "rgba(255, 255, 255, 1)",
                    "borderWidth": 2
                }]
            },
            "options": {
                "responsive": True,
                "cutout": "60%",
                "plugins": {
                    "legend": {"position": "right"}
                }
            }
        }

        if center_text:
            config["centerText"] = center_text

        return config

    def create_line_chart(
        self,
        labels: List[str],
        datasets: List[Dict],
        title: str
    ) -> Dict:
        """Create a line chart configuration"""
        formatted_datasets = []
        for i, ds in enumerate(datasets):
            color = self.COLORS["primary"][i % len(self.COLORS["primary"])]
            formatted_datasets.append({
                "label": ds.get("label", f"Series {i+1}"),
                "data": ds.get("data", []),
                "borderColor": color.replace("0.8", "1"),
                "backgroundColor": color,
                "fill": ds.get("fill", False),
                "tension": 0.4
            })

        return {
            "type": "line",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": formatted_datasets
            },
            "options": {
                "responsive": True,
                "interaction": {
                    "intersect": False,
                    "mode": "index"
                },
                "plugins": {
                    "legend": {"position": "top"}
                }
            }
        }

    def create_timeline_line_chart(
        self,
        labels: List[str],
        datasets: List[Dict],
        title: str,
        *,
        period_type: Optional[str] = None,
    ) -> Dict:
        """
        Line chart tuned for time-series readability.

        Frontend uses Chart.js; this config focuses on tick density control.
        """
        # Heuristic: more granular periods -> fewer ticks visible.
        max_ticks = {
            "year": 10,
            "quarter": 8,
            "month": 12,
            "week": 14,
            "custom": 14,
            "day": 18,
        }.get((period_type or "").lower(), 12)

        chart = self.create_line_chart(labels, datasets, title)
        chart["options"].update(
            {
                "scales": {
                    "x": {
                        "ticks": {
                            "maxTicksLimit": max_ticks,
                            "autoSkip": True,
                            # Keep labels horizontal for compactness; Chart.js will skip if needed.
                            "maxRotation": 0,
                        },
                        "grid": {"display": False},
                    }
                }
            }
        )
        return chart

    def create_timeline_bar_chart(
        self,
        labels: List[str],
        data: List[float],
        title: str,
        *,
        period_type: Optional[str] = None,
        dataset_label: str = "Count",
    ) -> Dict:
        """
        Bar chart tuned for time-series readability.
        """
        max_ticks = {
            "year": 10,
            "quarter": 8,
            "month": 12,
            "week": 14,
            "custom": 14,
            "day": 18,
        }.get((period_type or "").lower(), 12)

        config = self.create_bar_chart(
            labels=labels,
            data=data,
            title=title,
            dataset_label=dataset_label,
            horizontal=False,
        )
        # create_bar_chart sets legend off for bar; keep it.
        config["options"].update(
            {
                "scales": {
                    "x": {
                        "ticks": {
                            "maxTicksLimit": max_ticks,
                            "autoSkip": True,
                            "maxRotation": 0,
                        },
                        "grid": {"display": False},
                    }
                }
            }
        )
        return config

    def create_kpi_card(
        self,
        title: str,
        value: Any,
        unit: str = "",
        trend: str = "stable",
        change: str = "",
        subtitle: str = ""
    ) -> Dict:
        """Create a KPI card configuration"""
        return {
            "type": "kpi",
            "title": title,
            "data": {
                "value": value,
                "unit": unit,
                "trend": trend,  # up, down, stable
                "change": change,
                "subtitle": subtitle
            }
        }

    def create_table(
        self,
        headers: List[str],
        rows: List[List[Any]],
        title: str
    ) -> Dict:
        """Create a table configuration"""
        return {
            "type": "table",
            "title": title,
            "data": {
                "headers": headers,
                "rows": rows
            }
        }

    def create_stacked_bar_chart(
        self,
        labels: List[str],
        datasets: List[Dict],
        title: str,
        horizontal: bool = False
    ) -> Dict:
        """Create a stacked bar chart configuration"""
        formatted_datasets = []
        for i, ds in enumerate(datasets):
            color = self.COLORS["primary"][i % len(self.COLORS["primary"])]
            formatted_datasets.append({
                "label": ds.get("label", f"Series {i+1}"),
                "data": ds.get("data", []),
                "backgroundColor": color,
                "borderColor": color.replace("0.8", "1"),
                "borderWidth": 1
            })

        return {
            "type": "bar",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": formatted_datasets
            },
            "options": {
                "indexAxis": "y" if horizontal else "x",
                "responsive": True,
                "scales": {
                    "x": {"stacked": True},
                    "y": {"stacked": True}
                },
                "plugins": {
                    "legend": {"position": "top"}
                }
            }
        }

    def _get_colors(self, labels: List[str]) -> List[str]:
        """Get appropriate colors for labels"""
        colors = []
        for label in labels:
            label_lower = str(label).lower()

            # Check status colors
            if label_lower in self.COLORS["status"]:
                colors.append(self.COLORS["status"][label_lower])
            # Check priority colors
            elif label_lower in self.COLORS["priority"]:
                colors.append(self.COLORS["priority"][label_lower])
            # Check severity colors
            elif label_lower in self.COLORS["severity"]:
                colors.append(self.COLORS["severity"][label_lower])
            else:
                # Use primary colors cyclically
                idx = len(colors) % len(self.COLORS["primary"])
                colors.append(self.COLORS["primary"][idx])

        return colors

    def auto_chart(
        self,
        data: List[Dict],
        group_column: str,
        value_column: str = "count",
        title: str = "Chart"
    ) -> Dict:
        """Automatically select best chart type based on data"""
        if not data:
            return self.create_kpi_card(title, 0, "items")

        labels = [str(d.get(group_column, "Unknown")) for d in data]
        values = [float(d.get(value_column, 0)) for d in data]

        # Choose chart type based on data characteristics
        num_categories = len(labels)

        if num_categories <= 5:
            return self.create_doughnut_chart(labels, values, title)
        elif num_categories <= 10:
            return self.create_bar_chart(labels, values, title)
        else:
            # For many categories, use horizontal bar
            return self.create_bar_chart(
                labels[:15], values[:15], f"{title} (Top 15)",
                horizontal=True
            )
