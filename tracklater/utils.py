import re
from datetime import timedelta, tzinfo
from dateutil import parser as dateparser
import pytz
from typing import Any, Optional


def parse_time(timestr: str):
    return dateparser.parse(timestr).astimezone(pytz.utc).replace(tzinfo=None)


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


def obj_from_dict(d):
    top = type('new', (object,), d)
    seqs = tuple, list, set, frozenset
    callables = {}
    for i, j in d.items():
        if isinstance(j, dict):
            value = obj_from_dict(j)
        elif isinstance(j, seqs):
            value = type(j)(obj_from_dict(sj) if isinstance(sj, dict) else sj for sj in j)
        else:
            value = j
        _match = re.match(r'(.*)\((.*)\)', i)
        if _match:
            _key = _match.groups()[0]
            # Matched parentheses, so we will need to build a function (later)
            # for _key
            _args = []
            if len(_match.groups()) > 1 and _match.groups()[1] != '':
                _args = _match.groups()[1].split(",")
            callables[_key] = callables.get(_key, [])
            # Store a list of possible arguments and their corresponding value
            callables[_key].append((_args, value))
        else:
            setattr(top, i, value)

    for _key, arg_list in callables.items():
        def _func(*args, **kwargs):
            for _data in arg_list:
                if list(args[:len(_data[0])]) == _data[0]:
                    return _data[1]
        setattr(top, _key, _func)

    return top
