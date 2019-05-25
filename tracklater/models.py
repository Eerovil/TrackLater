from sqlalchemy import Column, Integer, String, DateTime, Text, PickleType
from database import db
from datetime import datetime


from typing import Optional


class Project(db.Model):
    __tablename__ = 'projects'
    pk: int = Column(Integer, primary_key=True)
    id: str = Column(String(50))
    pid: str = Column(String(50))
    module: str = Column(String(50))
    group: str = Column(String(50))
    title: str = Column(String(50))

    def to_dict(self):
        return {
            "title": self.title,
            "id": self.pid,
            "group": self.group,
        }


class Issue(db.Model):
    __tablename__ = 'issues'
    pk: int = Column(Integer, primary_key=True)
    id: str = Column(String(50))
    key: str = Column(String(50))
    module: str = Column(String(50))
    group: str = Column(String(50))
    title: str = Column(String(50))
    uuid: Optional[str] = Column(String(50))
    extra_data: dict = Column(PickleType)  # For custom js

    # def __post_init__(self) -> None:
    #     self.uuid = _str(uuid.uuid4())

    def to_dict(self):
        return {
            "title": self.title,
            "key": self.key,
            "group": self.group,
            "extra_data": self.extra_data,
            "uuid": self.uuid
        }


class Entry(db.Model):
    __tablename__ = 'entries'
    pk: int = Column(Integer, primary_key=True)
    id: str = Column(String(50))
    module: str = Column(String(50))
    group: Optional[str] = Column(String(50))
    start_time: datetime = Column(DateTime)
    end_time: Optional[datetime] = Column(DateTime)
    date_group: Optional[str] = Column(String(50))
    issue: Optional[str] = Column(String(50))  # Issue id
    project: Optional[str] = Column(String(50))  # Project id
    title: str = Column(String(255))  # Title to show in timeline
    text: str = Column(Text())  # Text to show in timeline hover
    extra_data: dict = Column(PickleType)  # For custom js

    # def __post_init__(self) -> None:
    #     # Calculate date_group immediately
    #     item_time = self.start_time
    #     offset = None
    #     if item_time.tzinfo:
    #         offset = item_time.tzinfo.utcoffset(None)
    #     _cutoff = getattr(settings, 'CUTOFF_HOUR', 3) + (getattr(offset, 'seconds', 0) / 3600)
    #     if item_time.hour >= _cutoff:
    #         self.date_group = item_time.strftime('%Y-%m-%d')
    #     else:
    #         self.date_group = (item_time - timedelta(days=1)).strftime('%Y-%m-%d')

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
