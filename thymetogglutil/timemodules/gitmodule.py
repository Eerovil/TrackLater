from thymetogglutil import settings
import git
import pytz

from datetime import datetime
from thymetogglutil.utils import FixedOffset
from thymetogglutil.timemodules.interfaces import AbstractEntryParser, Entry


HEL = pytz.timezone('Europe/Helsinki')


class Parser(AbstractEntryParser):
    def get_entries(self):
        start_date = self.start_date.replace(tzinfo=HEL)
        end_date = self.end_date.replace(tzinfo=HEL)
        log = []
        for repo_path in settings.GIT_REPOS:
            repo = git.Repo(repo_path)
            for branch in repo.branches:
                try:
                    entries = branch.log()
                except Exception:
                    continue
                for log_entry in entries:
                    if log_entry.actor.email not in settings.GIT_EMAILS:
                        continue
                    if not log_entry.message.startswith('commit'):
                        continue
                    message = ''.join(log_entry.message.split(':')[1:])
                    time = datetime.fromtimestamp(
                        log_entry.time[0], tz=FixedOffset(log_entry.time[1], 'Helsinki')
                    )
                    if time < start_date or time > end_date:
                        continue

                    log.append(Entry(
                        text=[
                            "{} - {}".format(repo_path.split('/')[-1], message)
                        ],
                        start_time=time,
                    ))
        return log
