import requests
from thymetogglutil import settings
import codecs
import os
import json

import logging
logger = logging.getLogger(__name__)


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
        start_str = '&startAt={}'.format(start_from) if (start_from is not None and start_from > 0) else ''
        response = requests.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary&maxResults=100'
            '{start_str}'.format(
                JIRA_URL=settings.JIRA_URL, JIRA_KEY=settings.JIRA_KEY, start_str=start_str
            ), auth=self.credentials
        )
        logging.warning(response.text)
        return response.json()

    def _add_issue(self, issue):
        for _issue in self.issues:
            if issue['key'] == _issue['key']:
                _issue = issue
                return False
        self.issues.append(issue)
        return True

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
        run_once = False
        while latest_issues['total'] - len(self.issues) > 0 or not run_once:
            run_once = True
            logging.warning('Fetching issues %s to %s', len(self.issues), len(self.issues) + 100)
            new_issues = self.fetch_issues(
                start_from=(latest_issues['total'] - len(self.issues) - 100)
            )['issues']
            for issue in new_issues:
                self._add_issue({
                    'key': issue['key'],
                    'summary': issue['fields']['summary'],
                })
            with codecs.open('jira-cache', 'wb', encoding='utf8') as f:
                f.write(json.dumps(self.issues))
        logging.warning(self.get_issues()[-10:])

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
