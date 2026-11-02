#!/usr/bin/env python3
"""Refresh the red calendar from the same public data shown on GitHub's profile."""

import argparse
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
import re
import urllib.parse
import urllib.request

from build_calendar import PALETTE, render_calendar


class PublicCalendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tooltips = {}
        self.tooltip_id = None
        self.tooltip_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'data-date' in attrs and 'data-level' in attrs:
            day = attrs['data-date']
            if day in self.cells:
                raise ValueError(f'Duplicate public calendar date: {day}')
            self.cells[day] = (attrs['id'], int(attrs['data-level']))
        if tag == 'tool-tip' and attrs.get('for'):
            self.tooltip_id = attrs['for']
            self.tooltip_text = []

    def handle_data(self, text):
        if self.tooltip_id:
            self.tooltip_text.append(text)

    def handle_endtag(self, tag):
        if tag == 'tool-tip' and self.tooltip_id:
            self.tooltips[self.tooltip_id] = ''.join(self.tooltip_text).strip()
            self.tooltip_id = None


def parse_calendar(html, as_of):
    parser = PublicCalendar()
    parser.feed(html)
    first_day = date(as_of.year, 1, 1)
    weeks = {}
    levels = list(PALETTE)
    for offset in range((as_of - first_day).days + 1):
        day = first_day + timedelta(days=offset)
        key = day.isoformat()
        if key not in parser.cells:
            raise ValueError(f'GitHub response is missing {key}; keeping the previous SVG')
        cell_id, level = parser.cells[key]
        text = parser.tooltips.get(cell_id, '')
        match = re.match(r'^(No|[\d,]+) contributions? on\b', text)
        if not match or not 0 <= level < len(levels):
            raise ValueError(f'Unrecognized public contribution data for {key}')
        count = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
        weekday = (day.weekday() + 1) % 7
        week = (day - timedelta(days=weekday)).isoformat()
        weeks.setdefault(week, []).append({
            'date': key,
            'weekday': weekday,
            'contributionCount': count,
            'contributionLevel': levels[level],
        })
    return {
        'totalContributions': sum(day['contributionCount'] for days in weeks.values() for day in days),
        'weeks': [{'contributionDays': days} for days in weeks.values()],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='yashwant938')
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'assets' / 'contributions-red.svg')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.username):
        parser.error('Invalid GitHub username')
    query = urllib.parse.urlencode({'from': f'{args.as_of.year}-01-01', 'to': args.as_of.isoformat()})
    url = f'https://github.com/users/{args.username}/contributions?{query}'
    request = urllib.request.Request(url, headers={
        'User-Agent': 'GitHub-Profile-Contribution-Calendar',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    with urllib.request.urlopen(request, timeout=40) as response:
        html = response.read().decode('utf-8')
    calendar = parse_calendar(html, args.as_of)
    svg, warnings = render_calendar(calendar, args.username, args.as_of.year, args.as_of)
    if warnings:
        raise ValueError('; '.join(warnings))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix('.svg.tmp')
    temporary.write_text(svg, encoding='utf-8', newline='\n')
    temporary.replace(args.output)
    print(f"Updated {args.output.name}: {calendar['totalContributions']} public-profile contributions through {args.as_of}")


if __name__ == '__main__':
    main()
