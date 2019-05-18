
from datetime import timedelta, tzinfo
from dateutil import parser as dateparser

from typing import Any, Optional


def parse_time(timestr: str):
    return dateparser.parse(timestr)


def _str(obj: Any) -> Optional[str]:
    return str(obj) if obj else None


class FixedOffset(tzinfo):
    """Fixed offset in minutes west from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(seconds=-offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)
