from dataclasses import dataclass
from typing import List, Union
from datetime import datetime


@dataclass
class Entry:
    start_time: datetime
    extra_data: object
    end_time: Union[datetime, None] = None

    def duration(self) -> int:
        return int((self.end_time - self.start_time).total_seconds())


class AbstractParser(object):
    """
    Implement some (or all) of these mixins.
    """
    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        self.start_date = start_date
        self.end_date = end_date

    def get_entries(self) -> List[Entry]:
        raise NotImplementedError()


class AddMixin(object):
    def add_entry(self, entry: Entry) -> bool:
        raise NotImplementedError()


class DeleteMixin(object):
    def delete_entry(self, entry_id: str) -> bool:
        raise NotImplementedError()


class UpdateMixin(object):
    def update_entry(self, entry_id: str, entry_data: Entry) -> bool:
        raise NotImplementedError()
