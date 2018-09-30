from thymetogglutil import settings
import json
from datetime import timedelta
from thymetogglutil.utils import parse_time

import logging
logger = logging.getLogger(__name__)


def get_window(entry, id):
    for w in entry['Windows']:
        if w['ID'] == id:
            return w
    return None


class ThymeMixin(object):
    def parse_thyme(self):
        snapshot_entries = self.read_files()
        self.sessions = self.generate_sessions(snapshot_entries)

    def read_files(self):
        snapshot_entries = []
        filenames = []
        date = self.start_date
        while date <= self.end_date:
            filenames.append('{}/{}.json'.format(settings.THYME_DIR, date.strftime('%Y-%m-%d')))
            date = date + timedelta(days=1)

        for filename in filenames:
            logging.info("opening file {}".format(filename))
            with open(filename) as f:
                data = json.load(f)
                entries = data.get('Snapshots')
                for entry in entries:
                    parsed_entry = self.parse_snapshot_entry(entry)
                    if parsed_entry is not None:
                        snapshot_entries.append(parsed_entry)

        return snapshot_entries

    def parse_snapshot_entry(self, entry):
        active_window = get_window(entry, entry['Active'])
        if active_window is None:
            return None
        return {
            'active_window': active_window,
            'time': parse_time(entry['Time']),
            'category': self.guess_category(active_window),
        }

    def guess_category(self, window):
        for l in settings.LEISURE:
            if l in window['Name']:
                return 'leisure'
        for l in settings.WORK:
            if l in window['Name']:
                return 'work'
        return 'unknown'

    def generate_sessions(self, entries):
        def _init_session(entry):
            return {
                'start_time': entry['time'],
                'end_time': None,
                'windows': {},
                'duration': None,
                'category': {'work': 0, 'leisure': 0}
            }

        def _end_session(session, entry):
            session['end_time'] = entry['time']
            session['duration'] = (entry['time'] - session['start_time']).seconds
            session['windows'] = [{'name': window, 'time': session['windows'][window]}
                                  for window in session['windows']]
            if session['category']['work'] >= session['category']['leisure']:
                session['category'] = 'work'
            else:
                session['category'] = 'leisure'

        def _add_window(session, window, seconds):
            if 'eero@eero-ThinkPad-L470' in window['Name']:
                return session

            if window['Name'] not in session['windows']:
                session['windows'][window['Name']] = 0
            session['windows'][window['Name']] += seconds

            return session

        def _update_category(session, category, seconds):
            if category == 'work':
                session['category']['work'] += seconds * 2
            elif category == 'leisure':
                session['category']['leisure'] += seconds * 2

        prev_entry = entries[0]
        sessions = [_init_session(prev_entry)]
        for entry in entries[1:]:
            if prev_entry['active_window'] == entry['active_window']:
                continue

            diff = entry['time'] - prev_entry['time']

            _add_window(sessions[-1], prev_entry['active_window'], diff.seconds)
            _update_category(sessions[-1], prev_entry['category'], diff.seconds)

            if diff.seconds >= settings.CUTOFF:
                _end_session(sessions[-1], prev_entry)
                sessions.append(_init_session(entry))

            prev_entry = entry

        _end_session(sessions[-1], prev_entry)

        return sessions
