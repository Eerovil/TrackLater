from thymetogglutil import settings
import git
import pytz

from datetime import datetime
from thymetogglutil.utils import FixedOffset


HEL = pytz.timezone('Europe/Helsinki')


class GitMixin(object):
    def __init__(self, repos):
        self.repos = repos
        self.log = []  # List of git.refs.log.RefLogEntry objects

    def parse_git(self):
        start_date = self.start_date.replace(tzinfo=HEL)
        end_date = self.end_date.replace(tzinfo=HEL)
        for repo_path in self.repos:
            repo = git.Repo(repo_path)
            for branch in repo.branches:
                for log_entry in branch.log():
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
                    self.log.append({
                        'repo': repo_path.split('/')[-1],
                        'message': message,
                        'time': time,
                    })

    def get_commits(self, start_time, end_time):
        ret = []
        for log in self.log:
            if start_time <= log['time'] <= end_time:
                ret.append(log)
        return ret

    def print_commits(self, out=True, sort='time'):
        print_str = (
            "\n".join(['{} - {} - {}'.format(
                log['time'], log['repo'], log['message']
            ) for log in sorted(self.log, key=lambda x: x[sort])])
        )
        if out:
            print(print_str)
        return print_str