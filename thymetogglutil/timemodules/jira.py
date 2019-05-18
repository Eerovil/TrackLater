import requests
import settings
import os
import pickle

from .interfaces import IssueMixin, AbstractParser, Issue

from typing import Any, List

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global') -> Any:
    return settings.helper('JIRA', key, group=group, default=default)


class Parser(IssueMixin, AbstractParser):
    def __init__(self, *args, **kwargs) -> None:
        super(Parser, self).__init__(*args, **kwargs)

    def get_issues(self) -> List[Issue]:
        issues: List[Issue] = []
        for group, group_settings in settings.JIRA.items():
            self.credentials = get_setting('CREDENTIALS', group=group)
            issues += self.get_group_issues(group, group_settings)
        return issues

    def get_group_issues(self, group, group_settings) -> List[Issue]:
        issues: List[Issue] = []
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

    def fetch_issues(self, url, project_key, start_from=None) -> dict:
        start_str = '&startAt={}'.format(start_from) if (start_from and start_from > 0) else ''
        response = requests.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=100{start_str}'.format(
                JIRA_URL=url, JIRA_KEY=project_key, start_str=start_str
            ), auth=self.credentials
        )
        return response.json()
