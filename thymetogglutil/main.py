#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from argparse import ArgumentParser
from mixins.gitmixin import GitMixin
from mixins.thyme import ThymeMixin
from mixins.toggl import TogglMixin
from mixins.jira import JiraMixin
from thymetogglutil.utils import DateGroupMixin
from thymetogglutil import settings
import re

import logging
logger = logging.getLogger(__name__)

parser = ArgumentParser()
parser.add_argument("-f", "--file", dest="filename",
                    help="json file to parse", metavar="FILE")
parser.add_argument("-d", "--date", dest="date",
                    help="date")
parser.add_argument("-y", "--yesterday", dest="yesterday",
                    help="yesterday")
parser.add_argument("-n", "--consecutive", dest="consecutive",
                    help="consecutive", type=int)
parser.add_argument("-c", "--cutoff", dest="cutoff",
                    help="cutoff", default=900, type=int)
parser.add_argument("-a", "--api_key", dest="api_key",
                    help="api_key")


class Parser(GitMixin, JiraMixin, ThymeMixin, TogglMixin, DateGroupMixin):
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
        self.cutoff_hour = 3  # Used to group dates

    def parse_toggl(self):
        super(Parser, self).parse_toggl()
        for session in self.sessions:
            session['exported'] = self.check_session_exists(session)

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

    def parse(self):
        self.parse_git()
        self.parse_jira()
        self.parse_thyme()
        self.parse_toggl()
        self.parse_group()
