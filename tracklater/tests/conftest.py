
import pytest
import settings
import example_settings


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Replace settings completely with example_settings
    """
    for module_setting in [item for item in dir(settings) if not item.startswith("__")]:
        if module_setting == 'helper':
            continue
        monkeypatch.setattr(
            'settings.{}'.format(module_setting),
            getattr(example_settings, module_setting)
        )

    # Test settings for Jira
    monkeypatch.setattr('settings.JIRA', {
        'group1': {
            'CREDENTIALS': ('', ''),
            'URL': 'mock://jira.test',
            'PROJECT_KEY': 'TEST',
        }
    })


@pytest.fixture
def obj_from_dict():
    def obj_dic(d):
        top = type('new', (object,), d)
        seqs = tuple, list, set, frozenset
        callables = {}
        for i, j in d.items():
            if isinstance(j, dict):
                value = obj_dic(j)
            elif isinstance(j, seqs):
                value = type(j)(obj_dic(sj) if isinstance(sj, dict) else sj for sj in j)
            else:
                value = j
            _match = re.match('(.*)\((.*)\)', i)  # noqa
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
    return obj_dic
