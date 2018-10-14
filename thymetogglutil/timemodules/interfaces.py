from dataclasses import dataclass
from typing import List
from datetime import datetime


@dataclass
class Entry:
    start_time: datetime
    end_time: datetime
    extra_data: dict

    def duration(self) -> int:
        return int((self.end_time - self.start_time).total_seconds())


class AbstractParser(object):
    """
    Implement or override some (or all) of these functions.
    """
    def __init__(self, start_time: datetime, end_time: datetime) -> None:
        self.start_time = start_time
        self.end_time = end_time

    def get_entries(self) -> List[Entry]:
        pass

    def add_entry(self, entry: Entry) -> bool:
        pass

    def delete_entry(self, entry_id: str) -> bool:
        pass

    def update_entry(self, entry_id: str, entry_data: Entry) -> bool:
        pass
