import requests
import json
from typing import List, cast, Any

from tracklater import settings
from .interfaces import IssueMixin, AbstractParser, AbstractProvider
from tracklater.models import Issue

import logging

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com/graphql"


class Parser(IssueMixin, AbstractParser):
    def get_issues(self) -> List[Issue]:
        self.github_login()
        issues: List[Issue] = []
        for github_project in self.github_projects:
            for issue in self.provider.get_issues(
                github_project["repo"], github_project["id"]
            ):
                issues.append(
                    Issue(
                        key="#{}".format(issue["ref"]),
                        id=issue["id"],
                        title=issue["subject"],
                        group=github_project["group"],
                    )
                )
        return issues

    def github_login(self) -> None:
        github_settings = cast(Any, settings.GITHUB)
        self.provider = Provider(github_settings["global"]["TOKEN"])
        self.github_projects: List[dict] = []
        id_counter = 0
        for group, data in github_settings.items():
            if "repo" not in data:
                continue
            self.github_projects.append(
                {"id": id_counter, "group": group, "repo": data["repo"]}
            )
            id_counter += 1


class Provider(AbstractProvider):
    def __init__(self, token):
        self.token = token
        self.headers = {"Authorization": "Bearer {}".format(self.token)}

    def get_issues(self, repo, project_id):
        query = """
        query {
            repository(owner:"#{repo_owner}", name:"#{repo_name}") {
                issues(first:100#{cursor}) {
                    totalCount
                    edges {
                        node {
                            title
                            number
                            id
                        }
                    }
                    pageInfo {
                        endCursor
                        hasNextPage
                    }
                }
            }
        }
        """
        issues: List[dict] = []
        cursor = ""
        while True:
            logger.error(
                json.dumps(
                    {
                        "query": query.replace("#{repo_owner}", repo[0])
                        .replace("#{repo_name}", repo[1])
                        .replace("#{cursor}", cursor)
                    }
                )
            )
            response = requests.post(
                API_URL,
                data=json.dumps(
                    {
                        "query": query.replace("#{repo_owner}", repo[0])
                        .replace("#{repo_name}", repo[1])
                        .replace("#{cursor}", cursor)
                    }
                ),
                headers=self.headers,
            )
            logger.error(response.json())
            data = response.json()["data"]
            issues += [
                {
                    "ref": edge["node"]["number"],
                    "subject": edge["node"]["title"],
                    "id": edge["node"]["id"],
                }
                for edge in data["repository"]["issues"]["edges"]
            ]
            # Paginate
            if data["repository"]["issues"]["pageInfo"]["hasNextPage"]:
                cursor = ' after:"{}"'.format(
                    data["repository"]["issues"]["pageInfo"]["endCursor"]
                )
            else:
                break
        return issues
