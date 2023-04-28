import requests
import json
import time
from typing import List, Union, cast, Any, Optional
from datetime import timedelta

from tracklater.utils import parse_time, _str
from tracklater import settings
from .interfaces import (
    EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin, AbstractParser,
    AbstractProvider
)
from tracklater.models import Entry, Project, Issue


import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('TOGGL', key, group=group, default=default)


class Parser(EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin,
             AbstractParser):
    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.provider = Provider(get_setting('API_KEY'))
        workspaces = self.provider.request('workspaces', method='GET')
        self.workspace_id = workspaces[0]['id']

    def get_entries(self) -> List[Entry]:
        if self.start_date:
            params = {'start_date': self.start_date.isoformat() + "+00:00",
                      'end_date': self.end_date.isoformat() + "+00:00"}
        else:
            params = {}
        data = self.provider.request(
            'me/time_entries', params=params, method='GET'
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
        clients = self.provider.request('me/clients', method='GET')
        projects = self.provider.request('me/projects', method='GET')
        projects = []
        toggl_settings = cast(Any, settings.TOGGL)
        for client in clients:
            groups = []  # Possible groups
            for project, data in toggl_settings.items():
                if data.get('NAME', None) == client['name']:
                    groups.append(project)
            if not groups:
                continue
            for project in projects:
                for group in groups:
                    if project['name'] in toggl_settings[group]['PROJECTS']:
                        break
                else:
                    continue
                projects.append(Project(
                    pid=project['id'],
                    title="{} - {}".format(client['name'], project['name']),
                    group=group
                ))
        return projects

    def create_entry(self, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        entry = self.push_session(
            session={
                'start_time': new_entry.start_time,
                'end_time': new_entry.end_time,
            },
            name=new_entry.title,
            project_id=new_entry.project
        )
        return Entry(
            id=_str(entry['id']),
            start_time=parse_time(entry['start']),
            end_time=parse_time(entry['stop']),
            title=entry['description'],
            project=entry.get('pid', None),
            group=new_entry.group,
        )

    def update_entry(self, entry_id: str, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        updated_entry = self.push_session(
            session={
                'start_time': new_entry.start_time,
                'end_time': new_entry.end_time,
            },
            entry_id=entry_id,
            name=new_entry.title,
            project_id=new_entry.project
        )
        logger.warning("Updated entry: %s - %s", new_entry.end_time, parse_time(updated_entry['stop']))
        if not updated_entry:
            return new_entry

        return Entry(
            id=_str(updated_entry['id']),
            start_time=parse_time(updated_entry['start']),
            end_time=parse_time(updated_entry['stop']),
            title=updated_entry['description'],
            project=_str(updated_entry.get('pid', None)),
            group=new_entry.group,
        )

    def delete_entry(self, entry_id: str) -> None:
        removed_id = self.delete_time_entry(entry_id)

        for i, entry in enumerate(self.entries):
            if entry.id == str(removed_id):
                del self.entries[i]
                break

    def push_session(self, session: dict, name: str, entry_id: str = '', project_id: str = None):
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "description": name,
            "start": session['start_time'].isoformat() + "+00:00",
            "stop": session['end_time'].isoformat() + "+00:00",
            "created_with": "thyme-toggl-cli",
            "workspace_id": self.workspace_id,
            "billable": True,
        }
        logger.warning("Pushing session: %s", data)
        if project_id:
            data['project_id'] = int(project_id) or None
        else:
            data['project_id'] = None
        if entry_id:
            try:
                return self.update_time_entry(entry_id, data)
            except Exception:
                logger.exception("Error updating entry")
                return None

        response = self.provider.request(
            'workspaces/{}/time_entries'.format(self.workspace_id), data=json.dumps(data),
            headers=headers, method='POST'
        )
        logger.warning(u'Pushed session to toggl: {}'.format(response))
        entry = response
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        return entry

    def update_time_entry(self, entry_id: str, data: dict):
        response = self.provider.request(
            'workspaces/{}/time_entries/{}'.format(self.workspace_id, entry_id),
            data=json.dumps(data), method='PUT'
        )
        logger.warning(u'Updated session to toggl: {}'.format(response))
        entry = response
        entry['start_time'] = parse_time(entry['start'])
        entry['end_time'] = parse_time(entry['stop'])
        return entry

    def delete_time_entry(self, entry_id):
        logger.warning('deleting %s', entry_id)
        response = self.provider.request(
            'workspaces/{}/time_entries/{}'.format(self.workspace_id, entry_id),
            method='DELETE'
        )
        return entry_id


class Provider(AbstractProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        self.id_counter = 4

    def request(self, endpoint: str, **kwargs) -> Union[List[dict], dict]:
        url = 'https://api.track.toggl.com/api/v9/{}'.format(endpoint)
        kwargs['headers'] = kwargs.get('headers', {
            "Content-Type": "application/json"
        })
        kwargs['auth'] = kwargs.get('auth', (self.api_key, 'api_token'))

        method = kwargs.get('method', 'POST').lower()
        try:
            del kwargs['method']
        except KeyError:
            pass
        response = getattr(requests, method)(url, **kwargs)
        if not response.content:
            return
        try:
            ret = response.json()
            if response.status_code >= 400:
                if method == "delete" and "not found" in ret.lower():
                    return  # This is ok
                logger.exception("%s: %s, - %s", url, kwargs, response.content)
                raise Exception(ret)
            return ret
        except Exception as e:
            logger.exception("%s - %s: %s", url, response.content, e)
            raise

    def test_request(self, endpoint: str, **kwargs) -> Union[List[dict], dict, str]:
        method = kwargs.get('method', 'POST').lower()
        if endpoint == "time_entries" and method == 'get':
            return [
                {
                    "id": "1",
                    "pid": "10",
                    "start": "2019-05-09T08:00:00+00:00",
                    "stop": "2019-05-09T09:00:00+00:00",
                    "description": "Toggl entry 1",
                },
                {
                    "id": "2",
                    "pid": "11",
                    "start": "2019-05-13T07:42:55+00:00",
                    "stop": "2019-05-13T08:34:52+00:00",
                    "description": "Toggl entry 2",
                },
                {
                    "id": "3",
                    "pid": "20",
                    "start": "2019-05-13T09:35:11+00:00",
                    "stop": "2019-05-13T10:34:02+00:00",
                    "description": "Toggl entry 3",
                }
            ]
        elif endpoint == "clients" and method == 'get':
            return [
                {
                    "id": "1",
                    "name": "First Client",
                },
                {
                    "id": "2",
                    "name": "Second Client",
                },
            ]
        elif endpoint.startswith("clients") and method == 'get':
            _clid = endpoint[8]
            return [
                {
                    "id": str(int(_clid) * 10),
                    "name": "Development"
                },
                {
                    "id": str(int(_clid) * 10 + 1),
                    "name": "Bug fixing"
                },
            ]
        elif endpoint == "time_entries" and method == 'post':
            entry = json.loads(kwargs['data'])['time_entry']
            entry['stop'] = (
                parse_time(entry['start']) + timedelta(seconds=entry['duration'])
            ).isoformat() + "+00:00"
            entry['id'] = self.id_counter
            self.id_counter += 1
            return {'data': entry}
        elif endpoint.startswith("time_entries") and method == 'put':
            entry = json.loads(kwargs['data'])['time_entry']
            entry['stop'] = (
                parse_time(entry['start']) + timedelta(seconds=entry['duration'])
            ).isoformat() + "+00:00"
            entry['id'] = endpoint[13:]
            return {'data': entry}
        elif endpoint.startswith("time_entries") and method == 'delete':
            return endpoint[13:]
        return [{}]
