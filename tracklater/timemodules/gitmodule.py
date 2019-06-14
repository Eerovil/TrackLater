from typing import List
import git
import pytz
import os
import json
from datetime import datetime

from tracklater.utils import FixedOffset, obj_from_dict
from tracklater import settings
from tracklater.timemodules.interfaces import EntryMixin, AbstractParser, AbstractProvider
from tracklater.models import Entry

import logging
logger = logging.getLogger(__name__)


def get_setting(key, default=None, group='global'):
    return settings.helper('GIT', key, group=group, default=default)


FIXTURE_DIR = os.path.dirname(os.path.realpath(__file__)) + "/fixture"


def timestamp_to_datetime(timestamp: List):
    # Git has timezone-aware unix timestamps, convert that to a UTC datetime
    return datetime.fromtimestamp(
        timestamp[0], tz=FixedOffset(timestamp[1], '')
    ).astimezone(pytz.utc).replace(tzinfo=None)


class Parser(EntryMixin, AbstractParser):
    def get_entries(self) -> List[Entry]:
        start_date = self.start_date
        end_date = self.end_date
        log = []
        provider = Provider()
        for group, data in settings.GIT.items():
            for repo_path in data.get('REPOS', []):
                for log_entry in provider.get_log_entries(repo_path):
                    if log_entry.actor.email not in settings.GIT['global']['EMAILS']:
                        continue
                    if not log_entry.message.startswith('commit'):
                        continue
                    message = ''.join(log_entry.message.split(':')[1:])
                    time = timestamp_to_datetime(log_entry.time)
                    if time < start_date or time > end_date:
                        continue

                    log.append(Entry(
                        text="{} - {}".format(repo_path.split('/')[-1], message),
                        start_time=time,
                    ))
        return log


class Provider(AbstractProvider):
    def get_log_entries(self, repo_path):
        repo = git.Repo(repo_path)
        for branch in repo.branches:
            try:
                entries = branch.log()
            except Exception as e:
                logger.warning(e)
                continue
            for log_entry in entries:
                yield log_entry

    def test_get_log_entries(self, repo_path):
        with open(FIXTURE_DIR + '/git_test_data.json', 'r') as f:
            _git = obj_from_dict(json.load(f))

        repo = _git.Repo(repo_path)
        for branch in repo.branches:
            try:
                entries = branch.log()
            except Exception as e:
                logger.warning(e)
                continue
            for log_entry in entries:
                yield log_entry
