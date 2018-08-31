#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from datetime import date, datetime, timedelta
from dateutil import parser as dateparser
import requests
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
parser.add_argument("-a", "--api_key", dest="api_key",
                    help="api_key")

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
    
    toggl = Toggl(args.api_key)
    
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
                toggl.push_session(sessions.sessions[selection - 1])
        except Exception as e:
            print(e)
            pass

class Toggl():
    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get('https://www.toggl.com/api/v8/me', auth=(self.api_key, 'api_token'))
        data = response.json()['data']
        self.email = data['email']
        self.default_wid = data['default_wid']
        self.id = data['id']
        self.time_entries = self.get_time_entries()

    def push_session(self, session):
        uinput = raw_input("Name: ")
        if uinput == 'q':
            return
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            'time_entry': {
                "description": uinput,
                "start": session.start_time.isoformat(),
                "duration":(session.end_time - session.start_time).seconds,
                "created_with":"thyme-toggl-cli"
            }
        }
        entry_id = self.check_session_exists(session)
        if entry_id:
            self.update_time_entry(entry_id, data)
            return
        response = requests.post(
            'https://www.toggl.com/api/v8/time_entries',
            data=json.dumps(data), headers=headers, auth=(self.api_key, 'api_token'))
        print(u'Pushed session to toggl: {}'.format(response.text))
        self.time_entries = self.get_time_entries()
        pass

    def update_time_entry(self, entry_id, data):
        response = requests.put('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id), data=json.dumps(data), auth=(self.api_key, 'api_token'))
        print(u'Updated session to toggl: {}'.format(response.text))
        self.time_entries = self.get_time_entries()
        return response.json()

    def get_time_entries(self, start_time=None):
        response = requests.get('https://www.toggl.com/api/v8/time_entries', auth=(self.api_key, 'api_token'))
        return response.json()
    
    def check_session_exists(self, session):
        for entry in self.time_entries:
            start = parse_time(entry['start'])
            stop = parse_time(entry['stop'])
            if start <= session.start_time <= stop:
                return entry['id']
            if start <= session.end_time <= stop:
                return entry['id']
        return None

def parse_time(timestr):
    return dateparser.parse(timestr)

def get_window_name(snapshot):
    if snapshot is None:
        return None
    for window in snapshot['Windows']:
        if window['ID'] == snapshot['Active']:
            return window['Name']


class Session():
    def print_out(self):
        duration = (self.end_time - self.start_time)
        print u"{}, time: {}".format(
            self.start_time.strftime('%d.%m %H:%M'), str(duration)[:-10])

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
            new_time = parse_time(snapshot['Time'])
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