import requests
import json

from utils import parse_time, _str
import settings
from timemodules.interfaces import (
    EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin, AbstractParser,
    Entry, Project, Issue, AbstractProvider
)

from typing import List, Dict

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('TOGGL', key, group=group, default=default)


class Parser(EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin,
             AbstractParser):
    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.provider = Provider(get_setting('API_KEY'))

    def get_entries(self) -> List[Entry]:
        if self.start_date:
            params = {'start_date': self.start_date.isoformat() + "+03:00",
                      'end_date': self.end_date.isoformat() + "+03:00"}
        else:
            params = {}
        data = self.provider.request(
            'time_entries', params=params, method='GET'
        )
        time_entries = []
        for entry in data:
            time_entries.append(Entry(
                id=entry['id'],
                start_time=parse_time(entry['start']),
                end_time=parse_time(entry['stop']),
                title=entry.get('description', ''),
                project=entry.get('pid', None),
            ))

        return time_entries

    def get_projects(self) -> List[Project]:
        clients = self.provider.request('clients', method='GET')
        projects = []
        for client in clients:
            group = None
            for project, data in settings.TOGGL.items():
                if data.get('NAME', None) == client['name']:
                    group = project
            if not group:
                continue
            resp = self.provider.request(
                'clients/{}/projects'.format(client['id']), method='GET'
            )
            for project in resp:
                if project['name'] not in settings.TOGGL[group]['PROJECTS']:
                    continue
                projects.append(Project(
                    id=project['id'],
                    title="{} - {}".format(client['name'], project['name']),
                    group=group
                ))
        return projects

    def create_entry(self, new_entry: Entry, issue: Issue) -> str:
        entry = self.push_session(
            session={
                'start_time': new_entry.start_time,
                'end_time': new_entry.end_time,
            },
            name=new_entry.title,
            project_id=new_entry.project
        )
        self.entries.append(Entry(
            id=entry['id'],
            start_time=parse_time(entry['start']),
            end_time=parse_time(entry['stop']),
            title=entry['description'],
            project=entry.get('pid', None),
        ))
        return _str(entry['id']) or entry['id']

    def update_entry(self, entry_id: str, new_entry: Entry, issue: Issue) -> None:
        updated_entry = self.push_session(
            session={
                'start_time': new_entry.start_time,
                'end_time': new_entry.end_time,
            },
            entry_id=entry_id,
            name=new_entry.title,
            project_id=new_entry.project
        )

        for i, entry in enumerate(self.entries):
            if entry.id == str(updated_entry['id']):
                entry.start_time = parse_time(updated_entry['start'])
                entry.end_time = parse_time(updated_entry['stop'])
                entry.title = updated_entry.get('description', '')
                entry.project = updated_entry.get('pid')
                self.entries[i] = entry
                break

    def delete_entry(self, entry_id: str) -> None:
        self.delete_time_entry(entry_id)

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

        response = self.provider.request(
            'time_entries', data=json.dumps(data), headers=headers,
        )
        print(u'Pushed session to toggl: {}'.format(response))
        entry = response['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        return entry

    def update_time_entry(self, entry_id: str, data: dict):
        response = self.provider.request(
            'time_entries/{}'.format(entry_id), data=json.dumps(data), method='PUT'
        )
        print(u'Updated session to toggl: {}'.format(response))
        entry = response['data']
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        return entry

    def delete_time_entry(self, entry_id):
        logger.info('deleting %s', entry_id)
        response = self.provider.request(
            'time_entries/{}'.format(entry_id), method='DELETE'
        )
        return response


class Provider(AbstractProvider):
    def __init__(self, api_key):
        self.api_key = api_key

    def request(self, endpoint: str, **kwargs) -> dict:
        url = 'https://www.toggl.com/api/v8/{}'.format(endpoint)
        kwargs['headers'] = kwargs.get('headers', {
            "Content-Type": "application/json"
        })
        kwargs['auth'] = kwargs.get('auth', (self.api_key, 'api_token'))

        method = kwargs.get('method', 'POST').lower()
        del kwargs['method']
        return getattr(requests, method)(url, **kwargs).json()

    def test_request(self, endpoint: str, **kwargs) -> dict:
        method = kwargs.get('method', 'POST').lower()
        if endpoint == "time_entries" and method == 'get':
            return [
                {
                    "id": 1,
                    "pid": 10,
                    "start": "2019-05-09T08:00:00+00:00",
                    "stop": "2019-05-09T09:00:00+00:00",
                    "description": "Toggl entry 1",
                },
                {
                    "id": 2,
                    "pid": 11,
                    "start": "2019-05-13T07:42:55+00:00",
                    "stop": "2019-05-13T08:34:52+00:00",
                    "description": "Toggl entry 2",
                },
                {
                    "id": 3,
                    "pid": 20,
                    "start": "2019-05-13T09:35:11+00:00",
                    "stop": "2019-05-13T10:34:02+00:00",
                    "description": "Toggl entry 3",
                }
            ]
        elif endpoint == "clients" and method == 'get':
            return [
                {
                    "id": 1,
                    "name": "First Client",
                },
                {
                    "id": 2,
                    "name": "Second Client",
                },
            ]
        elif endpoint.startswith("clients") and method == 'get':
            _clid = endpoint[8]
            return [
                {
                    "id": int(_clid) * 10,
                    "name": "Development"
                },
                {
                    "id": int(_clid) * 10 + 1,
                    "name": "Bug fixing"
                },
            ]
        elif endpoint == "time_entries" and method == 'post':
            return json.loads(kwargs['data'])
        elif endpoint.startswith("time_entries") and method == 'put':
            return json.loads(kwargs['data'])
        elif endpoint.startswith("time_entries") and method == 'delete':
            return endpoint[12:]
