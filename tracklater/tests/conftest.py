import os
import tempfile

# Point every create_app() at a throwaway database BEFORE any test module is
# imported (test_app/test_ai_local call create_app() at import time). Without
# this, the engine binds to the real tracklater/database.db and tests mutate it.
os.environ.setdefault(
    'TRACKLATER_DB_URI',
    'sqlite:///{}'.format(os.path.join(tempfile.gettempdir(), 'tracklater_pytest.db')),
)

import pytest
from tracklater import settings
from tracklater import test_settings


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Replace settings completely with test_settings
    """
    for module_setting in [item for item in dir(settings) if not item.startswith("__")]:
        if module_setting == 'helper':
            continue
        monkeypatch.setattr(
            'tracklater.settings.{}'.format(module_setting),
            getattr(test_settings, module_setting, {})
        )


@pytest.fixture()
def db():
    from tracklater.database import db
    return db
