from thymetogglutil import settings
import json
import os
from datetime import timedelta
from thymetogglutil.utils import parse_time
from thymetogglutil.timemodules.interfaces import AbstractEntryParser, Entry
from typing import List

import logging
logger = logging.getLogger(__name__)


def get_window(entry, id):
    for w in entry['Windows']:
        if w['ID'] == id:
            return w
    return None


class Parser(AbstractEntryParser):
    """
    Only implements "get".
    """

    def get_entries(self) -> List[Entry]:
        snapshot_entries = self._read_files()
        self.sessions = self._generate_sessions(snapshot_entries)
        return self.sessions

    def _read_files(self):
        snapshot_entries = []
        filenames = []
        date = self.start_date
        while date <= self.end_date:
            filenames.append('{}/{}.json'.format(settings.THYME_DIR, date.strftime('%Y-%m-%d')))
            date = date + timedelta(days=1)

        for filename in filenames:
            logging.info("opening file {}".format(filename))
            if not os.path.exists(filename):
                continue
            with open(filename) as f:
                data = json.load(f)
                entries = data.get('Snapshots')
                for entry in entries:
                    parsed_entry = self._parse_snapshot_entry(entry)
                    if parsed_entry is not None:
                        snapshot_entries.append(parsed_entry)

        return snapshot_entries

    def _parse_snapshot_entry(self, entry):
        active_window = get_window(entry, entry['Active'])
        if active_window is None:
            return None
        return {
            'active_window': active_window,
            'time': parse_time(entry['Time']),
            'category': self._guess_category(active_window),
        }

    def _guess_category(self, window):
        for l in settings.LEISURE:
            if l in window['Name']:
                return 'leisure'
        for l in settings.WORK:
            if l in window['Name']:
                return 'work'
        return 'unknown'

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
            session.text = [
                "{} - {}".format(data['name'], data['name'])
                for data in sorted(extra['windows'], key=lambda x: x["time"], reverse=True)
            ]
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

            if diff >= settings.IDLE or session_length >= settings.CUTOFF:
                _end_session(sessions[-1], prev_entry)
                sessions.append(_init_session(entry))

            prev_entry = entry

        _end_session(sessions[-1], prev_entry)

        return sessions
