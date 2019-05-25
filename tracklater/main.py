#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib
import settings
from concurrent.futures import ThreadPoolExecutor, as_completed

from timemodules.interfaces import AbstractParser
from typing import Dict
from types import ModuleType

from database import db

import traceback
import logging
logger = logging.getLogger(__name__)


def reraise_with_stack(func):
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            traceback_str = traceback.format_exc()
            raise Exception("Error occurred. Original traceback "
                            "is\n%s\n" % traceback_str)
    return wrapped


class Parser(object):
    def __init__(self, start_date, end_date) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.modules: Dict[str, AbstractParser] = {}

    def parse(self) -> None:
        with ThreadPoolExecutor() as executor:
            running_tasks = {}

            for module_name in settings.ENABLED_MODULES:
                module: ModuleType = importlib.import_module(
                    'timemodules.{}'.format(module_name)
                )
                if getattr(module, 'Parser', None) is None:
                    logger.warning('Module %s has no Parser class', module_name)
                parser = module.Parser(self.start_date, self.end_date)  # type: ignore
                self.modules[module_name] = parser
                running_tasks[module_name] = executor.submit(reraise_with_stack(parser.parse))
                logger.warning("Parsing %s", module_name)
                parser = None

            for task in as_completed([value for key, value in running_tasks.items()]):
                for key, value in running_tasks.items():
                    if value is task:
                        module_name = key
                        break
                if task.exception():
                    logger.exception("Exception in %s: %s", module_name, task.exception())
                for entry in self.modules[module_name].entries:
                    entry.module = module_name
                    db.session.add(entry)
                db.session.commit()

                logger.warning("Task done %s", module_name)
