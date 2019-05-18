from dataclasses import dataclass, field
from typing import List, Union, Dict
from datetime import datetime, timedelta
from thymetogglutil import settings

from thymetogglutil.utils import _str

import uuid


@dataclass
class Project:
    title: str
    id: str
    group: str

    def __post_init__(self) -> None:
        # ensure ids are str
        self.id = _str(self.id)

    def to_dict(self):
        return {
            "title": self.title,
            "id": self.id,
            "group": self.group,
        }


@dataclass
class Issue:
    key: str
    title: str
    group: str
    uuid: str = None
    extra_data: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.uuid = _str(uuid.uuid4())

    def to_dict(self):
        return {
            "title": self.title,
            "key": self.key,
            "group": self.group,
            "extra_data": self.extra_data,
            "uuid": self.uuid
        }


@dataclass
class Entry:
    start_time: datetime
    id: str = None
    end_time: Union[datetime, None] = None
    date_group: str = None
    issue: str = None  # Issue id
    group: str = None
    project: str = None  # Project id
    title: str = ""  # Title to show in timeline
    text: List[str] = field(default_factory=list)  # Text to show in timeline hover
    extra_data: Dict = field(default_factory=dict)  # For custom js

    def __post_init__(self) -> None:
        # ensure ids are str
        self.id = _str(self.id)
        self.project = _str(self.project)
        self.issue = _str(self.issue)

        # Calculate date_group immediately
        item_time = self.start_time
        offset = item_time.tzinfo.utcoffset(None)
        _cutoff = getattr(settings, 'CUTOFF_HOUR', 3) + (getattr(offset, 'seconds', 0) / 3600)
        if item_time.hour >= _cutoff:
            self.date_group = item_time.strftime('%Y-%m-%d')
        else:
            self.date_group = (item_time - timedelta(days=1)).strftime('%Y-%m-%d')

    @property
    def duration(self) -> int:
        if not self.end_time:
            return 0
        return int((self.end_time - self.start_time).total_seconds())

    def to_dict(self):
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "id": self.id,
            "date_group": self.date_group,
            "issue": self.issue,
            "project": self.project,
            "title": self.title,
            "text": self.text,
            "extra_data": self.extra_data,
            "duration": self.duration
        }


class EntryMixin(object):
    def parse(self):
        self.entries = self.get_entries()
        super(EntryMixin, self).parse()

    @property
    def capabilities(self):
        _ret = super(EntryMixin, self).capabilities
        return _ret + ['entries']

    def get_entries(self) -> List[Entry]:
        raise NotImplementedError()


class ProjectMixin(object):
    def parse(self):
        self.projects = self.get_projects()
        super(ProjectMixin, self).parse()

    @property
    def capabilities(self):
        _ret = super(ProjectMixin, self).capabilities
        return _ret + ['projects']

    def get_projects(self) -> List[Project]:
        raise NotImplementedError()


class IssueMixin(object):
    def parse(self):
        self.issues = self.get_issues()
        super(IssueMixin, self).parse()

    @property
    def capabilities(self):
        _ret = super(IssueMixin, self).capabilities
        return _ret + ['issues']

    def get_issues(self) -> List[Issue]:
        raise NotImplementedError()

    def find_issue(self, uuid):
        for issue in self.issues:
            if issue.uuid == uuid:
                return issue
        return None


class AddEntryMixin(object):
    def create_entry(self, new_entry: Entry, issue: Issue) -> str:
        raise NotImplementedError()

    @property
    def capabilities(self):
        _ret = super(AddEntryMixin, self).capabilities
        return _ret + ['addentry']


class DeleteEntryMixin(object):
    def delete_entry(self, entry_id: str) -> bool:
        raise NotImplementedError()

    @property
    def capabilities(self):
        _ret = super(DeleteEntryMixin, self).capabilities
        return _ret + ['deleteentry']


class UpdateEntryMixin(object):
    def update_entry(self, entry_id: str, new_entry: Entry, issue: Issue) -> bool:
        raise NotImplementedError()

    @property
    def capabilities(self):
        _ret = super(UpdateEntryMixin, self).capabilities
        return _ret + ['updateentry']


class AbstractParser(object):
    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.entries: List[Entry] = []
        self.projects: List[Project] = []
        self.issues: List[Issue] = []

    @property
    def capabilities(self):
        return []

    def parse(self):
        pass
