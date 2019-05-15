#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib

from thymetogglutil.mixins.toggl import TogglMixin
from thymetogglutil.mixins.jira import JiraMixin
from thymetogglutil.utils import DateGroupMixin
from thymetogglutil import settings
import re

import logging
logger = logging.getLogger(__name__)


class Parser(JiraMixin, TogglMixin, DateGroupMixin):
    def __init__(self, start_date, end_date, jira_credentials=None):
        self.start_date = start_date
        self.end_date = end_date
        self.credentials = jira_credentials or settings.JIRA_CREDENTIALS
        self.log = []
        self.issues = []
        self.latest_issues = {}
        self.time_entries = []
        self.sessions = []
        self.projects = (self.request("/me?with_related_data=true", method='GET')
                         .json()['data']['projects'])
        self.cutoff_hour = 3  # Used to group dates
        self.slack_messages = []
        self.modules = {}

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
            m = re.match('.*({}-\d+)'.format(settings.JIRA_KEY), log['extra_data']['message'])
            if m:
                issue = self.get_issue(m.groups()[0])
                log['extra_data']['issue'] = issue
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
        for module_name in settings.ENABLED_TIMEMODULES:
            module = importlib.import_module('thymetogglutil.timemodules.{}'.format(module_name))
            parser = module.Parser(self.start_date, self.end_date)
            parser.parse()
            self.modules[module_name] = parser
            parser = None

        for module_name in settings.ENABLED_ISSUEMODULES:
            module = importlib.import_module('thymetogglutil.issuemodules.{}'.format(module_name))
            parser = module.Parser()
            parser.parse()
            self.modules[module_name] = parser
            parser = None
