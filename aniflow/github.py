from datetime import date, datetime
from os import getenv
from pathlib import Path
from urllib.request import urlretrieve

from common import nested_get
from requests import get


def get_last_commit_date(repo: str, path: str):
    response = get(
        f"https://api.github.com/repos/{repo}/commits?path={path}&per_page=1",
        headers={"Authorization": f"Bearer {getenv('GITHUB_TOKEN')}"},
    )
    if response.status_code != 200:
        return

    date = nested_get(response.json()[0], ["commit", "committer", "date"])
    return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


def update_file_if_necessary(repo: str, path: str, local_file_path: Path):
    if get_last_commit_date(repo, path).date() > date.today():
        urlretrieve(
            url=f"https://raw.githubusercontent.com/{repo}/master/{path}",
            filename=local_file_path,
        )
