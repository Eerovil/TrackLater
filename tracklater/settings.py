import logging
logger = logging.getLogger(__name__)


try:
    from tracklater.user_settings import *  # noqa
except ImportError:
    from tracklater.test_settings import *  # noqa
    logger.error("No user settings file! Create one called user_settings.py")


def helper(module, key, group='global', default=None):
    # Try given group first
    if group in globals()[module]:
        _tmp_dict = globals()[module][group]
        if key in _tmp_dict:
            return _tmp_dict[key]
    # Try with 'global' group
    if 'global' in globals()[module]:
        _tmp_dict = globals()[module]['global']
        if key in _tmp_dict:
            return _tmp_dict[key]
    if default:
        return default

    raise KeyError('No setting "{}" for module {} found'.format(key, module))
