#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib
import settings
from concurrent.futures import ThreadPoolExecutor, as_completed

from timemodules.interfaces import AbstractParser
from typing import Dict
from types import ModuleType

from models import ApiCall, Entry, Issue, Project

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


def store_parser_to_database(parser, module_name, start_date, end_date):
    Entry.query.filter(
        Entry.module == module_name, Entry.start_time >= start_date,
        Entry.start_time <= end_date
    ).delete()
    for entry in parser.entries:
        entry.module = module_name
        db.session.merge(entry)
    for issue in parser.issues:
        issue.module = module_name
        db.session.merge(issue)
    for project in parser.projects:
        project.module = module_name
        db.session.merge(project)
    db.session.add(ApiCall(
        start_date=start_date,
        end_date=end_date,
        module=module_name
    ))
    db.session.commit()


def set_parser_caching_data(parser, module_name):
    apicall = ApiCall.query.filter_by(module=module_name).order_by('created').first()
    if apicall:
        parser.set_database_values(
            start_date=apicall.start_date,
            end_date=apicall.end_date,
            issue_count=Issue.query.filter_by(module=module_name).count(),
            entry_count=Entry.query.filter_by(module=module_name).count(),
            project_count=Project.query.filter_by(module=module_name).count(),
        )


class Parser(object):
    def __init__(self, start_date, end_date, modules=None) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.modules: Dict[str, AbstractParser] = {}

        for module_name in settings.ENABLED_MODULES:
            if modules and module_name not in modules:
                continue
            module: ModuleType = importlib.import_module(
                'timemodules.{}'.format(module_name)
            )
            if getattr(module, 'Parser', None) is None:
                logger.warning('Module %s has no Parser class', module_name)
            parser = module.Parser(self.start_date, self.end_date)  # type: ignore
            self.modules[module_name] = parser

    def parse(self) -> None:
        with ThreadPoolExecutor() as executor:
            running_tasks = {}

            for module_name, parser in self.modules.items():
                set_parser_caching_data(parser, module_name)
                running_tasks[module_name] = executor.submit(reraise_with_stack(parser.parse))
                logger.warning("Parsing %s", module_name)

            for task in as_completed([value for key, value in running_tasks.items()]):
                for key, value in running_tasks.items():
                    if value is task:
                        module_name = key
                        break
                if task.exception():
                    logger.exception("Exception in %s: %s", module_name, task.exception())

                store_parser_to_database(self.modules[module_name], module_name,
                                         start_date=self.start_date, end_date=self.end_date)

                logger.warning("Task done %s", module_name)
