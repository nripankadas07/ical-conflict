from datetime import datetime, timezone
import unittest
from ical_conflict import parse, conflicts, local_time


def calendar(events):
    return 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\n' + ''.join('BEGIN:VEVENT\r\n'+e+'\r\nEND:VEVENT\r\n' for e in events) + 'END:VCALENDAR\r\n'


def event(uid, start='20261006T100000Z', end='20261006T110000Z'):
    return f'UID:{uid}\r\nDTSTART:{start}\r\nDTEND:{end}'


class CalendarTests(unittest.TestCase):
    def test_overlap_and_adjacent_exclusive_end(self):
        events, _ = parse(calendar([event('a'), event('b','20261006T103000Z','20261006T113000Z'), event('c','20261006T113000Z','20261006T120000Z')]), 'one')
        pairs = conflicts(events)['conflicts']
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]['overlap_seconds'], 1800)

    def test_iana_zone_equal_to_utc_and_folded_uid(self):
        text = calendar([event('abc\r\n def').replace('DTSTART:20261006T100000Z', 'DTSTART;TZID=Asia/Dubai:20261006T140000').replace('DTEND:20261006T110000Z', 'DTEND;TZID=Asia/Dubai:20261006T150000')])
        events, _ = parse(text, 'one')
        self.assertEqual(events[0]['uid'], 'abcdef')
        self.assertEqual(events[0]['start'], datetime(2026,10,6,10,tzinfo=timezone.utc))

    def test_dst_ambiguity_and_gap_rejected(self):
        for value in ['20261101T013000', '20260308T023000']:
            with self.assertRaisesRegex(ValueError, 'ambiguous or nonexistent'):
                local_time(value, 'America/New_York')

    def test_all_day_requires_explicit_zone(self):
        text = calendar(['UID:a\r\nDTSTART;VALUE=DATE:20261006\r\nDTEND;VALUE=DATE:20261007'])
        with self.assertRaises(ValueError):
            parse(text, 'one')
        events, _ = parse(text, 'one', 'Asia/Dubai')
        self.assertEqual(events[0]['start'].isoformat(), '2026-10-05T20:00:00+00:00')

    def test_cancelled_transparent_skipped(self):
        events, skipped = parse(calendar([event('a')+'\r\nSTATUS:CANCELLED',event('b')+'\r\nTRANSP:TRANSPARENT']), 'one')
        self.assertEqual(events, [])
        self.assertEqual(skipped, 2)

    def test_recurring_floating_custom_zone_rejected(self):
        for text in [calendar([event('a')+'\r\nRRULE:FREQ=DAILY']), calendar([event('a','20261006T100000','20261006T110000')]), 'BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VTIMEZONE\nEND:VTIMEZONE\nEND:VCALENDAR']:
            with self.assertRaises(ValueError):
                parse(text, 'one')

    def test_duplicate_export_dedup_and_conflicting_uid(self):
        a, _ = parse(calendar([event('a')]), 'one')
        b, _ = parse(calendar([event('a')]), 'two')
        self.assertEqual(conflicts(a+b)['duplicate_exports'], 1)
        self.assertEqual(conflicts(a+b)['conflicts'], [])
        c, _ = parse(calendar([event('a','20261006T120000Z','20261006T130000Z')]), 'three')
        with self.assertRaises(ValueError):
            conflicts(a+c)

    def test_bad_boundaries_duplicate_uid_and_negative_interval(self):
        for text in [calendar([event('a'),event('a')]), calendar([event('a','20261006T110000Z','20261006T100000Z')]), calendar([event('a')]).replace('END:VEVENT','END:VTODO')]:
            with self.assertRaises(ValueError):
                parse(text, 'one')


if __name__ == '__main__':
    unittest.main()
