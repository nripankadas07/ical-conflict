# Research and project brief

Observed: 2026-10-06T06:11:59.770604+00:00 UTC, exact query `icalendar`, sorted by stars descending.
[Search receipt](https://api.github.com/search/repositories?q=icalendar&sort=stars&order=desc&per_page=5). Only the first ten results were inspected;
this is not an exhaustive worldwide ranking. Kozea/Radicale is the highest-star
relevant comparable found in this query. Comparables can serve broader/different workflows.

| Repository | Observed stars | Repository pushed UTC | License metadata |
|---|---:|---|---|
| [Kozea/Radicale](https://github.com/Kozea/Radicale) | 5087 | 2026-10-06T06:02:00Z | GPL-3.0 |
| [jkbrzt/rrule](https://github.com/jkbrzt/rrule) | 3742 | 2024-06-27T17:52:15Z | NOASSERTION |
| [pimutils/khal](https://github.com/pimutils/khal) | 3067 | 2026-10-05T23:21:47Z | MIT |

Pushed timestamps are evidence of repository activity, not proof of response/support quality.
Commit observations for the original research are in [machine-readable evidence](research.json).
Latest PR activity can be dependency automation rather than substantive maintenance.

## User, need and smallest useful capability

People or scheduling administrators checking explicit appointment exports across calendars. Different calendar exports can hide overlaps through timezones or duplicated events. Unsupported recurrence must not silently yield a clear report. Finds busy-event overlaps across explicit non-recurring UTC, IANA-zone and explicitly zoned all-day intervals.

Read all three docs/issues and rrule src/datetime.ts. Recurrence-count and calendar free/busy PRs illustrate complexity; none verifies a request for our exact checker. Demand is inferred.

## Fair feature comparison

Radicale serves CalDAV/CardDAV; rrule expands recurrences; khal is a complete terminal calendar. Our narrower workflow is offline explicit-interval review. Users requiring recurrence should use a mature calendar stack; this MVP refuses it.

Our install path is a source clone plus Python pip install, with no runtime third-party
dependencies. Alternatives have their documented Go/Node/Python/Rust, hosted platform or
calendar-server workflows; their setup was reviewed in current documentation, not timed.
Our example and failure checks are runnable. Our supported input surface and support are
smaller; mature alternatives have broader documentation, integrations and maintenance history.
License metadata is reported, not legal compatibility advice; no code was reused.

No equivalent cross-tool workload was measured. No speed, reliability or global ranking
superiority is claimed. Synthetic fixtures prove only our documented behavior. Negative
results and unsupported configurations are in [validation](VALIDATION.md).

## Distinctness and discovery

Compared all five candidate briefs with 138 existing README/description briefs.
Existing trace/report/diff tools do not make these five one product: their users, accepted
input contracts and working algorithms differ. The archive-preflight idea was rejected
because it overlapped the existing wheel/path safety tools. iCalendar and scheduling topics with UTC/timezone/all-day fixtures and explicit unsupported examples.

Acceptance criteria: Honor exclusive ends and overlapping intervals, convert IANA zones, reject DST ambiguity/gaps and recurrence, unfold lines, skip free/cancelled events and deduplicate repeated exports without hiding conflicting UIDs.
