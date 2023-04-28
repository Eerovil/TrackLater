import json
import os
from datetime import timedelta
from typing import List, Any, Optional
import requests

from tracklater import settings
from tracklater.utils import parse_time
from .interfaces import EntryMixin, AbstractParser, AbstractProvider
from tracklater.models import Entry

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global') -> Any:
    return settings.helper('ACTIVITYWATCH', key, group=group, default=default)


DEFAULTS = {
    'IDLE': 900,
    'CUTOFF': 300,
}


def get_window(entry) -> Optional[str]:
    if entry.get('data') and entry['data'].get('app'):
        parts = [entry['data']['app']]
        if entry['data'].get('title'):
            parts.append(entry['data']['title'])
        if entry['data'].get('url'):
            parts.append(entry['data']['url'])
        return ' - '.join(parts)
    return None


class Parser(EntryMixin, AbstractParser):
    """
    Only implements "get".
    """

    def get_entries(self) -> List[Entry]:
        raw_events: List[dict] = self._fetch_events()
        return self._generate_sessions(raw_events)

    def _fetch_events(self) -> List[dict]:
        provider = Provider()
        _ret: List[dict] = []
        for raw_event in provider.fetch_events(self.start_date, self.end_date):
            entry = self._parse_raw_event(raw_event)
            if entry:
                _ret.append(entry)
        return _ret

    def _parse_raw_event(self, entry):
        try:
            active_window = get_window(entry)[:100]
        except Exception as e:
            logger.exception(e)
            active_window = None
        if active_window is None:
            return None
        if (entry['duration'] or 0) > 1000:
            return None
        time = parse_time(entry['timestamp'])
        end_time = time + timedelta(seconds=(entry['duration'] or 0))
        return {
            'active_window': active_window,
            'time': time,
            'end_time': end_time,
            'category': 'work',
        }

    def _generate_sessions(self, entries):
        def _init_session(entry):
            return Entry(
                start_time=entry['time'],
                end_time=entry['end_time'],
                extra_data={
                    'windows': {},
                    'group': {},
                }
            )

        def _end_session(session, entry):
            session.start_time = entry['time']
            extra = session.extra_data
            extra['windows'] = [
                {'name': window, 'time': extra['windows'][window]}
                for window in extra['windows']
            ]
            session.text = "\n".join([
                "{}s - {}".format(int(data['time']), data['name'])
                for data in sorted(extra['windows'], key=lambda x: x["time"], reverse=True)
            ])

            sorted_groups = sorted(extra['group'].items(), key=lambda val: val[1], reverse=True)

            session.extra_data['groups'] = sorted_groups
            if sorted_groups:
                session.group = sorted_groups[0][0]
                session.text = session.group + "\n" + session.text

        def _add_window(session, window_name, seconds):
            if window_name not in session.extra_data['windows']:
                session.extra_data['windows'][window_name] = 0
            session.extra_data['windows'][window_name] += seconds

            for key in settings.ACTIVITYWATCH:
                for keyword in settings.ACTIVITYWATCH[key].get('KEYWORDS', []):
                    if keyword in window_name:
                        if key not in session.extra_data['group']:
                            session.extra_data['group'][key] = 0
                        session.extra_data['group'][key] += seconds

            return session

        if not entries:
            return []
        next_entry = entries[0]
        # Were going backwards in time while looping these!!!
        sessions = [_init_session(next_entry)]

        for entry in entries[1:]:
            if next_entry['active_window'] == entry['active_window']:
                continue

            # Time spent in window
            diff = abs((entry['end_time'] - next_entry['end_time']).total_seconds())
            session_length = abs((next_entry['end_time'] - sessions[-1].start_time).total_seconds())

            # Add window name and time spent to extra data
            _add_window(sessions[-1], next_entry['active_window'], diff)

            _idle = get_setting('IDLE', DEFAULTS['IDLE'])
            _cutoff = get_setting('CUTOFF', DEFAULTS['CUTOFF'])

            if (diff >= _idle or session_length >= _cutoff):
                _end_session(sessions[-1], next_entry)
                sessions.append(_init_session(entry))

            next_entry = entry

        _end_session(sessions[-1], next_entry)

        logger.warning("sessions: %s", sessions)

        return sessions


class Provider(AbstractProvider):
    def fetch_events(self, start_date, end_date) -> List[dict]:
        parsed_events = []

        url = get_setting('EVENTS_URL')
        resp = requests.get(url, headers={'HOST': '127.0.0.1'})
        for event in resp.json():
            parsed_events.append(event)
        return parsed_events

    def test_fetch_events(self, start_date=None, end_date=None):
        return [
            {
                "id": 46,
                "timestamp": "2022-09-04T04:41:31.063000+00:00",
                "duration": 10.464,
                "data": {
                    "app": "Google Chrome",
                    "url": "http://localhost:5600/api/0/buckets/",
                    "title": "",
                    "incognito": False
                }
            },
            {
                "id": 45,
                "timestamp": "2022-09-04T04:41:29.999000+00:00",
                "duration": 0.0,
                "data": {
                    "app": "Google Chrome",
                    "url": "chrome://downloads/",
                    "title": "Downloads",
                    "incognito": False
                }
            }
        ]
