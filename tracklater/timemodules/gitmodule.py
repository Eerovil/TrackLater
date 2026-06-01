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


def _all_changed_files(commit) -> List[str]:
    if getattr(commit, 'changed_files', None):
        return list(commit.changed_files)
    try:
        return list(commit.stats.files.keys())
    except Exception:
        logger.debug("Could not read changed files for commit", exc_info=True)
        return []


def format_commit_entry(
    repo_name: str, branch: str, commit, max_files: int = 12
) -> str:
    message = commit.message.strip()
    subject = message.split('\n')[0] if message else ''
    header = "{} [{}] - {}".format(repo_name, branch, subject)

    lines = [header]
    all_files = _all_changed_files(commit)
    shown = all_files[:max_files]
    if shown:
        lines.extend(shown)
        if len(all_files) > len(shown):
            lines.append("... and {} more".format(len(all_files) - len(shown)))

    return "\n".join(lines)


class Parser(EntryMixin, AbstractParser):
    def get_entries(self) -> List[Entry]:
        start_date = self.start_date
        end_date = self.end_date
        log = []
        provider = Provider()
        for group, data in settings.GIT.items():
            for repo_path in data.get('REPOS', []):
                for log_entry, branch in provider.get_log_entries(
                        repo_path, start_date=start_date):
                    logger.warning(log_entry.author.email)
                    if log_entry.author.email not in settings.GIT['global']['EMAILS']:
                        logger.warning(log_entry.author.email)
                        continue
                    time = git_time_to_datetime(log_entry.authored_datetime)
                    if time < start_date or time > end_date:
                        continue

                    repo_name = repo_path.split('/')[-1]
                    log.append(Entry(
                        title="",
                        text=format_commit_entry(repo_name, branch, log_entry),
                        start_time=time,
                        group=group,
                    ))
        return log


class Provider(AbstractProvider):
    def get_log_entries(self, repo_path, start_date=None):
        try:
            repo = git.Repo(repo_path)
        except Exception:
            logger.warning(f"Error opening repo {repo_path}")
            return
        for head in repo.heads:
            iterator = repo.iter_commits(head)
            for commit in iterator:
                logger.warning(commit.author.email)
                try:
                    if start_date and git_time_to_datetime(commit.authored_datetime) < start_date:
                        break
                except Exception as e:
                    logger.warning(e)
                    continue
                yield commit, head.name

    def test_get_log_entries(self, repo_path, start_date=None):
        with open(FIXTURE_DIR + '/git_test_data.json', 'r') as f:
            _git = obj_from_dict(json.load(f))

        for commit in _git.commits:
            branch = 'main'
            if 'Branch 1' in commit.message:
                branch = 'branch1'
            elif 'Branch 2' in commit.message:
                branch = 'branch2'
            yield commit, branch
