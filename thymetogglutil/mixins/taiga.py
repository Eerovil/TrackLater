import requests
from thymetogglutil import settings
import codecs
import os
import json

import logging
logger = logging.getLogger(__name__)

AUTH_URL = 'https://api.taiga.io/api/v1/auth'
ISSUE_URL = 'https://api.taiga.io/api/v1/userstories'
PROJECT_URL = 'https://api.taiga.io/api/v1/projects/by_slug?slug={}'


class TaigaMixin(object):
    def taiga_login(self):
        credentials = settings.TAIGA_CREDENTIALS
        response = requests.post(
            AUTH_URL, data={
                'type': 'normal',
                'username': credentials[0],
                'password': credentials[1]
            }
        )
        self.token = response.json()['auth_token']
        self.headers = {
            "Authorization": "Bearer {}".format(self.token), 'x-disable-pagination': 'True'
        }
        self.issues = []
        self.taiga_projects = []
        for client, data in settings.CLIENTS.iteritems():
            if data['from'] != 'taiga':
                continue
            response = requests.get(
                PROJECT_URL.format(data['project_slug']),
                headers=self.headers
            )
            self.taiga_projects.append({
                'id': response.json()['id'],
                'slug': data['project_slug'],
                'client': client
            })

    def get_cached(self, *args, **kwargs):

        response = requests.get(*args, **kwargs)

        with codecs.open('taiga-cache', 'wb', encoding='utf8') as f:
            f.write(response.text)

        return response.json()

    def taiga_fetch_issues(self, start_from=None):
        issues = []
        for taiga_project in self.taiga_projects:
            response = requests.get(
                '{ISSUE_URL}?project={id}'.format(
                    ISSUE_URL=ISSUE_URL,
                    id=taiga_project['id']
                ), headers=self.headers
            )
            issues += response.json()
        return issues

    def _add_issue(self, issue):
        for _issue in self.issues:
            if issue['key'] == _issue['key']:
                _issue = issue
                return False
        self.issues.append(issue)
        return True

    def parse_taiga(self):
        self.taiga_login()
        self.issues = []

        latest_issues = self.taiga_fetch_issues()
        for issue in latest_issues:
            taiga_project = [p for p in self.taiga_projects if p['id'] == issue['project']][0]
            self._add_issue({
                'key': "#{}".format(issue['ref']),
                'summary': issue['subject'],
                'type': '',
                'client': taiga_project['client']
            })

    def get_issue(self, key):
        for issue in self.issues:
            if issue['key'] == key:
                return issue

    def sorted_issues(self):
        return sorted(self.issues, key=lambda x: int(x['key'][4:]), reverse=True)

    def get_issues(self):
        return [
            issue['key'] + " " + issue['summary']
            for issue in sorted(self.issues, key=lambda x: int(x['key'][4:]))
        ]
