# Contribution calendar and streaks

The profile uses GitHub's public contribution calendar for both the animated
calendar and the two streak cards above it. No third-party badge service or
private contribution data is used.

- An active day has at least one public contribution reported by GitHub.
  Multiple commits, pushes, or other contributions on one day count as one day.
- The current streak ends today if today is active. Before today's first
  contribution, yesterday's streak remains available for the unfinished day.
  A missed completed day breaks it: if yesterday was empty and today is active,
  the current streak is **1 day**.
- The **longest streak in the displayed year** uses the same calendar year as
  the chart. The year appears directly in the card heading. Older records do not
  affect this number. If several runs tie, the most recent dates appear.
- The current streak still uses the full account history and can cross December
  31. The yearly longest streak is clipped to the displayed year's dates.
- Dates and the snapshot cutoff use the public calendar's date labels and UTC.
  The card shows its update date. GitHub determines which activity qualifies.
- Missing dates or failed historical requests stop the refresh and preserve the
  previously published assets rather than inventing zero-contribution days.

The GitHub Actions workflow refreshes every four hours (at minute 17, UTC), can
be run manually, and also runs after changes to the generator or its tests.
GitHub may delay scheduled workflow runs.

Only Python's standard library is required:

```sh
python -m unittest discover -s tests -v
python scripts/update_contributions.py
```

For a dated snapshot in another output directory:

```sh
python scripts/update_contributions.py --as-of 2026-11-04 --output preview/contributions-red.svg
```

The updater writes the calendar, `contribution-streaks.svg`, and
`contribution-streaks-mobile.svg` to that directory only after the complete
history is fetched and validated. The calendar's recorded contribution counts
are independent of the decorative snake animation.
