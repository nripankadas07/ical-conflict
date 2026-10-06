"""Find overlaps in bounded, non-recurring iCalendar exports without a server."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import heapq
import json
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

UTC = timezone.utc
MAX_BYTES = 10_000_000
MAX_EVENTS = 5000
MAX_CONFLICTS = 10000


def local_time(value: str, zone: str):
    naive = datetime.strptime(value, '%Y%m%dT%H%M%S')
    tz = ZoneInfo(zone)
    candidates = {naive.replace(tzinfo=tz, fold=fold).astimezone(UTC)
                  for fold in [0, 1]
                  if naive.replace(tzinfo=tz, fold=fold).astimezone(UTC).astimezone(tz).replace(tzinfo=None) == naive}
    if len(candidates) != 1:
        raise ValueError('ambiguous or nonexistent local time; export UTC instead')
    return candidates.pop()


def timestamp(params: dict, value: str, date_zone: str | None):
    if set(params) - {'TZID', 'VALUE'}:
        raise ValueError('unsupported date parameters')
    kind = params.get('VALUE', 'DATE-TIME')
    if kind == 'DATE':
        if 'TZID' in params or not date_zone or not re.fullmatch(r'\d{8}', value):
            raise ValueError('all-day DATE requires --date-zone and no TZID')
        return local_time(value + 'T000000', date_zone), kind
    if kind != 'DATE-TIME' or not re.fullmatch(r'\d{8}T\d{6}Z?', value):
        raise ValueError('unsupported date/time representation')
    if value.endswith('Z'):
        if 'TZID' in params:
            raise ValueError('UTC date/time cannot also have TZID')
        return datetime.strptime(value, '%Y%m%dT%H%M%SZ').replace(tzinfo=UTC), kind
    if 'TZID' not in params:
        raise ValueError('floating time unsupported; export UTC or IANA TZID')
    return local_time(value, params['TZID']), kind


def parse(text: str, source: str, date_zone=None):
    physical = text.replace('\r\n', '\n').splitlines()
    lines = []
    for line in physical:
        if line.startswith((' ', '\t')):
            if not lines:
                raise ValueError('orphan folded line')
            lines[-1] += line[1:]
        elif line:
            lines.append(line)
    stack, current, events, version = [], None, [], None
    calendars = 0
    for line in lines:
        if ':' not in line:
            raise ValueError('content line lacks colon')
        left, value = line.split(':', 1)
        tokens = left.split(';')
        name = tokens[0].upper()
        params = {}
        for token in tokens[1:]:
            if '=' not in token:
                raise ValueError('invalid property parameter')
            key, val = token.split('=', 1)
            key = key.upper()
            if key in params or not val:
                raise ValueError('duplicate or empty property parameter')
            params[key] = val.strip('"')
        if name == 'BEGIN':
            value = value.upper()
            if value == 'VCALENDAR' and not stack and calendars == 0:
                calendars += 1
            elif value == 'VEVENT' and stack == ['VCALENDAR']:
                current = {}
            elif value == 'VALARM' and stack == ['VCALENDAR', 'VEVENT']:
                pass
            else:
                raise ValueError('unsupported component; VTIMEZONE/custom definitions are not interpreted')
            stack.append(value)
        elif name == 'END':
            if not stack or stack[-1] != value.upper():
                raise ValueError('mismatched component boundary')
            ended = stack.pop()
            if ended == 'VEVENT':
                events.append(current)
                current = None
                if len(events) > MAX_EVENTS:
                    raise ValueError('event count exceeds 5000')
        elif not stack:
            raise ValueError('property outside calendar')
        elif stack == ['VCALENDAR'] and name == 'VERSION':
            if version is not None:
                raise ValueError('duplicate VERSION')
            version = value
        elif stack == ['VCALENDAR', 'VEVENT']:
            if name in {'RRULE', 'RDATE', 'EXDATE', 'EXRULE', 'RECURRENCE-ID', 'DURATION'}:
                raise ValueError('recurrence and DURATION unsupported; provide explicit non-recurring DTSTART/DTEND')
            if name in {'UID', 'DTSTART', 'DTEND', 'STATUS', 'TRANSP'}:
                if name in current:
                    raise ValueError('duplicate event property')
                current[name] = (params, value)
    if stack or calendars != 1 or version != '2.0':
        raise ValueError('expected one complete VERSION:2.0 VCALENDAR')
    result, skipped, seen = [], 0, set()
    for event in events:
        if 'UID' not in event or not event['UID'][1] or event['UID'][0]:
            raise ValueError('event requires plain unique UID')
        uid = event['UID'][1]
        if uid in seen:
            raise ValueError('duplicate UID in one export')
        seen.add(uid)
        status = event.get('STATUS', ({}, 'CONFIRMED'))[1].upper()
        transparency = event.get('TRANSP', ({}, 'OPAQUE'))[1].upper()
        if status not in {'CONFIRMED', 'TENTATIVE', 'CANCELLED'} or transparency not in {'OPAQUE', 'TRANSPARENT'}:
            raise ValueError('unsupported status/transparency')
        if status == 'CANCELLED' or transparency == 'TRANSPARENT':
            skipped += 1
            continue
        if 'DTSTART' not in event or 'DTEND' not in event:
            raise ValueError('busy event requires explicit DTSTART and DTEND')
        start, start_kind = timestamp(*event['DTSTART'], date_zone)
        end, end_kind = timestamp(*event['DTEND'], date_zone)
        if start_kind != end_kind or end <= start:
            raise ValueError('end must follow start with matching DATE/DATE-TIME kind')
        result.append({'uid': uid, 'source': source, 'start': start, 'end': end})
    return result, skipped


def conflicts(events):
    unique, duplicates = {}, 0
    for event in events:
        uid = event['uid']
        if uid in unique:
            old = unique[uid]
            if (old['start'], old['end']) != (event['start'], event['end']):
                raise ValueError('same UID has conflicting intervals across exports')
            duplicates += 1
        else:
            unique[uid] = event
    if len(unique) > MAX_EVENTS:
        raise ValueError('combined event count exceeds 5000')
    ordered = sorted(unique.values(), key=lambda e: (e['start'], e['end'], e['uid']))
    active, heap, pairs = {}, [], []
    for index, event in enumerate(ordered):
        while heap and heap[0][0] <= event['start']:
            _, expired = heapq.heappop(heap)
            active.pop(expired)
        for other in active.values():
            overlap_end = min(other['end'], event['end'])
            pairs.append({'a': {'uid': other['uid'], 'source': other['source']},
                          'b': {'uid': event['uid'], 'source': event['source']},
                          'start_utc': event['start'].isoformat(), 'end_utc': overlap_end.isoformat(),
                          'overlap_seconds': (overlap_end-event['start']).total_seconds()})
            if len(pairs) > MAX_CONFLICTS:
                raise ValueError('more than 10000 conflict pairs; narrow the input')
        active[index] = event
        heapq.heappush(heap, (event['end'], index))
    return {'schema': 1, 'events': len(ordered), 'duplicate_exports': duplicates, 'conflicts': pairs}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('calendars', nargs='+', type=Path)
    parser.add_argument('--date-zone', help='explicit IANA zone for all-day DATE values')
    args = parser.parse_args(argv)
    try:
        if len(args.calendars) > 50:
            raise ValueError('at most 50 calendar files')
        events, skipped = [], 0
        for index, path in enumerate(args.calendars):
            with path.open('rb') as handle:
                data = handle.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError('calendar exceeds 10 MB')
            loaded, count = parse(data.decode('utf-8-sig'), f'input-{index+1}', args.date_zone)
            events.extend(loaded)
            skipped += count
        report = conflicts(events)
        report['skipped_free_or_cancelled'] = skipped
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return int(bool(report['conflicts']))
    except (OSError, ValueError, KeyError) as exc:
        print(f'ical-conflict: invalid or unsupported input: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
