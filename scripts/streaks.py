"""Calculate public contribution-day streaks and render matching profile cards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from typing import Mapping


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


@dataclass(frozen=True)
class Streak:
    length: int = 0
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True)
class StreakSummary:
    current: Streak
    longest: Streak
    as_of: date
    first_date: date | None
    today_contributions: int = 0
    longest_year: int | None = None


def calculate_streaks(counts: Mapping[date, int], as_of: date, *, longest_year: int | None = None) -> StreakSummary:
    """Count active days, allowing the unfinished current day to remain open.

    History must be complete through as_of. A missing date is not a zero day.
    Tied longest runs show the most recent run; future data is ignored.
    longest_year limits the record to that calendar year. The current streak
    always uses the full history so January does not reset an ongoing run.
    """
    if longest_year is not None and (
        isinstance(longest_year, bool) or not isinstance(longest_year, int) or not 1 <= longest_year <= as_of.year
    ):
        raise ValueError("Longest-streak year must be an elapsed or current calendar year")
    for day, count in counts.items():
        if not isinstance(day, date):
            raise ValueError("Contribution dates must be date objects")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Contribution counts must be non-negative integers")
    days = sorted(day for day in counts if day <= as_of)
    if not days:
        return StreakSummary(Streak(), Streak(), as_of, None, longest_year=longest_year)
    first = days[0]
    if len(days) != (as_of - first).days + 1:
        raise ValueError("Streak history must contain every date through the snapshot date")

    longest, run_start = Streak(), None
    for day in days:
        if counts[day] > 0 and (longest_year is None or day.year == longest_year):
            if run_start is None:
                run_start = day
            run = Streak((day - run_start).days + 1, run_start, day)
            if run.length >= longest.length:
                longest = run
        else:
            run_start = None

    current = Streak()
    end = as_of if counts[as_of] or as_of == first else as_of - timedelta(days=1)
    if counts.get(end, 0):
        start = end
        while start > first and counts.get(start - timedelta(days=1), 0):
            start -= timedelta(days=1)
        current = Streak((end - start).days + 1, start, end)
    return StreakSummary(current, longest, as_of, first, counts[as_of], longest_year)


def date_label(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"


def streak_dates(streak: Streak) -> str:
    if not streak.length:
        return "No active days yet"
    if streak.start == streak.end:
        return date_label(streak.start)
    return f"{date_label(streak.start)} – {date_label(streak.end)}"


def render_streaks(summary: StreakSummary, username: str, *, mobile: bool = False) -> str:
    """Self-contained, static SVG: no remote badge service or tracking requests."""
    width, height = (400, 278) if mobile else (960, 158)
    if summary.longest_year is not None:
        scope = f"{summary.longest_year} calendar"
        longest_heading = f"LONGEST STREAK IN {summary.longest_year}"
        longest_name = f"Longest streak in {summary.longest_year}"
    else:
        scope = f"All-time since {summary.first_date.year}" if summary.first_date else "Public contribution days"
        longest_heading, longest_name = "LONGEST STREAK", "Longest streak"
    current_label = f"{summary.current.length} {'day' if summary.current.length == 1 else 'days'}"
    longest_label = f"{summary.longest.length} {'day' if summary.longest.length == 1 else 'days'}"
    title = f"{username}: current streak {current_label}; {longest_name.lower()} {longest_label}"
    description = (
        f"{scope}. Current streak: {current_label}, {streak_dates(summary.current)}. "
        f"{longest_name}: {longest_label}, {streak_dates(summary.longest)}. "
        f"Updated {summary.as_of.isoformat()} UTC. Each day with at least one public GitHub contribution "
        "counts once. A missed completed day breaks the current streak; today stays open until the next date."
    )
    if summary.longest_year is not None:
        description += (
            f" The longest streak covers only {summary.longest_year}, matching the chart. "
            "The current streak continues across year boundaries."
        )
    scope_attribute = f' data-longest-year="{summary.longest_year}"' if summary.longest_year is not None else ''
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="streak-title streak-description"{scope_attribute}>',
        f'  <title id="streak-title">{escape(title)}</title>',
        f'  <desc id="streak-description">{escape(description)}</desc>',
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="18" fill="#0d1117" stroke="#30363d"/>',
        '  <g font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica, Arial, sans-serif">',
    ]
    if mobile:
        svg.append('    <path d="M24 119 H376 M24 228 H376" stroke="#252b35"/>')
    else:
        svg.append('    <path d="M480 23 V112 M32 126 H928" stroke="#252b35"/>')

    panels = ((summary.current, "CURRENT STREAK"), (summary.longest, longest_heading))
    for index, (streak, label) in enumerate(panels):
        x, y = (24, 115 * index) if mobile else (32 + 486 * index, 0)
        label_y, value_y, dates_y = ((29, 75, 99) if mobile else (32, 85, 111))
        number_size = 38 if mobile else 44
        unit = "day" if streak.length == 1 else "days"
        color = "#ff8fa6" if index == 0 else "#f0f6fc"
        dates = streak_dates(streak) if streak.length else ("No current streak" if index == 0 else "No active days yet")
        svg.extend([
            f'    <g data-streak="{"current" if index == 0 else "longest"}" data-days="{streak.length}" transform="translate({x} {y})">',
            '      <rect x="0" y="19" width="3" height="12" rx="1.5" fill="#ff6b81"/>',
            f'      <text x="13" y="{label_y}" fill="#b0b8c5" font-size="11" font-weight="600" letter-spacing="1.4">{label}</text>',
            f'      <text x="0" y="{value_y}" fill="{color}" font-size="{number_size}" font-weight="700" letter-spacing="-0.6">{streak.length:,}<tspan dx="5" fill="#a9b1bd" font-size="16" font-weight="400" letter-spacing="0">{unit}</tspan></text>',
            f'      <text x="1" y="{dates_y}" fill="#8b949e" font-size="12">{escape(dates)}</text>',
            '    </g>',
        ])
    if mobile:
        svg.extend([
            f'    <text x="24" y="248" fill="#8b949e" font-size="11">Public activity · {escape(scope)}</text>',
            f'    <text x="24" y="265" fill="#6e7681" font-size="10.5">Updated {summary.as_of.isoformat()} · UTC</text>',
        ])
    else:
        svg.extend([
            f'    <text x="32" y="146" fill="#8b949e" font-size="11">Public contribution days · {escape(scope)}</text>',
            f'    <text x="928" y="146" text-anchor="end" fill="#6e7681" font-size="11">Updated {summary.as_of.isoformat()} · UTC</text>',
        ])
    svg.extend(['  </g>', '</svg>', ''])
    return "\n".join(svg)
