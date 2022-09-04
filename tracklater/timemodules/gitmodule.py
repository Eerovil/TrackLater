from typing import List
import git
import pytz
import os
import json
from datetime import datetime

from tracklater.utils import obj_from_dict
from tracklater import settings
from tracklater.timemodules.interfaces import EntryMixin, AbstractParser, AbstractProvider
from tracklater.models import Entry

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('GIT', key, group=group, default=default)


FIXTURE_DIR = os.path.dirname(os.path.realpath(__file__)) + "/fixture"


def git_time_to_datetime(_datetime):
    # Git has timezone-aware unix timestamps, convert that to a UTC datetime
    return _datetime.astimezone(pytz.utc).replace(tzinfo=None)


class Parser(EntryMixin, AbstractParser):
    def get_entries(self) -> List[Entry]:
        start_date = self.start_date
        end_date = self.end_date
        log = []
        provider = Provider()
        for group, data in settings.GIT.items():
            for repo_path in data.get('REPOS', []):
                for log_entry in provider.get_log_entries(repo_path, start_date=start_date):
                    if log_entry.author.email not in settings.GIT['global']['EMAILS']:
                        logger.info(log_entry.author.email)
                        continue
                    time = git_time_to_datetime(log_entry.authored_datetime)
                    if time < start_date or time > end_date:
                        continue

                    log.append(Entry(
                        text="{} - {}".format(repo_path.split('/')[-1], log_entry.message),
                        start_time=time,
                        group=group,
                    ))
        return log


class Provider(AbstractProvider):
    def get_log_entries(self, repo_path, start_date=None):
        repo = git.Repo(repo_path)
        for head in repo.heads:
            iterator = repo.iter_commits(head)
            for commit in iterator:
                try:
                    if start_date and git_time_to_datetime(commit.authored_datetime) < start_date:
                        break
                except Exception as e:
                    logger.warning(e)
                    continue
                yield commit

    def test_get_log_entries(self, repo_path, start_date=None):
        with open(FIXTURE_DIR + '/git_test_data.json', 'r') as f:
            _git = obj_from_dict(json.load(f))

        for commit in _git.commits:
            yield commit
