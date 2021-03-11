import requests
import json
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
    return settings.helper('CLOCKIFY', key, group=group, default=default)


class Parser(EntryMixin, AddEntryMixin, UpdateEntryMixin, DeleteEntryMixin, ProjectMixin,
             AbstractParser):
    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)
        self.provider = Provider(get_setting('API_KEY'))
        workspaces = self.provider.request(
            'workspaces', method='GET'
        )
        if len(workspaces) > 1:
            if 'WORKSPACE' in settings.CLOCKIFY['global']:
                for workspace in workspaces:
                    if workspace['id'] == settings.CLOCKIFY['global']['WORKSPACE']:
                        self.provider.workspace = workspace
            else:
                self.provider.workspace = workspaces[0]
                logger.warning(
                    "More than one clockify workspace... Using just one (%s)",
                    self.provider.workspace['id']
                )
            
        self.user = self.provider.request(
            'user', method='GET'
        )


    def get_entries(self) -> List[Entry]:

        if self.start_date:
            params = {'start': self.start_date.isoformat() + 'Z',
                      'end': self.end_date.isoformat() + 'Z'}
        else:
            params = {}

        time_entries = []
        data = self.provider.workspace_request(
            'user/{user_id}/time-entries'.format(
                user_id=self.user['id']
            ), params=params, method='GET'
        )
        for entry in data:
            time_entries.append(Entry(
                id=entry['id'],
                start_time=parse_time(entry['timeInterval']['start']),
                end_time=parse_time(entry['timeInterval']['end']),
                title=entry['description'],
                project=entry['projectId'],
            ))

        return time_entries

    def get_projects(self) -> List[Project]:
        projects = []
        clients = self.provider.workspace_request('clients', method='GET')
        _settings = cast(Any, settings.CLOCKIFY)
        for client in clients:
            group = None
            for project, data in _settings.items():
                if data.get('NAME', None) == client['name']:
                    group = project
            if not group:
                continue
            resp = self.provider.workspace_request(
                'projects?clients={}'.format(client['id']), method='GET'
            )
            for project in resp:
                if project['name'] not in _settings[group]['PROJECTS']:
                    continue
                projects.append(Project(
                    pid=project['id'],
                    title="{} - {}".format(client['name'], project['name']),
                    group=group
                ))
        return projects

    def create_entry(self, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        if not new_entry.project or new_entry.project == '0':
            new_entry.project = None
        if new_entry.end_time is None:
            raise ValueError("No end_time")
        entry = self.provider.workspace_request(
            'time-entries',
            data=json.dumps({
                'start': new_entry.start_time.isoformat() + 'Z',
                'end': new_entry.end_time.isoformat() + 'Z',
                'description': new_entry.title,
                'projectId': new_entry.project,
            }),
            method='POST'
        )
        return Entry(
            id=_str(entry['id']),
            start_time=parse_time(entry['timeInterval']['start']),
            end_time=parse_time(entry['timeInterval']['end']),
            title=entry['description'],
            project=entry['projectId'],
        )

    def update_entry(self, entry_id: str, new_entry: Entry, issue: Optional[Issue]) -> Entry:
        if not new_entry.project or new_entry.project == '0':
            new_entry.project = None
        if new_entry.end_time is None:
            raise ValueError("No end_time")
        entry = self.provider.workspace_request(
            'time-entries/{}'.format(entry_id),
            data=json.dumps({
                'start': new_entry.start_time.isoformat() + 'Z',
                'end': new_entry.end_time.isoformat() + 'Z',
                'description': new_entry.title,
                'projectId': new_entry.project,
            }),
            method='PUT'
        )
        return Entry(
            id=_str(entry['id']),
            start_time=parse_time(entry['timeInterval']['start']),
            end_time=parse_time(entry['timeInterval']['end']),
            title=entry['description'],
            project=entry['projectId'],
        )

    def delete_entry(self, entry_id: str) -> None:
        self.provider.workspace_request(
            'time-entries/{}'.format(entry_id),
            data=json.dumps({}),
            method="DELETE"
        )


class Provider(AbstractProvider):
    def __init__(self, api_key):
        self.api_key = api_key
        self.id_counter = 4
        self.workspace = None

    def workspace_request(self, endpoint: str, **kwargs) -> Union[List[dict], dict]:
        return self.request('workspaces/{workspace_id}/{endpoint}'.format(
            workspace_id=self.workspace['id'],
            endpoint=endpoint
        ), **kwargs)

    def request(self, endpoint: str, **kwargs) -> Union[List[dict], dict]:
        url = 'https://api.clockify.me/api/v1/{}'.format(endpoint)
        kwargs['headers'] = kwargs.get('headers', {
            "Content-Type": "application/json"
        })
        kwargs['headers']['X-Api-Key'] = self.api_key

        method = kwargs.get('method', 'POST').lower()
        try:
            del kwargs['method']
        except KeyError:
            pass
        response = getattr(requests, method)(url, **kwargs)
        if method == 'delete':
            return {}
        try:
            ret = response.json()
            return ret
        except Exception as e:
            logger.exception("%s: %s", response.content, e)
            raise

    def test_request(self, endpoint: str, **kwargs) -> Union[List[dict], dict, str]:
        method = kwargs.get('method', 'POST').lower()
        return [{}]
