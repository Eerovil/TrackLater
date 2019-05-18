#!/usr/bin/env python
# -*- encoding: utf-8 -*-


import importlib
from concurrent.futures import ThreadPoolExecutor

import settings
from time import sleep

import logging
logger = logging.getLogger(__name__)


class Parser(object):
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.modules = {}

    def parse(self):
        with ThreadPoolExecutor() as executor:
            running_tasks = []

            for module_name in settings.ENABLED_MODULES:
                module = importlib.import_module(
                    'thymetogglutil.timemodules.{}'.format(module_name)
                )
                parser = module.Parser(self.start_date, self.end_date)
                self.modules[module_name] = parser
                running_tasks.append((module_name, executor.submit(parser.parse)))
                logger.warning("Parsing %s", module_name)
                parser = None
            running = True
            while running:
                running = False
                for i, (module_name, running_task) in enumerate(running_tasks):
                    if running_task and not running_task.running():
                        logger.warning("Task done %s", module_name)
                        running_tasks[i] = (module_name, None)
                    elif running_task:
                        running = True
                sleep(0.1)
