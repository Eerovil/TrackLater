import requests
import json

from thymetogglutil.utils import parse_time
from thymetogglutil import settings
from thymetogglutil.timemodules.interfaces import (
    EntryMixin, ProjectMixin, AbstractParser, Entry, Project
)

from typing import List

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('TOGGL', key, group=group, default=default)


class Parser(EntryMixin, ProjectMixin, AbstractParser):
    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.api_key = get_setting('API_KEY')
        response = requests.get('https://www.toggl.com/api/v8/me?with_related_data=true',
                                auth=(self.api_key, 'api_token'))
        data = response.json()['data']
        self.email = data['email']
        self.default_wid = data['default_wid']
        self.id = data['id']
        self.time_entries = []
        self.projects = data['projects']

    def get_entries(self) -> List[Entry]:
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
        time_entries = []
        for entry in data:
            time_entries.append(Entry(
                start_time=parse_time(entry['start']),
                end_time=parse_time(entry['stop']),
                title=entry['description'],
                project=entry.get('pid', None)
            ))

        return time_entries

    def get_projects(self) -> List[Project]:
        clients = self.request('clients', method='GET').json()
        projects = []
        for client in clients:
            group = None
            for project, data in settings.TOGGL.items():
                if data.get('NAME', None) == client['name']:
                    group = project
            if not group:
                continue
            resp = self.request('clients/{}/projects'.format(client['id']),
                                method='GET')
            for project in resp.json():
                if project['name'] not in settings.TOGGL[group]['PROJECTS']:
                    continue
                projects.append(Project(
                    id=project['id'],
                    title="{} - {}".format(client['name'], project['name']),
                    group=group
                ))
        return projects

    def request(self, endpoint: str, **kwargs) -> requests.Response:
        url = 'https://www.toggl.com/api/v8/{}'.format(endpoint)
        kwargs['headers'] = kwargs.get('headers', {
            "Content-Type": "application/json"
        })
        kwargs['auth'] = kwargs.get('auth', (self.api_key, 'api_token'))

        method = kwargs.get('method', 'POST').lower()
        del kwargs['method']
        return getattr(requests, method)(url, **kwargs)

    def push_session(self, session: dict, name: str, entry_id: str = '', project_id: str = None):
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
        if project_id:
            data['time_entry']['pid'] = project_id
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

    def update_time_entry(self, entry_id: str, data: dict):
        response = requests.put('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id),
                                data=json.dumps(data), auth=(self.api_key, 'api_token'))
        print(u'Updated session to toggl: {}'.format(response.text))
        entry = response.json()['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        self.parse_toggl()
        return entry

    def delete_time_entry(self, entry_id):
        logger.info('deleting %s', entry_id)
        response = requests.delete('https://www.toggl.com/api/v8/time_entries/{}'.format(entry_id),
                                   auth=(self.api_key, 'api_token'))
        return response.text

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
