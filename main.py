#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from datetime import date, datetime, timedelta
import json

parser = ArgumentParser()
parser.add_argument("-f", "--file", dest="filename",
                    help="json file to parse", metavar="FILE")
parser.add_argument("-d", "--date", dest="date",
                    help="date")
parser.add_argument("-y", "--yesterday", dest="yesterday",
                    help="yesterday")
parser.add_argument("-n", "--consecutive", dest="consecutive",
                    help="consecutive")
parser.add_argument("-c", "--cutoff", dest="cutoff",
                    help="cutoff", default=60, type=int)

def main():
    filename = args.filename
    if not filename:
        if args.date:
            _date = datetime.strptime(args.date, '%Y-%m-%d')
        else:
            _date = date.today() - timedelta(days=int(args.yesterday or 0))
        filename = '../thyme/{}.json'.format(_date.strftime('%Y-%m-%d'))

    print("opening file {}".format(filename))
    with open(filename) as f:
        data = json.load(f)
        snapshots = data.get('Snapshots')

        sessions = SessionGenerator(snapshots)
        sessions.generate()
    
    
    while True:
        sessions.print_sessions()
        uinput = raw_input("select command (w, p, q): ")
        if uinput not in ['w', 'p', 'q']:
            continue
        command = uinput
        if command == 'q':
            break
        uinput = raw_input("Select session (1-{}): ".format(len(sessions.sessions)))
        try:
            selection = int(uinput)
            if command == 'w':
                sessions.sessions[selection].print_windows()
            elif command == 'p':
                push_session(sessions.sessions[selection])
        except:
            pass

def push_session(session):
    uinput = raw_input("Name: ")
    if uinput == 'q' or len(uinput) == 0:
        return
    print('Pushed session to toggl')
    pass

def get_window_name(snapshot):
    if snapshot is None:
        return None
    for window in snapshot['Windows']:
        if window['ID'] == snapshot['Active']:
            return window['Name']


class Session():
    def print_out(self):
        duration = (self.end_time - self.start_time)

        print u"{} - {}, time: {}".format(
            self.start_time, self.end_time, duration)

    def print_windows(self):
        for window in self.windows:
            print u"{}s - {}".format(self.windows[window], window)

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
        if window_name not in self.windows:
            self.windows[window_name] = 0
        self.windows[window_name] += diff.seconds


class SessionGenerator():
    def __init__(self, snapshots):
        self.sessions = []
        self.snapshots = snapshots
    
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
        for snapshot in self.snapshots:
            prev_time = new_time
            new_time = datetime.strptime(snapshot['Time'][:19], '%Y-%m-%dT%H:%M:%S')
            if not prev_time:  # first loop
                continue
            diff = new_time - prev_time
            if diff.seconds < args.cutoff:
                self.start_or_continue_session(prev_time, diff=diff, window=get_window_name(prev_snapshot))
            else:
                self.end_session(prev_time)
            prev_snapshot = snapshot
        self.end_session(new_time)

if __name__ == '__main__':
    args = parser.parse_args()
    main()