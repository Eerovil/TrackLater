from user_settings import *  # noqa


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
