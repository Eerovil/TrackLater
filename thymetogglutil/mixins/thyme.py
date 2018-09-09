from thymetogglutil import settings
import json
from datetime import timedelta
from thymetogglutil.utils import parse_time

import logging
logger = logging.getLogger(__name__)


def get_window_name(snapshot):
    if snapshot is None:
        return None
    for window in snapshot['Windows']:
        if window['ID'] == snapshot['Active']:
            return window['Name']


class ThymeMixin(object):
    def parse_thyme(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = self.start_date
        if end_date is None:
            end_date = self.end_date

        generator = SessionGenerator()
        filenames = []
        date = start_date
        while date <= end_date:
            filenames.append('{}/{}.json'.format(settings.THYME_DIR, date.strftime('%Y-%m-%d')))
            date = date + timedelta(days=1)

        for filename in filenames:
            logging.info("opening file {}".format(filename))
            with open(filename) as f:
                data = json.load(f)
                snapshots = data.get('Snapshots')
                generator.add(snapshots)

        generator.generate()

        self.sessions = generator.to_list()


class Session(object):
    def print_out(self, out=True):
        duration = (self.end_time - self.start_time)
        print_str = u"{}, time: {}".format(
            self.start_time.strftime('%a %d.%m %H:%M'),
            str(duration)[:-10]
        )
        if out:
            print print_str
        return print_str

    def sorted_windows(self):
        return sorted(self.windows, key=lambda x: self.windows[x])

    def print_windows(self):
        for window in self.sorted_windows():
            print u"{}s - {}".format(self.windows[window], window)

    def guess_category(self):
        top_windows = self.sorted_windows()[-3:]
        medium_windows = self.sorted_windows()[-6:-3]
        score = dict(settings.SCORE)
        for window in top_windows:
            for l in settings.LEISURE:
                if l in window:
                    score['leisure'] += 2
                    break
            for l in settings.WORK:
                if l in window:
                    score['work'] += 2
                    break
        for window in medium_windows:
            for l in settings.LEISURE:
                if l in window:
                    score['leisure'] += 1
                    break
            for l in settings.WORK:
                if l in window:
                    score['work'] += 1
                    break
        return max(score.iterkeys(), key=(lambda key: score[key]))

    def __init__(self, time):
        self.start_time = time
        self.end_time = None
        self.windows = {}
        self.running = True

    def end(self, time):
        if self.end_time:
            return
        self.end_time = time
        self.running = False
    
    def add_window(self, diff, window_name):
        if 'eero@eero-ThinkPad-L470' in window_name:
            return
        if window_name not in self.windows:
            self.windows[window_name] = 0
        self.windows[window_name] += diff.seconds

    def to_dict(self):
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': (self.end_time - self.start_time).seconds,
            'windows': [{'name': window, 'time': self.windows[window]} for window in self.windows],
            'category': self.guess_category(),
        }


class SessionGenerator(object):
    def __init__(self):
        self.sessions = []
        self.snapshots = []

    def add(self, snapshots):
        self.snapshots += snapshots
    
    def print_sessions(self):
        for session in self.sessions:
            session.print_out()

    def start_or_continue_session(self, time, diff=None, window=None):
        if len(self.sessions) > 0 and self.sessions[-1].running:
            if window:
                self.sessions[-1].add_window(diff, window)
            return

        self.sessions.append(Session(time))

    def end_session(self, time):
        self.sessions[-1].end(time)

    def generate(self):
        new_time = None
        prev_snapshot = None
        last_active = 0
        if len(self.snapshots) == 0:
            return
        for snapshot in self.snapshots:
            def _get_window(id):
                for w in snapshot['Windows']:
                    if w['ID'] == id:
                        return w
            if _get_window(snapshot['Active']) == last_active:
                continue
            prev_time = new_time
            new_time = parse_time(snapshot['Time'])
            if not prev_time:  # first loop
                continue
            diff = new_time - prev_time
            if diff.seconds < settings.CUTOFF:
                self.start_or_continue_session(prev_time, diff=diff, window=get_window_name(prev_snapshot))
            else:
                self.end_session(prev_time)
            prev_snapshot = snapshot
            last_active = _get_window(snapshot['Active'])
        self.end_session(new_time)

    def to_list(self):
        return [session.to_dict() for session in self.sessions]
