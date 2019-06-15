#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib
from typing import Dict
from types import ModuleType

from tracklater import settings
from tracklater.timemodules.interfaces import AbstractParser
from tracklater.models import ApiCall, Entry, Issue, Project
from tracklater.database import db

import logging
logger = logging.getLogger(__name__)


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
    Project.query.delete()
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
                'tracklater.timemodules.{}'.format(module_name)
            )
            if getattr(module, 'Parser', None) is None:
                logger.warning('Module %s has no Parser class', module_name)
            parser = module.Parser(self.start_date, self.end_date)  # type: ignore
            self.modules[module_name] = parser

    def parse(self) -> None:
        for module_name, parser in self.modules.items():
            set_parser_caching_data(parser, module_name)
            parser.parse()
            logger.warning("Parsing %s", module_name)
            store_parser_to_database(self.modules[module_name], module_name,
                                     start_date=self.start_date, end_date=self.end_date)
            logger.warning("Task done %s", module_name)
