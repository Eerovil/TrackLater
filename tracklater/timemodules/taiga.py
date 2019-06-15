import requests
from typing import List, cast, Any

from tracklater import settings
from .interfaces import IssueMixin, AbstractParser, AbstractProvider
from tracklater.models import Issue

import logging
logger = logging.getLogger(__name__)

AUTH_URL = 'https://api.taiga.io/api/v1/auth'
ISSUE_URL = 'https://api.taiga.io/api/v1/userstories'
PROJECT_URL = 'https://api.taiga.io/api/v1/projects/by_slug?slug={}'


class Parser(IssueMixin, AbstractParser):
    def get_issues(self) -> List[Issue]:
        self.taiga_login()
        issues: List[Issue] = []

        latest_issues = self.taiga_fetch_issues()
        for issue in latest_issues:
            taiga_project = [p for p in self.taiga_projects if p['id'] == issue['project']][0]
            issues.append(Issue(
                key="#{}".format(issue['ref']),
                id=issue['id'],
                title=issue['subject'],
                group=taiga_project['group']
            ))
        return issues

    def taiga_login(self) -> None:
        taiga_settings = cast(Any, settings.TAIGA)
        self.provider = Provider(taiga_settings['global']['CREDENTIALS'])
        self.taiga_projects: List[dict] = []
        # Get taiga project id for all clients
        # "No client" not supported yet
        for group, data in taiga_settings.items():
            if 'project_slug' not in data:
                continue
            project = self.provider.get_project(data['project_slug'])
            self.taiga_projects.append({
                'id': project['id'],
                'group': group
            })

    def taiga_fetch_issues(self, start_from=None):
        issues: List[dict] = []
        for taiga_project in self.taiga_projects:
            issues += self.provider.get_issues(taiga_project['id'])
        return issues


class Provider(AbstractProvider):
    def __init__(self, credentials):
        self.token = self.login(credentials)
        self.headers = {
            "Authorization": "Bearer {}".format(self.token), 'x-disable-pagination': 'True'
        }

    def login(self, credentials):
        response = requests.post(
            AUTH_URL, data={
                'type': 'normal',
                'username': credentials[0],
                'password': credentials[1]
            }
        )
        return response.json()['auth_token']

    def test_login(self, credentials):
        return ""

    def get_project(self, project_slug):
        response = requests.get(
            PROJECT_URL.format(project_slug),
            headers=self.headers
        )
        return response.json()

    def test_get_project(self, credentials):
        return {'id': "1"}

    def get_issues(self, project_id):
        response = requests.get(
            '{ISSUE_URL}?project={id}'.format(
                ISSUE_URL=ISSUE_URL,
                id=project_id
            ), headers=self.headers
        )
        return response.json()

    def test_get_issues(self, credentials):
        return [
            {
                "ref": "1",
                "id": "1",
                "subject": "Taiga issue 1",
                "project": "1"
            },
            {
                "ref": 2,
                "id": "2",
                "subject": "Taiga issue 2",
                "project": "1"
            },
            {
                "ref": 3,
                "id": "3",
                "subject": "Taiga issue 3",
                "project": "1"
            }
        ]
