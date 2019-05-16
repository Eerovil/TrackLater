import requests
from thymetogglutil import settings
import codecs
import os
import pickle

from .interfaces import IssueMixin, AbstractParser, Issue

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('JIRA', key, group=group, default=default)


class Parser(IssueMixin, AbstractParser):
    def __init__(self, *args, **kwargs):
        super(Parser, self).__init__(*args, **kwargs)

    def get_issues(self):
        issues = []
        for group, group_settings in settings.JIRA.items():
            self.credentials = get_setting('CREDENTIALS', group=group)
            issues += self.get_group_issues(group, group_settings)
        return issues

    def get_group_issues(self, group, group_settings):
        issues = []
        filename = '{}.jira-cache'.format(group)
        if os.path.exists(filename):
            try:
                with open(filename, 'rb') as f:
                    issues = pickle.load(f)
            except Exception:
                print('cache error')
                os.remove(filename)

        latest_issues = self.fetch_issues(
            project_key=group_settings['PROJECT_KEY'],
            url=group_settings['URL']
        )
        logging.warning('latest_issues: %s cached: %s', latest_issues['total'], len(issues))
        run_once = False
        while latest_issues['total'] - len(issues) > 0 or not run_once:
            run_once = True
            logging.info('Fetching issues %s to %s', len(issues), len(issues) + 100)
            new_issues = self.fetch_issues(
                url=group_settings['URL'],
                project_key=group_settings['PROJECT_KEY'],
                start_from=(latest_issues['total'] - len(issues) - 100)
            )['issues']
            for issue in new_issues:
                issues.append(Issue(
                    key=issue['key'],
                    title=issue['fields']['summary'],
                    group=group,
                    extra_data={'type': issue['fields']['issuetype']['name']},
                ))
            with open(filename, 'wb') as f:
                pickle.dump(issues, f)
        return issues

    def fetch_issues(self, url, project_key, start_from=None):
        start_str = '&startAt={}'.format(start_from) if (start_from and start_from > 0) else ''
        response = requests.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=100{start_str}'.format(
                JIRA_URL=url, JIRA_KEY=project_key, start_str=start_str
            ), auth=self.credentials
        )
        return response.json()

    def get_issue(self, key):
        for issue in self.issues:
            if issue['key'] == key:
                return issue

    def sorted_issues(self):
        return sorted(self.issues, key=lambda x: int(x['key'][4:]), reverse=True)
