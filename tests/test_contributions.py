"""Offline regression checks for public counts, streak boundaries and refreshes."""

from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from build_calendar import CalendarError, render_calendar
from streaks import calculate_streaks, render_streaks
from update_contributions import fetch_history, main, parse_calendar


def history(start, values):
    first = date.fromisoformat(start)
    return {first + timedelta(days=index): count for index, count in enumerate(values)}


def calendar(counts):
    return {
        'totalContributions': sum(counts.values()),
        'weeks': [{'contributionDays': [
            {'date': day.isoformat(), 'contributionCount': count,
             'contributionLevel': 'FIRST_QUARTILE' if count else 'NONE'}
            for day, count in sorted(counts.items())
        ]}],
    }


class StreakTests(unittest.TestCase):
    def test_missed_yesterday_four_contributions_today_is_one_day(self):
        summary = calculate_streaks(history('2026-11-01', [3, 2, 0, 4]), date(2026, 11, 4))
        self.assertEqual(summary.current.length, 1)
        self.assertEqual(summary.current.start, date(2026, 11, 4))
        self.assertEqual(summary.longest.length, 2)
        self.assertEqual(summary.today_contributions, 4)

    def test_consecutive_days_count_once_regardless_of_volume(self):
        summary = calculate_streaks(history('2026-11-01', [1, 20, 1, 100]), date(2026, 11, 4))
        self.assertEqual(summary.current.length, 4)
        self.assertEqual(summary.longest.length, 4)

    def test_unfinished_today_keeps_yesterdays_streak(self):
        summary = calculate_streaks(history('2026-11-01', [1, 2, 1, 0]), date(2026, 11, 4))
        self.assertEqual(summary.current.length, 3)
        self.assertEqual(summary.current.end, date(2026, 11, 3))

    def test_missed_completed_day_breaks_the_streak(self):
        summary = calculate_streaks(history('2026-11-01', [1, 2, 0, 0]), date(2026, 11, 4))
        self.assertEqual(summary.current.length, 0)
        self.assertEqual(summary.longest.length, 2)

    def test_longest_uses_older_years_and_crosses_new_year(self):
        summary = calculate_streaks(history('2025-12-29', [1, 1, 4, 1, 0, 1]), date(2026, 1, 3))
        self.assertEqual(summary.current.length, 1)
        self.assertEqual(summary.longest.length, 4)
        self.assertEqual(summary.longest.start, date(2025, 12, 29))
        self.assertEqual(summary.longest.end, date(2026, 1, 1))

    def test_yearly_longest_excludes_the_2023_record(self):
        start, as_of = date(2023, 8, 13), date(2026, 11, 4)
        counts = history(start.isoformat(), [0] * ((as_of - start).days + 1))
        counts.update(history('2023-08-14', [1] * 21))
        counts.update(history('2026-10-03', [2, 1, 19, 2, 1, 1, 6, 14]))
        counts[as_of] = 4
        yearly = calculate_streaks(counts, as_of, longest_year=2026)
        all_time = calculate_streaks(counts, as_of)
        self.assertEqual(all_time.longest.length, 21)
        self.assertEqual(yearly.longest.length, 8)
        self.assertEqual(yearly.longest.start, date(2026, 10, 3))
        self.assertEqual(yearly.longest.end, date(2026, 10, 10))
        self.assertEqual(yearly.current.length, 1)
        self.assertEqual(yearly.longest_year, 2026)
        self.assertEqual(sum(count for day, count in counts.items() if day.year == 2026 and day.month == 8), 0)

    def test_current_crosses_new_year_but_yearly_record_is_clipped(self):
        summary = calculate_streaks(history('2025-12-29', [1, 1, 1, 1, 1]),
                                    date(2026, 1, 2), longest_year=2026)
        self.assertEqual(summary.current.length, 5)
        self.assertEqual(summary.current.start, date(2025, 12, 29))
        self.assertEqual(summary.longest.length, 2)
        self.assertEqual(summary.longest.start, date(2026, 1, 1))

    def test_year_scope_is_prominent_in_desktop_mobile_and_empty_cards(self):
        for counts in ({}, history('2026-11-01', [1, 1, 0, 4])):
            summary = calculate_streaks(counts, date(2026, 11, 4), longest_year=2026)
            for mobile in (False, True):
                with self.subTest(empty=not counts, mobile=mobile):
                    svg = render_streaks(summary, 'yashwant938', mobile=mobile)
                    self.assertEqual(ET.fromstring(svg).attrib['data-longest-year'], '2026')
                    self.assertIn('LONGEST STREAK IN 2026', svg)
                    self.assertIn('2026 calendar', svg)
                    self.assertNotIn('All-time', svg)

    def test_invalid_longest_year_is_rejected(self):
        for year in (True, 0, 2027, '2026'):
            with self.subTest(year=year), self.assertRaises(ValueError):
                calculate_streaks({}, date(2026, 11, 4), longest_year=year)

    def test_leap_day_is_a_normal_consecutive_day(self):
        summary = calculate_streaks(history('2024-02-28', [1, 2, 3]), date(2024, 3, 1))
        self.assertEqual(summary.current.length, 3)

    def test_tied_longest_runs_show_most_recent_dates(self):
        summary = calculate_streaks(history('2026-11-01', [1, 1, 0, 1, 1]), date(2026, 11, 5))
        self.assertEqual(summary.longest.start, date(2026, 11, 4))
        self.assertEqual(summary.longest.end, date(2026, 11, 5))

    def test_empty_history_and_zero_activity(self):
        for counts in ({}, history('2026-11-01', [0, 0, 0, 0])):
            with self.subTest(counts=counts):
                summary = calculate_streaks(counts, date(2026, 11, 4))
                self.assertEqual(summary.current.length, 0)
                self.assertEqual(summary.longest.length, 0)
                ET.fromstring(render_streaks(summary, 'yashwant938'))

    def test_future_dates_do_not_extend_streaks(self):
        summary = calculate_streaks(history('2026-11-01', [1, 1, 1, 5]), date(2026, 11, 3))
        self.assertEqual(summary.current.length, 3)
        self.assertEqual(summary.longest.end, date(2026, 11, 3))

    def test_missing_dates_and_missing_snapshot_are_not_zero_days(self):
        for counts in ({date(2026, 11, 1): 1, date(2026, 11, 3): 1},
                       {date(2026, 11, 1): 1, date(2026, 11, 2): 1}):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                calculate_streaks(counts, date(2026, 11, 3))

    def test_invalid_counts_fail_instead_of_inflating_the_streak(self):
        for count in (-1, True, 1.5, '4'):
            with self.subTest(count=count), self.assertRaises(ValueError):
                calculate_streaks({date(2026, 11, 4): count}, date(2026, 11, 4))

    def test_responsive_cards_have_matching_numbers_and_dates(self):
        summary = calculate_streaks(history('2026-11-01', [1, 1, 0, 4]), date(2026, 11, 4))
        for mobile, width in ((False, '960'), (True, '400')):
            with self.subTest(mobile=mobile):
                svg = render_streaks(summary, 'yashwant938', mobile=mobile)
                root = ET.fromstring(svg)
                self.assertEqual(root.attrib['width'], width)
                self.assertEqual({item.attrib['data-streak']: item.attrib['data-days']
                                  for item in root.iter() if 'data-streak' in item.attrib},
                                 {'current': '1', 'longest': '2'})
                self.assertIn('Nov 4, 2026', svg)
                self.assertIn('Nov 1, 2026 – Nov 2, 2026', svg)
                self.assertNotIn('<script', svg)


class PublicCalendarTests(unittest.TestCase):
    HTML = '''
        <td id="d1" data-date="2026-01-01" data-level="1"></td>
        <td id="d2" data-date="2026-01-02" data-level="0"></td>
        <tool-tip for="d1">4 contributions on January 1.</tool-tip>
        <tool-tip for="d2">No contributions on January 2.</tool-tip>
    '''

    def test_public_tooltip_counts_and_levels_are_preserved(self):
        parsed = parse_calendar(self.HTML, date(2026, 1, 2))
        self.assertEqual(parsed['totalContributions'], 4)
        days = [day for week in parsed['weeks'] for day in week['contributionDays']]
        self.assertEqual([day['contributionCount'] for day in days], [4, 0])

    def test_missing_public_dates_and_unrecognized_tooltips_fail(self):
        for html in (self.HTML.replace('data-date="2026-01-02"', 'data-date="2026-01-03"'),
                     self.HTML.replace('4 contributions on', 'Unknown activity for')):
            with self.subTest(html=html), self.assertRaises(ValueError):
                parse_calendar(html, date(2026, 1, 2))

    def test_decorative_animation_does_not_change_calendar_counts(self):
        svg, warnings = render_calendar(calendar(history('2026-01-01', [4, 0])),
                                        'yashwant938', 2026, date(2026, 1, 2))
        self.assertEqual(warnings, [])
        counts = {item.attrib['data-date']: item.attrib['data-count']
                  for item in ET.fromstring(svg).iter() if 'data-count' in item.attrib}
        self.assertEqual(counts, {'2026-01-01': '4', '2026-01-02': '0'})

    def test_inconsistent_counts_and_levels_are_rejected(self):
        data = calendar(history('2026-01-01', [4]))
        data['weeks'][0]['contributionDays'][0]['contributionLevel'] = 'NONE'
        with self.assertRaises(CalendarError):
            render_calendar(data, 'yashwant938', 2026, date(2026, 1, 1))


class RefreshTests(unittest.TestCase):
    def test_fetches_history_but_limits_the_record_to_the_displayed_year(self):
        def fetched(username, end):
            if end.year == 2025:
                return calendar(history('2025-12-31', [1]))
            return calendar(history('2026-01-01', [4, 0]))

        with patch('update_contributions.fetch_public', return_value='{"created_at":"2025-12-31T00:00:00Z"}'), \
                patch('update_contributions.fetch_calendar', side_effect=fetched) as request:
            latest, summary = fetch_history('yashwant938', date(2026, 1, 2))
        self.assertEqual(request.call_count, 2)
        self.assertEqual(latest['totalContributions'], 4)
        self.assertEqual(summary.current.length, 2)
        self.assertEqual(summary.longest_year, 2026)
        self.assertEqual(summary.longest.length, 1)
        self.assertEqual(summary.longest.start, date(2026, 1, 1))

    def test_failed_history_request_preserves_all_existing_images(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in
                     ('contributions-red.svg', 'contribution-streaks.svg', 'contribution-streaks-mobile.svg')]
            for path in paths:
                path.write_text('previous good image', encoding='utf-8')
            with patch('update_contributions.fetch_history', side_effect=OSError('history unavailable')), \
                    self.assertRaises(OSError):
                main(['--as-of', '2026-11-04', '--output', str(paths[0])])
            self.assertEqual([path.read_text(encoding='utf-8') for path in paths], ['previous good image'] * 3)

    def test_refresh_writes_calendar_and_both_streak_cards(self):
        counts = history('2026-01-01', [4, 1])
        summary = calculate_streaks(counts, date(2026, 1, 2), longest_year=2026)
        with tempfile.TemporaryDirectory() as directory, \
                patch('update_contributions.fetch_history', return_value=(calendar(counts), summary)):
            output = Path(directory) / 'contributions-red.svg'
            main(['--as-of', '2026-01-02', '--output', str(output)])
            for name in ('contributions-red.svg', 'contribution-streaks.svg', 'contribution-streaks-mobile.svg'):
                root = ET.fromstring((Path(directory) / name).read_text(encoding='utf-8'))
                if name != 'contributions-red.svg':
                    self.assertEqual(root.attrib['data-longest-year'], '2026')


if __name__ == '__main__':
    unittest.main()
