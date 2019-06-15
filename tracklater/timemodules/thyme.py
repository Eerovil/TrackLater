import json
import os
from datetime import timedelta
from typing import List, Any, Optional

from tracklater import settings
from tracklater.utils import parse_time
from .interfaces import EntryMixin, AbstractParser, AbstractProvider
from tracklater.models import Entry

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global') -> Any:
    return settings.helper('THYME', key, group=group, default=default)


DEFAULTS = {
    'IDLE': 900,
    'CUTOFF': 300,
}


def get_window(entry, id) -> Optional[dict]:
    for w in entry['Windows']:
        if w['ID'] == id:
            return w
    return None


class Parser(EntryMixin, AbstractParser):
    """
    Only implements "get".
    """

    def get_entries(self) -> List[Entry]:
        snapshot_entries: List[Entry] = self._read_files()
        return self._generate_sessions(snapshot_entries)

    def _read_files(self):
        provider = Provider()
        _ret: List[dict] = []
        for snapshot in provider.read_files(self.start_date, self.end_date):
            entry = self._parse_snapshot_entry(snapshot)
            if entry:
                _ret.append(entry)
        return _ret

    def _parse_snapshot_entry(self, entry):
        active_window = get_window(entry, entry['Active'])
        if active_window is None:
            return None
        return {
            'active_window': active_window,
            'time': parse_time(entry['Time']),
            'category': 'work',
        }

    def _generate_sessions(self, entries):
        def _init_session(entry):
            return Entry(
                start_time=entry['time'],
                extra_data={
                    'windows': {},
                    'category': {'work': 0, 'leisure': 0}
                }
            )

        def _end_session(session, entry):
            session.end_time = entry['time']
            extra = session.extra_data
            extra['windows'] = [
                {'name': window, 'time': extra['windows'][window]}
                for window in extra['windows']
            ]
            session.text = "\n".join([
                "{}s - {}".format(int(data['time']), data['name'])
                for data in sorted(extra['windows'], key=lambda x: x["time"], reverse=True)
            ])
            if extra['category']['work'] >= extra['category']['leisure']:
                extra['category'] = 'work'
            else:
                extra['category'] = 'leisure'

        def _add_window(session, window, seconds):
            if 'eero@eero-ThinkPad-L470' in window['Name']:
                return session

            if window['Name'] not in session.extra_data['windows']:
                session.extra_data['windows'][window['Name']] = 0
            session.extra_data['windows'][window['Name']] += seconds

            return session

        def _update_category(session, category, seconds):
            if category == 'work':
                session.extra_data['category']['work'] += seconds * 2
            elif category == 'leisure':
                session.extra_data['category']['leisure'] += seconds * 2

        prev_entry = entries[0]
        sessions = [_init_session(prev_entry)]

        for entry in entries[1:]:
            if prev_entry['active_window'] == entry['active_window']:
                continue

            diff = (entry['time'] - prev_entry['time']).total_seconds()
            session_length = (prev_entry['time'] - sessions[-1].start_time).total_seconds()

            _add_window(sessions[-1], prev_entry['active_window'], diff)
            _update_category(sessions[-1], prev_entry['category'], diff)

            _idle = get_setting('IDLE', DEFAULTS['IDLE'])
            _cutoff = get_setting('CUTOFF', DEFAULTS['CUTOFF'])

            if (diff >= _idle or session_length >= _cutoff):
                _end_session(sessions[-1], prev_entry)
                sessions.append(_init_session(entry))

            prev_entry = entry

        _end_session(sessions[-1], prev_entry)

        return sessions


class Provider(AbstractProvider):
    def read_files(self, start_date, end_date) -> List[dict]:
        snapshot_entries = []
        filenames = []
        date = start_date
        while date <= end_date:
            filenames.append('{}/{}.json'.format(get_setting('DIR'), date.strftime('%Y-%m-%d')))
            date = date + timedelta(days=1)

        for filename in filenames:
            logging.info("opening file {}".format(filename))
            if not os.path.exists(filename):
                continue
            with open(filename) as f:
                data = json.load(f)
                entries = data.get('Snapshots')
                for entry in entries:
                    snapshot_entries.append(entry)
        return snapshot_entries

    def test_read_files(self, start_date=None, end_date=None):
        return [
            {
                "Time": "2019-05-23T12:00:01.242072673+03:00",
                "Windows": [
                    {
                        "ID": 1,
                        "Desktop": -1,
                        "Name": "Chrome - github"
                    },
                    {
                        "ID": 2,
                        "Desktop": 0,
                        "Name": "VSCode"
                    }
                ],
                "Active": 1,
                "Visible": [
                    1,
                    2,
                ]
            },
            {
                "Time": "2019-05-23T12:04:01.242072673+03:00",
                "Windows": [
                    {
                        "ID": 1,
                        "Desktop": -1,
                        "Name": "Chrome - github"
                    },
                    {
                        "ID": 2,
                        "Desktop": 0,
                        "Name": "VSCode"
                    }
                ],
                "Active": 2,
                "Visible": [
                    1,
                    2,
                ]
            },
            {
                "Time": "2019-05-23T12:08:01.242072673+03:00",
                "Windows": [
                    {
                        "ID": 1,
                        "Desktop": -1,
                        "Name": "Chrome - github"
                    },
                    {
                        "ID": 2,
                        "Desktop": 0,
                        "Name": "VSCode"
                    }
                ],
                "Active": 1,
                "Visible": [
                    1,
                    2,
                ]
            },
        ]
