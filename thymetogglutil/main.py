#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib

from thymetogglutil import settings

import logging
logger = logging.getLogger(__name__)


class Parser(object):
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.modules = {}

    def parse(self):
        for module_name in settings.ENABLED_MODULES:
            module = importlib.import_module('thymetogglutil.timemodules.{}'.format(module_name))
            parser = module.Parser(self.start_date, self.end_date)
            parser.parse()
            self.modules[module_name] = parser
            parser = None
