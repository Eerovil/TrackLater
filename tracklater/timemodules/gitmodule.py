from typing import List
import settings
import git
import pytz

from datetime import datetime
from utils import FixedOffset
from timemodules.interfaces import EntryMixin, AbstractParser, Entry


def get_setting(key, default=None, group='global'):
    return settings.helper('GIT', key, group=group, default=default)


HEL = pytz.timezone('Europe/Helsinki')


def timestamp_to_datetime(timestamp: List):
    return datetime.fromtimestamp(
        timestamp[0], tz=FixedOffset(timestamp[1], 'Helsinki')
    )


class Parser(EntryMixin, AbstractParser):
    def get_entries(self) -> List[Entry]:
        start_date = self.start_date.replace(tzinfo=HEL)
        end_date = self.end_date.replace(tzinfo=HEL)
        log = []
        for group, data in settings.GIT.items():
            for repo_path in data.get('REPOS', []):
                repo = git.Repo(repo_path)
                for branch in repo.branches:
                    try:
                        entries = branch.log()
                    except Exception:
                        continue
                    for log_entry in entries:
                        if log_entry.actor.email not in settings.GIT['global']['EMAILS']:
                            continue
                        if not log_entry.message.startswith('commit'):
                            continue
                        message = ''.join(log_entry.message.split(':')[1:])
                        time = timestamp_to_datetime(log_entry.time)
                        if time < start_date or time > end_date:
                            continue

                        log.append(Entry(
                            text=[
                                "{} - {}".format(repo_path.split('/')[-1], message)
                            ],
                            start_time=time,
                        ))
        return log
