from thymetogglutil import settings
import git

from datetime import datetime
from thymetogglutil.utils import FixedOffset
from thymetogglutil.timemodules.interfaces import AbstractEntryParser, Entry


class Parser(AbstractEntryParser):
    def get_entries(self):
        log = []
        for repo_path in settings.GIT_REPOS:
            repo = git.Repo(repo_path)
            for branch in repo.branches:
                for log_entry in branch.log():
                    if log_entry.actor.email not in settings.GIT_EMAILS:
                        continue
                    if not log_entry.message.startswith('commit'):
                        continue
                    message = ''.join(log_entry.message.split(':')[1:])
                    log.append(Entry(
                        text=[
                            "{} - {}".format(repo_path.split('/')[-1], message)
                        ],
                        start_time=datetime.fromtimestamp(
                            log_entry.time[0], tz=FixedOffset(log_entry.time[1], 'Helsinki')
                        ),
                    ))
        return log
