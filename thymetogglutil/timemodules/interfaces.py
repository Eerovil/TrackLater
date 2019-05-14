from dataclasses import dataclass, field
from typing import List, Union, Dict
from datetime import datetime, timedelta


@dataclass
class Project:
    title: str
    id: str


@dataclass
class Entry:
    start_time: datetime
    end_time: Union[datetime, None] = None
    date_group: str = None
    issue: str = None  # Issue id
    project: str = None  # Project id
    title: str = ""  # Title to show in timeline
    text: List[str] = field(default_factory=list)  # Text to show in timeline hover
    extra_data: Dict = field(default_factory=dict)  # For custom js

    def __post_init__(self) -> None:
        # Calculate date_group immediately
        item_time = self.start_time
        offset = item_time.tzinfo.utcoffset(None)
        _cutoff = self.cutoff_hour + (getattr(offset, 'seconds', 0) / 3600)
        if item_time.hour >= _cutoff:
            self.date_group = item_time.strftime('%Y-%m-%d')
        else:
            self.date_group = (item_time - timedelta(days=1)).strftime('%Y-%m-%d')

    @property
    def duration(self) -> int:
        return int((self.end_time - self.start_time).total_seconds())


class AbstractEntryParser(object):
    """
    Implement some (or all) of these mixins.
    """
    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.entries = []

    def parse(self):
        self.entries = self.get_entries()

    def get_entries(self) -> List[Entry]:
        raise NotImplementedError()


class AddEntryMixin(object):
    def add_entry(self, entry: Entry) -> bool:
        raise NotImplementedError()


class DeleteEntryMixin(object):
    def delete_entry(self, entry_id: str) -> bool:
        raise NotImplementedError()


class UpdateEntryMixin(object):
    def update_entry(self, entry_id: str, entry_data: Entry) -> bool:
        raise NotImplementedError()
