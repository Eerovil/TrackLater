import requests
import json

from thymetogglutil.utils import parse_time
from thymetogglutil import settings

import logging
logger = logging.getLogger(__name__)


class TogglMixin(object):
    def __init__(self, api_key):
        self.api_key = api_key
        response = requests.get('https://www.toggl.com/api/v8/me',
                                auth=(self.api_key, 'api_token'))
        data = response.json()['data']
        self.email = data['email']
        self.default_wid = data['default_wid']
        self.id = data['id']
        self.start_date = None
        self.end_date = None
        self.time_entries = []
        self.projects = []
        self.check_overlap()

    def request(self, endpoint, **kwargs):
        url = 'https://www.toggl.com/api/v8/{}'.format(endpoint)
        kwargs['headers'] = kwargs.get('headers', {
            "Content-Type": "application/json"
        })
        kwargs['auth'] = kwargs.get('auth', (self.api_key, 'api_token'))

        method = kwargs.get('method', 'POST').lower()
        del kwargs['method']
        return getattr(requests, method)(url, **kwargs)

    def push_session(self, session, name, entry_id=None):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            'time_entry': {
                "description": name,
                "start": session['start_time'].isoformat(),
                "duration": int((session['end_time'] - session['start_time']).total_seconds()),
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
        response = requests.put('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id),
                                data=json.dumps(data), auth=(self.api_key, 'api_token'))
        print(u'Updated session to toggl: {}'.format(response.text))
        entry = response.json()['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        self.parse_toggl()
        return entry

    def split_time_entry(self, entry_id, start_time, split_time, end_time, description):
        entry1 = self.push_session({
            "start_time": start_time,
            "end_time": split_time
        }, description, entry_id)
        entry2 = self.push_session({
            "start_time": split_time,
            "end_time": end_time
        }, description)
        return (entry1, entry2)

    def delete_time_entry(self, entry_id):
        logger.info('deleting %s', entry_id)
        response = requests.delete('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id),
                                   auth=(self.api_key, 'api_token'))
        return response.text

    def get_projects(self):
        clients = self.request('clients', method='GET').json()
        self.projects = []
        for client in clients:
            if client['name'] not in settings.CLIENTS.keys():
                continue
            settings_regex = settings.CLIENTS[client['name']]['regex']
            settings_projects = settings.CLIENTS[client['name']]['projects']
            resp = self.request('clients/{}/projects'.format(client['id']),
                                method='GET')
            my_projects = []
            for project in resp.json():
                if project['name'] not in settings_projects:
                    continue
                project['client'] = client
                project['type'] = settings_projects[project['name']]
                project['regex'] = settings_regex
                my_projects.append(project)
            self.projects += my_projects

        return self.projects

    def parse_toggl(self):
        if self.start_date:
            params = {'start_date': self.start_date.isoformat() + "+03:00",
                      'end_date': self.end_date.isoformat() + "+03:00"}
        else:
            params = {}
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.get('https://www.toggl.com/api/v8/time_entries', headers=headers,
                                params=params, auth=(self.api_key, 'api_token'))
        data = response.json()
        self.time_entries = []
        for entry in data:
            entry['start_time'] = parse_time(entry['start'])
            entry['end_time'] = parse_time(entry['stop'])
            self.time_entries.append(entry)

        self.get_projects()

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
