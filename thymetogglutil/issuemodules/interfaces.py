from dataclasses import dataclass
from typing import List


class AbstractIssueParser(object):
    def __init__(self) -> None:
        self.issues = []

    def parse(self):
        self.issues = self.get_issues()

    def get_issues(self) -> List[Issue]:
        raise NotImplementedError()
