
import pytest
import settings
import test_settings


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Replace settings completely with test_settings
    """
    for module_setting in [item for item in dir(settings) if not item.startswith("__")]:
        if module_setting == 'helper':
            continue
        monkeypatch.setattr(
            'settings.{}'.format(module_setting),
            getattr(test_settings, module_setting, {})
        )


@pytest.fixture()
def db():
    from database import db
    return db
