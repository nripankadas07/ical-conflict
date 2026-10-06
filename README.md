# ical-conflict

Finds busy-event overlaps across explicit non-recurring UTC, IANA-zone and explicitly zoned all-day intervals.

Built for people or scheduling administrators checking explicit appointment exports across calendars. Different calendar exports can hide overlaps through timezones or duplicated events. Unsupported recurrence must not silently yield a clear report.

## Quickstart

Python 3.11 or later. No runtime dependencies, service account or API key.
Clone the public source, create an isolated environment and install:

```sh
git clone https://github.com/nripankadas07/ical-conflict.git
cd ical-conflict
python -m venv .venv
. .venv/bin/activate
python -m pip install .
ical-conflict example.ics
```

Expected synthetic demo outcome: 2 busy events, zero conflicts; adjacent ends are exclusive. JSON goes to stdout.
Use `--help` for options. On Windows, activate with `.venv\Scripts\activate`.
Windows is not locally validated in this launch; remote CI covers Linux Python 3.11/3.12/3.13.

## Contract

Honor exclusive ends and overlapping intervals, convert IANA zones, reject DST ambiguity/gaps and recurrence, unfold lines, skip free/cancelled events and deduplicate repeated exports without hiding conflicting UIDs.

Exit 0 means the supported input has no gated finding; 1 means a finding or gate failure;
2 means malformed or unsupported input/coverage. Read the JSON counts and limitations
before interpreting a zero result as comprehensive validation.

## Limitations

Explicit non-recurring VEVENT DTSTART/DTEND only. Recurrence fields, DURATION, floating timestamps and VTIMEZONE definitions rejected, including in cancelled events. IANA TZID uses the installed system tzdb; ambiguous/nonexistent local times reject. All-day DATE requires --date-zone. Missing end rejects instead of assuming a duration. Transparent/cancelled events skipped; tentative busy events included. Duplicate identical UID intervals across exports collapse; conflicting UID intervals reject. Requires unique UIDs per input. Limits: 50 files, 10 MB/file, 5000 combined unique events and 10000 conflict pairs. VALARM ignored. No server writes, calendar sync or full RFC 5545 implementation. Output includes UIDs and UTC overlap intervals, not summaries or paths.

## Verify and contribute

```sh
python -m unittest -v
python -m compileall -q ical_conflict.py
python -m pip install build
python -m build
```

The tests exercise successful behavior and meaningful failure cases. See
[validation](VALIDATION.md), [research](RESEARCH.md), [contribution guidance](CONTRIBUTING.md)
and [security guidance](SECURITY.md). Open a reproducible issue with a synthetic fixture;
do not post private exports or credentials. MIT licensed; implementation is original,
with no competitor code or prose copied.
