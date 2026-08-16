# School-year report selection design

## Goal

Show the active school year in the top-right corner of the page and let the user
select any school year represented by stored study or sleep data. The Reports tab
must calculate every value from the selected school year only. Calendar browsing
remains month-based and independent of the report range.

## School-year definition

A school year is identified by its starting calendar year and displayed as
`YYYY-YYYY+1`, for example `2026-2027`.

The `2026-2027` report range starts on the Monday of ISO week 30 in 2026 and runs
through the Sunday of ISO week 31 in 2027, matching the requested inclusive week
range. Queries express this as a half-open interval (`start <= date < end`), where
`end` is the Monday of ISO week 32 in the ending year.

Adjacent report ranges overlap during ISO weeks 30 and 31. A date in that overlap
is assigned to the newer school year when determining the current label, but is
included in both selectable report ranges. School-year discovery likewise offers
both ranges when an overlap date is the only stored data, so every range containing
data remains selectable.

The current school year is derived from today's date. Before the week-30 boundary,
the current school year started in the previous calendar year; on or after that
boundary, it starts in the current calendar year.

## Backend design

Add small, pure helpers in `app.py` for:

- calculating the start date and half-open bounds for a school year;
- mapping a date to its school-year start year;
- formatting and strictly parsing the `YYYY-YYYY+1` label;
- finding available school years from distinct dates in both data tables.

`GET /` accepts an optional `school_year=YYYY-YYYY+1` query parameter. A missing
or malformed value falls back to the current school year. The current year is
always offered in the selector, even when it has no data; additional choices are
derived from any study or sleep row in the database.

The selected bounds are applied to both report data sources:

- subject totals query only `STUDY_HOURS` rows inside the selected range;
- weekly totals cover only weeks inside the selected range. Past years render
  through their last complete week, while the current year stops at the current
  week so no future weeks are displayed.

The monthly study and sleep queries are intentionally unchanged. Month navigation
and the selector links preserve both `month` and `school_year` so changing the
calendar month does not silently reset the report selection.

Keep SQL parameterized and retain separate PostgreSQL (`%s`, native dates) and
SQLite (`?`, ISO strings) parameter handling.

## UI design

Turn the page heading row into a flex layout. The existing title stays on the
left; a Bootstrap dropdown on the right shows `School year: YYYY-YYYY+1`. Its menu
contains the available years in newest-first order, visually marking the selected
one. Selecting an entry performs a normal `GET /` with the current calendar month
and chosen school year.

No new JavaScript is required because Bootstrap's existing dropdown behavior and
ordinary links provide the interaction.

## Test plan

Extend `tests/test_app.py` with coverage for:

1. Boundary mapping: a date immediately before ISO week 30 belongs to the prior
   school year, the boundary date belongs to the new one, and report bounds include
   the following year's week 31.
2. Default UI: the response shows the current school-year label and selector.
3. Discovery: data in either table causes the corresponding year to appear in the
   dropdown.
4. Filtering: selecting one of two populated school years includes only that
   year's subject totals and weekly minutes in Reports.
5. Navigation: previous/next-month links retain the selected school year.
6. Invalid input: a malformed school-year parameter safely falls back to the
   current year.

Run the complete `pytest` suite after implementation and use `git diff --check`
to verify the patch.
