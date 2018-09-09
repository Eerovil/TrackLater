
from datetime import timedelta, tzinfo
from dateutil import parser as dateparser


def parse_time(timestr):
    return dateparser.parse(timestr)


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


class DateGroupMixin(object):
    """
    Includes a 'date_group' key that allows grouping entries by date.
    """
    def __init__(self):
        self.cutoff_hour = 3

    def _parse_list(self, l, key='start_time'):
        for item in l:
            item_time = item[key]
            offset = item_time.tzinfo.utcoffset(None)
            _cutoff = self.cutoff_hour + (getattr(offset, 'seconds', 0) / 3600)
            if item_time.hour >= _cutoff:
                item['date_group'] = item_time.strftime('%Y-%m-%d')
            else:
                item['date_group'] = (item_time - timedelta(days=1)).strftime('%Y-%m-%d')

    def parse_group(self):
        self._parse_list(self.sessions)
        self._parse_list(self.time_entries)
        self._parse_list(self.log, key='time')
