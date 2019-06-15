from sqlalchemy import Column, Integer, String, DateTime, Text, PickleType
from datetime import datetime, timedelta
from typing import Optional

from tracklater.database import db
from tracklater import settings

import logging
logger = logging.getLogger(__name__)


class ApiCall(db.Model):
    pk: int = Column(Integer, primary_key=True)
    module: str = Column(String(50), nullable=False)
    created = Column(DateTime, default=datetime.utcnow)
    start_date: datetime = Column(DateTime)
    end_date: Optional[datetime] = Column(DateTime)


class Project(db.Model):
    __tablename__ = 'projects'
    module: str = Column(String(50), primary_key=True)
    pid: str = Column(String(50), primary_key=True, nullable=True)
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
    module: str = Column(String(50), primary_key=True)
    id: str = Column(String(50), primary_key=True, nullable=True)
    key: str = Column(String(50), primary_key=True, nullable=True)
    group: str = Column(String(50))
    title: str = Column(String(50))
    uuid: Optional[str] = Column(String(50))
    extra_data: dict = Column(PickleType)  # For custom js

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "key": self.key,
            "group": self.group,
            "extra_data": self.extra_data,
            "uuid": self.uuid
        }


class Entry(db.Model):
    __tablename__ = 'entries'
    module: str = Column(String(50), primary_key=True)
    id: str = Column(String(50), primary_key=True, nullable=True, unique=True)
    start_time: datetime = Column(DateTime, primary_key=True)
    group: Optional[str] = Column(String(50))
    end_time: Optional[datetime] = Column(DateTime)
    date_group: Optional[str] = Column(String(50))
    issue: Optional[str] = Column(String(50))  # Issue id
    project: Optional[str] = Column(String(50))  # Project id
    title: str = Column(String(255), default="")  # Title to show in timeline
    text: str = Column(Text())  # Text to show in timeline hover
    extra_data: dict = Column(PickleType)  # For custom js

    def __init__(self, **kwargs):
        super(Entry, self).__init__(**kwargs)
        # Calculate date_group immediately
        item_time = self.start_time
        _cutoff = getattr(settings, 'CUTOFF_HOUR', 3)
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
