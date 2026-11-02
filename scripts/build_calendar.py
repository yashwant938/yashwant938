#!/usr/bin/env python3
"""Render an authentic GitHub contribution calendar as a self-contained SVG.

The input is the contributionCalendar object, not a complete GraphQL response.
Only Python's standard library is required. This program never accesses a network.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from html import escape
import json
from pathlib import Path
import re
import sys


PALETTE = {
    "NONE": "#161b22",
    "FIRST_QUARTILE": "#4c1020",
    "SECOND_QUARTILE": "#8b1832",
    "THIRD_QUARTILE": "#d73552",
    "FOURTH_QUARTILE": "#ff6b81",
}
LEVEL_LABELS = {
    "NONE": "No contributions",
    "FIRST_QUARTILE": "Low activity",
    "SECOND_QUARTILE": "Medium-low activity",
    "THIRD_QUARTILE": "Medium-high activity",
    "FOURTH_QUARTILE": "High activity",
}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class CalendarError(ValueError):
    """The supplied calendar cannot be represented faithfully."""


def integer(value: object, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CalendarError(f"{location} must be a non-negative integer")
    return value


def iso_date(value: object, location: str) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise CalendarError(f"{location} must be a date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CalendarError(f"{location} is not a valid date: {value}") from exc


def load_calendar(data: object, year: int, updated: date) -> tuple[int, dict[date, dict], list[str]]:
    if not isinstance(data, dict):
        raise CalendarError("input must be a JSON object containing totalContributions and weeks")
    total = integer(data.get("totalContributions"), "totalContributions")
    weeks = data.get("weeks")
    if not isinstance(weeks, list):
        raise CalendarError("weeks must be an array")
    days: dict[date, dict] = {}
    warnings: list[str] = []
    for week_index, week in enumerate(weeks):
        location = f"weeks[{week_index}]"
        if not isinstance(week, dict) or not isinstance(week.get("contributionDays"), list):
            raise CalendarError(f"{location}.contributionDays must be an array")
        for day_index, day in enumerate(week["contributionDays"]):
            location = f"weeks[{week_index}].contributionDays[{day_index}]"
            if not isinstance(day, dict):
                raise CalendarError(f"{location} must be an object")
            day_date = iso_date(day.get("date"), f"{location}.date")
            if day_date in days:
                raise CalendarError(f"duplicate contribution date: {day_date.isoformat()}")
            count = integer(day.get("contributionCount"), f"{location}.contributionCount")
            level = day.get("contributionLevel")
            if not isinstance(level, str) or level not in PALETTE:
                raise CalendarError(f"{location}.contributionLevel must be one of {', '.join(PALETTE)}")
            if (count == 0) != (level == "NONE"):
                raise CalendarError(f"{location}: contributionCount and contributionLevel contradict one another")
            expected_weekday = (day_date.weekday() + 1) % 7
            if "weekday" in day:
                weekday = integer(day["weekday"], f"{location}.weekday")
                if weekday != expected_weekday:
                    raise CalendarError(f"{location}.weekday must be {expected_weekday} for {day_date.isoformat()}")
            if count and day_date.year != year:
                raise CalendarError(f"nonzero contribution date {day_date.isoformat()} falls outside requested year {year}")
            if count and day_date > updated:
                raise CalendarError(f"nonzero contribution date {day_date.isoformat()} falls after --updated {updated.isoformat()}")
            days[day_date] = {"date": day_date.isoformat(), "count": count, "level": level}
    visible_sum = sum(day["count"] for day_date, day in days.items() if day_date.year == year and day_date <= updated)
    if total != visible_sum:
        warnings.append(
            f"API totalContributions ({total}) differs from the sum of displayed daily counts ({visible_sum}); "
            "the supplied API total is preserved and no daily values are changed."
        )
    return total, days, warnings


def render_calendar(data: object, username: str, year: int, updated: date) -> tuple[str, list[str]]:
    if not 2 <= year <= 9998:
        raise CalendarError("year must be between 2 and 9998")
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", username):
        raise CalendarError("username must be a GitHub-style username of 1 to 39 letters, digits or hyphens")
    total, days, warnings = load_calendar(data, year, updated)
    first_day, last_day = date(year, 1, 1), date(year, 12, 31)
    grid_start = first_day - timedelta(days=(first_day.weekday() + 1) % 7)
    week_count = ((last_day - grid_start).days + 7) // 7
    grid_x, grid_y, step, cell = 76, 143, 16, 12
    known_days = sum(first_day <= day_date <= min(last_day, updated) for day_date in days)
    elapsed_days = max(0, (min(last_day, updated) - first_day).days + 1)
    missing_days = max(0, elapsed_days - known_days)
    title = f"{username}: {total:,} public contributions in {year}"
    description = (
        f"Contribution calendar for {username}, January through December {year}. "
        f"GitHub's public profile reports {total:,} contributions. Updated {updated.isoformat()}. "
        "Columns are weeks and rows run Sunday through Saturday. "
        "Crimson shades preserve GitHub's contribution levels. Each known day has its exact count in a title. "
        "Future dates are neutral; dates absent from the input are identified as unavailable."
    )
    if missing_days:
        description += f" {missing_days} elapsed dates have no supplied data."
    if warnings:
        description += " " + " ".join(warnings)
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="300" viewBox="0 0 960 300" role="img" aria-labelledby="calendar-title calendar-description">',
        f'  <title id="calendar-title">{escape(title)}</title>',
        f'  <desc id="calendar-description">{escape(description)}</desc>',
        '  <rect x="0.5" y="0.5" width="959" height="299" rx="18" fill="#0d1117" stroke="#30363d"/>',
        '  <path d="M33 30 H57" stroke="#ff6b81" stroke-width="3" stroke-linecap="round"/>',
        '  <g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">',
        '    <text x="69" y="35" fill="#a9b1bd" font-size="11" font-weight="600" letter-spacing="1.6">CONTRIBUTION ACTIVITY</text>',
        f'    <text x="32" y="81" fill="#f0f6fc" font-size="34" font-weight="700" letter-spacing="-0.8">{total:,}</text>',
        f'    <text x="33" y="103" fill="#8b949e" font-size="13">public contributions in {year} <tspan fill="#484f58"> / </tspan><tspan fill="#c9d1d9">@{escape(username)}</tspan></text>',
        '    <rect x="861" y="27" width="67" height="29" rx="14.5" fill="#28131c" stroke="#4c1020"/>',
        f'    <text x="894.5" y="46" text-anchor="middle" fill="#ff9bae" font-size="12" font-weight="600">{year}</text>',
    ]
    for month in range(1, 13):
        month_start = date(year, month, 1)
        column = (month_start - grid_start).days // 7
        svg.append(f'    <text x="{grid_x + column * step}" y="130" fill="#8b949e" font-size="11">{MONTHS[month - 1]}</text>')
    for label, weekday in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        svg.append(f'    <text x="34" y="{grid_y + weekday * step + 10}" fill="#8b949e" font-size="11">{label}</text>')
    svg.append('    <g aria-label="Contribution days">')
    for column in range(week_count):
        for weekday in range(7):
            day_date = grid_start + timedelta(days=column * 7 + weekday)
            if day_date.year != year:
                continue
            day = days.get(day_date)
            attributes = f'x="{grid_x + column * step}" y="{grid_y + weekday * step}" width="{cell}" height="{cell}" rx="2.5"'
            if day_date > updated:
                fill, extra = "#161b22", ' opacity="0.35"'
                tooltip = f"{day_date.isoformat()}: Future date"
                data_attributes = ' data-state="future"'
            elif day is None:
                fill, extra = "#10151c", ' stroke="#30363d" stroke-width="0.6"'
                tooltip = f"{day_date.isoformat()}: No data supplied"
                data_attributes = ' data-state="unavailable"'
            else:
                fill, extra = PALETTE[day["level"]], ""
                noun = "contribution" if day["count"] == 1 else "contributions"
                tooltip = f"{day_date.isoformat()}: {day['count']:,} {noun}; {LEVEL_LABELS[day['level']]}"
                data_attributes = f' data-count="{day["count"]}" data-level="{day["level"]}"'
            svg.append(f'      <rect {attributes} fill="{fill}"{extra} data-date="{day_date.isoformat()}"{data_attributes}><title>{escape(tooltip)}</title></rect>')
    svg.append('    </g>')
    footer = f"Updated {updated.isoformat()}"
    if missing_days:
        footer += f" · {missing_days} dates unavailable"
    svg.append(f'    <text x="33" y="278" fill="#6e7681" font-size="11">{escape(footer)}</text>')
    svg.append('    <text x="776" y="278" fill="#8b949e" font-size="11">Less</text>')
    for index, (level, color) in enumerate(PALETTE.items()):
        svg.append(f'    <rect x="{807 + index * 16}" y="268" width="12" height="12" rx="2.5" fill="{color}"><title>{LEVEL_LABELS[level]}</title></rect>')
    svg.append('    <text x="895" y="278" fill="#8b949e" font-size="11">More</text>')
    svg.extend(['  </g>', '</svg>', ''])
    return "\n".join(svg), warnings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="ContributionCalendar JSON file")
    parser.add_argument("--output", required=True, type=Path, help="Destination SVG file")
    parser.add_argument("--username", required=True)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--updated", required=True, help="Data snapshot date, YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        updated = iso_date(args.updated, "--updated")
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        svg, warnings = render_calendar(data, args.username, args.year, updated)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding="utf-8", newline="\n")
    except (OSError, json.JSONDecodeError, CalendarError) as exc:
        parser.error(str(exc))
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
