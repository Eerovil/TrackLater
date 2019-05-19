import requests
import settings

from timemodules.interfaces import IssueMixin, AbstractParser, Issue

from typing import List, Dict, Any

import logging
logger = logging.getLogger(__name__)

taiga_settings: Dict[str, Any] = settings.TAIGA

AUTH_URL = 'https://api.taiga.io/api/v1/auth'
ISSUE_URL = 'https://api.taiga.io/api/v1/userstories'
PROJECT_URL = 'https://api.taiga.io/api/v1/projects/by_slug?slug={}'


class Parser(IssueMixin, AbstractParser):
    def get_issues(self) -> List[Issue]:
        self.taiga_login()
        issues = []

        latest_issues = self.taiga_fetch_issues()
        for issue in latest_issues:
            taiga_project = [p for p in self.taiga_projects if p['id'] == issue['project']][0]
            issues.append(Issue(
                key="#{}".format(issue['ref']),
                title=issue['subject'],
                group=taiga_project['group']
            ))
        return issues

    def taiga_login(self) -> None:
        credentials = taiga_settings['global']['CREDENTIALS']
        response = requests.post(
            AUTH_URL, data={
                'type': 'normal',
                'username': credentials[0],
                'password': credentials[1]
            }
        )
        token = response.json()['auth_token']
        self.headers = {
            "Authorization": "Bearer {}".format(token), 'x-disable-pagination': 'True'
        }
        self.issues = []
        self.taiga_projects: List[dict] = []
        # Get taiga project id for all clients
        # "No client" not supported yet
        for group, data in taiga_settings.items():
            if 'project_slug' not in data:
                continue
            response = requests.get(
                PROJECT_URL.format(data['project_slug']),
                headers=self.headers
            )
            self.taiga_projects.append({
                'id': response.json()['id'],
                'group': group
            })

    def taiga_fetch_issues(self, start_from=None):
        issues: List[dict] = []
        for taiga_project in self.taiga_projects:
            response = requests.get(
                '{ISSUE_URL}?project={id}'.format(
                    ISSUE_URL=ISSUE_URL,
                    id=taiga_project['id']
                ), headers=self.headers
            )
            issues += response.json()
        return issues
