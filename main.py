#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from datetime import date, datetime, timedelta, tzinfo
from dateutil import parser as dateparser
from colorama import Fore, Style
import requests
import json
import settings
import time
import git
import re
import os
import codecs

import logging

parser = ArgumentParser()
parser.add_argument("-f", "--file", dest="filename",
                    help="json file to parse", metavar="FILE")
parser.add_argument("-d", "--date", dest="date",
                    help="date")
parser.add_argument("-y", "--yesterday", dest="yesterday",
                    help="yesterday")
parser.add_argument("-n", "--consecutive", dest="consecutive",
                    help="consecutive", type=int)
parser.add_argument("-c", "--cutoff", dest="cutoff",
                    help="cutoff", default=900, type=int)
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

    toggl.start_date = datetime.combine(_date - timedelta(days=1), datetime.min.time(), )

    filenames = [filename]
    if args.consecutive:
        for i in range(args.consecutive):
            _date = _date + timedelta(days=1)
            filenames.append('../thyme/{}.json'.format(_date.strftime('%Y-%m-%d')))

    toggl.end_date = datetime.combine(_date + timedelta(days=1), datetime.min.time())

    toggl.parse_toggl()

    sessions = SessionGenerator()

    for filename in filenames:
        print("opening file {}".format(filename))
        with open(filename) as f:
            data = json.load(f)
            snapshots = data.get('Snapshots')
            sessions.add(snapshots)
    
    sessions.generate()
    
    while True:
        print_sessions(sessions)
        uinput = raw_input("select command (w, p, q): ")
        if uinput not in ['w', 'p', 'q']:
            continue
        command = uinput
        if command == 'q':
            break
        uinput = raw_input("Select session (1-{}): ".format(len(sessions.sessions)))
        try:
            selection = parse_selection(uinput)
            if command == 'w':
                for i in selection:
                    sessions.sessions[i].print_windows()
            elif command == 'p':
                print("\n".join(parser.get_issues()))
                name = raw_input("Name: ")
                if uinput == 'q':
                    continue
                for i in selection:
                    toggl.push_session(sessions.sessions[i], name)
            time.sleep(2)
        except Exception as e:
            raise

def parse_selection(uinput):
    if '-' in uinput:
        vals = [int(i)-1 for i in uinput.split('-')]
        return range(vals[0], vals[1]+1)
    return [int(uinput)-1]

def print_sessions(sessions):
    count = 1
    for session in sessions.sessions:
        entry_id = toggl.check_session_exists(session)
        category = session.guess_category()
        if category == 'work':
            color = Fore.RED
            if entry_id:
                color = Fore.GREEN
                if not toggl.get_entry(entry_id).get('description', None):
                    color = Fore.MAGENTA
        else:
            color = Fore.GREEN
            if entry_id:
                color = Fore.RED
        print u"{}{}. {} {} - {}{}".format(color,
            count, session.print_out(out=False),
            u'exported: {}'.format(toggl.get_entry(entry_id).get('description', '')) if entry_id else '',
            category,
            Style.RESET_ALL
        )
        print ""
        for window in session.sorted_windows()[-3:]:
            print u"    {}s - {}".format(
                session.windows[window], window
            )
        print ""
        for commit in parser.get_commits(session.start_time, session.end_time):
            print u"    {} - {}".format(
                commit['message'],
                commit['issue'].get('summary', None) if commit['issue'] else None
            )
        print ""
        count += 1


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
            filenames.append('../thyme/{}.json'.format(date.strftime('%Y-%m-%d')))
            date = date + timedelta(days=1)

        for filename in filenames:
            logging.info("opening file {}".format(filename))
            with open(filename) as f:
                data = json.load(f)
                snapshots = data.get('Snapshots')
                generator.add(snapshots)

        generator.generate()

        self.sessions = generator.to_list()


class TogglMixin(object):
    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get('https://www.toggl.com/api/v8/me', auth=(self.api_key, 'api_token'))
        data = response.json()['data']
        self.email = data['email']
        self.default_wid = data['default_wid']
        self.id = data['id']
        self.start_date = None
        self.end_date = None
        self.check_overlap()

    def push_session(self, session, name, entry_id=None):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            'time_entry': {
                "description": name,
                "start": session['start_time'].isoformat(),
                "duration": (session['end_time'] - session['start_time']).seconds,
                "created_with": "thyme-toggl-cli"
            }
        }
        if entry_id:
            return self.update_time_entry(entry_id, data)

        response = requests.post(
            'https://www.toggl.com/api/v8/time_entries',
            data=json.dumps(data), headers=headers, auth=(self.api_key, 'api_token'))
        print(u'Pushed session to toggl: {}'.format(response.text))
        entry = response.json()['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        return entry

    def update_time_entry(self, entry_id, data):
        response = requests.put('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id), data=json.dumps(data), auth=(self.api_key, 'api_token'))
        print(u'Updated session to toggl: {}'.format(response.text))
        entry = response.json()['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        self.parse_toggl()
        return entry

    def parse_toggl(self):
        if self.start_date:
            params = {'start_date': self.start_date.isoformat() + "+03:00", 'end_date': self.end_date.isoformat() + "+03:00"}
        else:
            params = {}
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.get('https://www.toggl.com/api/v8/time_entries', headers=headers, params=params, auth=(self.api_key, 'api_token'))
        data = response.json()
        self.time_entries = []
        for entry in data:
            entry['start_time'] = parse_time(entry['start'])
            entry['end_time'] = parse_time(entry['stop'])
            self.time_entries.append(entry)
        return self.time_entries

    def check_overlap(self):
        for entry1 in self.time_entries:
            for entry2 in self.time_entries:
                if entry1 == entry2:
                    continue
                start1 = (entry1['start_time'])
                stop1 = (entry1['end_time'])
                start2 = (entry2['start_time'])
                stop2 = (entry2['end_time'])
                if start1 <= start2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)
                elif start1 <= stop2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)
                elif start1 <= start2 and stop2 <= stop1:
                    print "OVERLAP IN ENTRY {}".format(start1)

        return None
    
    def get_entry(self, entry_id):
        for entry in self.time_entries:
            if entry['id'] == entry_id:
                return entry
    
    def check_session_exists(self, session):
        for entry in self.time_entries:
            start = (entry['start_time'])
            stop = (entry['end_time'])
            if start <= session['start_time'] <= stop:
                return entry['id']
            if start <= session['end_time'] <= stop:
                return entry['id']
            if session['start_time'] <= start and stop <= session['end_time']:
                return entry['id']
            if start <= session['start_time'] and session['end_time'] <= stop:
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
            if snapshot['Active'] == last_active:
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
            last_active = snapshot['Active']
        self.end_session(new_time)

    def to_list(self):
        return [session.to_dict() for session in self.sessions]


class GitMixin(object):
    def __init__(self, repos):
        self.repos = repos
        self.log = []  # List of git.refs.log.RefLogEntry objects
    
    def parse_git(self):
        for repo_path in self.repos:
            repo = git.Repo(repo_path)
            for branch in repo.branches:
                for log_entry in branch.log():
                    if log_entry.actor.email not in settings.GIT_EMAILS:
                        continue
                    if not log_entry.message.startswith('commit'):
                        continue
                    message = ''.join(log_entry.message.split(':')[1:])
                    self.log.append({
                        'repo': repo_path.split('/')[-1],
                        'message': message,
                        'time': datetime.fromtimestamp(
                            log_entry.time[0], tz=FixedOffset(log_entry.time[1], 'Helsinki')
                        ),
                    })
    
    def get_commits(self, start_time, end_time):
        ret = []
        for log in self.log:
            if start_time <= log['time'] <= end_time:
                ret.append(log)
        return ret

    def print_commits(self, out=True, sort='time'):
        print_str = (
            "\n".join(['{} - {} - {}'.format(
                log['time'], log['repo'], log['message']
            ) for log in sorted(self.log, key=lambda x: x[sort])])
        )
        if out:
            print(print_str)
        return print_str

class FixedOffset(tzinfo):
    """Fixed offset in minutes west from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(seconds = -offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)

class JiraMixin(object):
    def __init__(self, credentials):
        self.credentials = credentials
        self.issues = []

    def get_cached(self, *args, **kwargs):

        response = requests.get(*args, **kwargs)

        with codecs.open('jira-cache', 'wb', encoding='utf8') as f:
            f.write(response.text)

        return response.json()

    def fetch_issues(self, start_from=None):
        start_str = '&startAt={}'.format(start_from) if start_from is not None else ''
        response = requests.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary&maxResults=100'
            '{start_str}'.format(
                JIRA_URL=settings.JIRA_URL, JIRA_KEY=settings.JIRA_KEY, start_str=start_str
            ), auth=self.credentials
        )
        return response.json()

    def parse_jira(self):
        self.issues = []
        if os.path.exists('jira-cache'):
            try:
                with codecs.open('jira-cache', 'rb', encoding='utf8') as f:
                    self.issues = json.load(f)
            except ValueError:
                print 'cache error'

        latest_issues = self.fetch_issues()
        logging.warning('latest_issues: %s cached: %s', latest_issues['total'], len(self.issues))
        while latest_issues['total'] - len(self.issues) > 0:
            logging.warning('Fetching issues %s to %s', len(self.issues), len(self.issues) + 100)
            for issue in self.fetch_issues(start_from=len(self.issues))['issues']:
                self.issues.append({
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                })
            with codecs.open('jira-cache', 'wb', encoding='utf8') as f:
                f.write(json.dumps(self.issues))
    
    def get_issue(self, key):
        for issue in self.issues:
            if issue['key'] == key:
                return issue
    
    def get_issues(self):
        return [issue['key'] + " " + issue['summary'] for issue in sorted(self.issues, key=lambda x: x['key'])]


class DateGroupMixin(object):
    """
    Includes a 'date_group' key that allows grouping entries by date.
    """
    def __init__(self):
        self.cutoff_hour = 3

    def _parse_list(self, l, key='start_time'):
        for item in l:
            item_time = item[key]
            offset = item_time.tzinfo.utcoffset(None)
            _cutoff = self.cutoff_hour + (getattr(offset, 'seconds', 0) / 3600)
            if item_time.hour >= _cutoff:
                item['date_group'] = item_time.strftime('%Y-%m-%d')
            else:
                item['date_group'] = (item_time - timedelta(days=1)).strftime('%Y-%m-%d')

    def parse_group(self):
        self._parse_list(self.sessions)
        self._parse_list(self.time_entries)
        self._parse_list(self.log, key='time')


class Parser(GitMixin, JiraMixin, ThymeMixin, TogglMixin, DateGroupMixin):
    def __init__(self, start_date, end_date, jira_credentials=None, git_repos=None):
        self.start_date = start_date
        self.end_date = end_date
        self.credentials = jira_credentials or settings.JIRA_CREDENTIALS
        self.repos = git_repos or settings.GIT_REPOS
        self.log = []
        self.issues = []
        self.time_entries = []
        self.sessions = []
        self.api_key = settings.API_KEY
        self.cutoff_hour = 3  # Used to group dates

    def parse_toggl(self):
        super(Parser, self).parse_toggl()
        for session in self.sessions:
            session['exported'] = self.check_session_exists(session)

    def parse_jira(self):
        super(Parser, self).parse_jira()
        for log in self.log:
            issue = None
            m = re.match('.*({}-\d+)'.format(settings.JIRA_KEY), log['message'])
            if m:
                issue = self.get_issue(m.groups()[0])
            log['issue'] = issue

    def parse(self):
        self.parse_git()
        self.parse_jira()
        self.parse_thyme()
        self.parse_toggl()
        self.parse_group()


if __name__ == '__main__':
    args = parser.parse_args()
    parser = Parser(settings.JIRA_CREDENTIALS, settings.GIT_REPOS)
    parser.parse()
    main()