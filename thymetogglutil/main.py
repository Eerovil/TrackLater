#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from thymetogglutil.mixins.gitmixin import GitMixin
from thymetogglutil.mixins.thyme import ThymeMixin
from thymetogglutil.mixins.toggl import TogglMixin
from thymetogglutil.mixins.jira import JiraMixin
from thymetogglutil.mixins.taiga import TaigaMixin
from thymetogglutil.utils import DateGroupMixin
from thymetogglutil import settings
import re

import logging
logger = logging.getLogger(__name__)


class Parser(GitMixin, JiraMixin, ThymeMixin, TogglMixin, DateGroupMixin, TaigaMixin):
    def __init__(self, start_date, end_date, jira_credentials=None, git_repos=None):
        self.start_date = start_date
        self.end_date = end_date
        self.credentials = jira_credentials or settings.JIRA_CREDENTIALS
        self.repos = git_repos or settings.GIT_REPOS
        self.log = []
        self.issues = []
        self.latest_issues = {}
        self.time_entries = []
        self.sessions = []
        self.api_key = settings.API_KEY
        self.projects = (self.request("/me?with_related_data=true", method='GET')
                         .json()['data']['projects'])
        self.cutoff_hour = 3  # Used to group dates

    def parse_toggl(self):
        super(Parser, self).parse_toggl()
        for session in self.sessions:
            session['exported'] = self.check_session_exists(session)

        # toggl parser will populate self.projects with client names.
        # Now we can match issues with projects.
        for key, issue in self.latest_issues.items():
            for project in self.projects:
                name = project['client']['name']
                if name not in settings.CLIENTS:
                    continue

                # Jira issues have 'from': 'jira', and have types for bug/improvement etc
                if settings.CLIENTS[name]['from'] == 'jira' and issue.get('from', '') == 'jira':
                    if project['type'] == 'default':
                        self.latest_issues[key]['project'] = project['id']
                    if project['type'].lower() == issue['type'].lower():
                        self.latest_issues[key]['project'] = project['id']
                # Taiga issues just have the client name
                elif issue.get('client', "") == name:
                    if project['type'] == 'default':
                        self.latest_issues[key]['project'] = project['id']

    def parse_jira(self):
        super(Parser, self).parse_jira()
        for log in self.log:
            issue = None
            m = re.match('.*({}-\d+)'.format(settings.JIRA_KEY), log['message'])
            if m:
                issue = self.get_issue(m.groups()[0])
                log['issue'] = issue
                self.latest_issues[issue['key']] = issue

        for issue in self.sorted_issues()[:100]:
            self.latest_issues[issue['key']] = issue

    def parse_taiga(self):
        self.issues = []
        super(Parser, self).parse_taiga()
        # Dump all taiga issues to latest issues (other issues will not be sent to client)
        for issue in self.issues:
            self.latest_issues[issue['key']] = issue

    def parse(self):
        self.parse_git()
        self.parse_jira()
        self.parse_taiga()
        self.parse_thyme()
        self.parse_toggl()
        self.parse_group()
