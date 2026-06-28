from typing import List
import git
import pytz
import os
import json
import subprocess
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
FETCH_TIMEOUT = 60  # seconds, per repo


def _sync_repo(repo_path: str) -> None:
    """Refresh a clone before reading so commits pushed elsewhere are seen.

    Runs `git fetch --all` (or the configured GIT.FETCH_COMMAND) — fetch only,
    never a merge or working-tree change, so there is no conflict risk. Runs
    non-interactively (GIT_TERMINAL_PROMPT=0) so a missing credential can't hang
    the parse, and any failure is logged and ignored so one unreachable remote
    doesn't sink the whole run. Gate with GIT.global.FETCH (default off; needs the
    container to have a usable SSH credential — e.g. a forwarded agent)."""
    command = get_setting('FETCH_COMMAND', default='')
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    # Use the mounted key and trust-on-first-use for host keys, so a container
    # without a pre-seeded known_hosts can still fetch over SSH. Overridable.
    env.setdefault('GIT_SSH_COMMAND', 'ssh -o StrictHostKeyChecking=accept-new')
    try:
        if command:
            proc = subprocess.run(
                command, cwd=repo_path, env=env, shell=True,
                timeout=FETCH_TIMEOUT, capture_output=True,
            )
        else:
            proc = subprocess.run(
                ['git', 'fetch', '--all', '--quiet'], cwd=repo_path, env=env,
                timeout=FETCH_TIMEOUT, capture_output=True,
            )
        if proc.returncode != 0:
            logger.warning(
                "git sync for %s exited %s: %s", repo_path, proc.returncode,
                (proc.stderr or b'')[:300],
            )
    except Exception as e:  # noqa: BLE001 - sync is best-effort
        logger.warning("git sync failed for %s: %s", repo_path, e)


def git_time_to_datetime(_datetime):
    # Git has timezone-aware unix timestamps, convert that to a UTC datetime
    return _datetime.astimezone(pytz.utc).replace(tzinfo=None)


def _commit_id(commit) -> str:
    hexsha = getattr(commit, 'hexsha', None)
    if hexsha:
        return hexsha
    message = (getattr(commit, 'message', None) or '').strip()
    subject = message.split('\n', 1)[0] if message else ''
    authored = getattr(commit, 'authored_datetime', None)
    if authored is not None:
        return '{}|{}'.format(git_time_to_datetime(authored).isoformat(), subject)
    return subject or 'unknown'


def _all_changed_files(commit) -> List[str]:
    if getattr(commit, 'changed_files', None):
        return list(commit.changed_files)
    try:
        return list(commit.stats.files.keys())
    except Exception:
        logger.debug("Could not read changed files for commit", exc_info=True)
        return []


def _exclusive_rev(head_name: str, other_head_names: List[str]) -> List[str]:
    """Revision list: commits reachable from head but not from other heads."""
    rev: List[str] = [head_name]
    rev.extend('^{}'.format(name) for name in other_head_names)
    return rev


def _is_ancestor_of(repo: git.Repo, commit, ref: str) -> bool:
    try:
        repo.git.merge_base('--is-ancestor', commit.hexsha, ref)
        return True
    except git.GitCommandError:
        return False


def _branch_for_commit(repo: git.Repo, commit) -> str:
    """Resolve a display branch for commits on shared history."""
    tip_branches = [head.name for head in repo.heads if head.commit == commit]
    if len(tip_branches) == 1:
        return tip_branches[0]
    if tip_branches:
        for name in tip_branches:
            if name not in ('main', 'master'):
                return name
        return tip_branches[0]
    for preferred in ('main', 'master'):
        if any(head.name == preferred for head in repo.heads):
            if _is_ancestor_of(repo, commit, preferred):
                return preferred
    try:
        name = repo.git.name_rev(
            commit.hexsha,
            '--name-only',
            '--refs=refs/heads/*',
        ).strip()
        if name:
            return name.split('~')[0].split('^')[0]
    except Exception:
        logger.debug('name-rev failed for %s', commit.hexsha, exc_info=True)
    if not repo.head.is_detached:
        return repo.active_branch.name
    return 'HEAD'


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
                    if log_entry.author.email not in settings.GIT['global']['EMAILS']:
                        continue
                    time = git_time_to_datetime(log_entry.authored_datetime)
                    if time < start_date or time > end_date:
                        continue

                    repo_name = repo_path.split('/')[-1]
                    log.append(Entry(
                        id=_commit_id(log_entry),
                        title="",
                        text=format_commit_entry(repo_name, branch, log_entry),
                        start_time=time,
                        group=group,
                    ))
        return log


class Provider(AbstractProvider):
    def get_log_entries(self, repo_path, start_date=None):
        if get_setting('FETCH', default=False):
            _sync_repo(repo_path)
        try:
            repo = git.Repo(repo_path)
        except Exception:
            logger.warning(f"Error opening repo {repo_path}")
            return

        heads = list(repo.heads)
        if not heads:
            return

        seen = set()
        head_names = [head.name for head in heads]

        for head in heads:
            others = [name for name in head_names if name != head.name]
            rev = _exclusive_rev(head.name, others)
            iterator = repo.iter_commits(rev)
            for commit in iterator:
                try:
                    if start_date and git_time_to_datetime(
                        commit.authored_datetime,
                    ) < start_date:
                        break
                except Exception as e:
                    logger.warning(e)
                    continue
                if commit.hexsha in seen:
                    continue
                seen.add(commit.hexsha)
                yield commit, head.name

        iter_kwargs = {}
        if start_date:
            iter_kwargs['since'] = start_date.isoformat()
        for commit in repo.iter_commits('--all', **iter_kwargs):
            if commit.hexsha in seen:
                continue
            try:
                if start_date and git_time_to_datetime(
                    commit.authored_datetime,
                ) < start_date:
                    continue
            except Exception as e:
                logger.warning(e)
                continue
            seen.add(commit.hexsha)
            yield commit, _branch_for_commit(repo, commit)

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
