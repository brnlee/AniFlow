from datetime import datetime
from os import getenv
from os.path import getmtime
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
    if local_file_path.exists():
        remote_last_updated = get_last_commit_date(repo, path)
        local_last_updated = datetime.fromtimestamp(getmtime(local_file_path))
        if local_last_updated > remote_last_updated:
            return
    urlretrieve(
        url=f"https://raw.githubusercontent.com/{repo}/master/{path}",
        filename=local_file_path,
    )
