import webbrowser
from os import getenv

import requests
from dotenv import set_key, unset_key

from common import AniListData, Episode, nested_get


class AniList:

    AUTH_URL = (
        "https://anilist.co/api/v2/oauth/authorize?client_id={}&response_type=token"
    )
    GRAPHQL_URL = "https://graphql.anilist.co"
    KEY_ANILIST_CLIENT_ID = "ANILIST_CLIENT_ID"
    KEY_ANILIST_TOKEN = "ANILIST_TOKEN"

    def __init__(self) -> None:
        self._token = getenv("ANILIST_TOKEN")

    def clean_string(self, string):
        """Removes all non-alphanumeric characters for string comparison"""
        return "".join(char for char in string if char.isalnum()).lower()

    def do_titles_match(self, episode: Episode, title_to_compare: str):
        if not title_to_compare:
            return False

        clean_title = self.clean_string(episode.anime_title)
        clean_title_to_compare = self.clean_string(title_to_compare)
        season = episode.season

        if not season:
            return clean_title == clean_title_to_compare

        if clean_title not in clean_title_to_compare:
            return False
        return (
            clean_title_to_compare.endswith(season)
            or self.clean_string(f"Season {season}") in clean_title_to_compare
            or self.clean_string(f"S{season}") in clean_title_to_compare
        )

    def match_anime(self, episode: Episode, results):
        for anime in results:
            anime["titles"] = [title for title in anime.get("title").values() if title]
            if anime.get("synonyms"):
                anime["titles"].extend(sorted(anime.get("synonyms")))
            if any(
                map(lambda title: self.do_titles_match(episode, title), anime["titles"])
            ) and int(episode.episode_number) <= anime.get("episodes"):
                return anime

    def should_auth(self):
        return not self._token

    def get_access_token(self):
        client_id = getenv(self.KEY_ANILIST_CLIENT_ID)
        webbrowser.open(self.AUTH_URL.format(client_id))

    def set_access_token(self, token):
        self._token = token
        set_key(".env", self.KEY_ANILIST_TOKEN, self._token)

    def clear_access_token(self):
        self._token = None
        unset_key(".env", self.KEY_ANILIST_TOKEN)

    def update_entry(self, episode: Episode) -> bool:
        """Returns True if there is an Auth error"""

        query = """
        mutation ($mediaId: Int, $status: MediaListStatus, $progress: Int) {
            SaveMediaListEntry (mediaId: $mediaId, status: $status, progress: $progress) {
                score
            }
        }
        """
        status = "COMPLETED" if episode.is_last_episode() else "CURRENT"
        variables = {
            "mediaId": episode.anilist_data.id,
            "status": status,
            "progress": int(episode.episode_number),
        }
        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        response = requests.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=headers,
        )
        match response.status_code:
            case 200:
                pass
            case 400:
                invalid_token = any(
                    error.get("message") == "Invalid token"
                    for error in response.json().get("errors")
                )
                if invalid_token:
                    self.clear_access_token()
                return invalid_token
            case _:
                return False

        return False

    def find_and_set_data(self, episode: Episode):
        query = """
        query ($search: String) {
        anime: Page(perPage: 10) {
            results: media(type: ANIME, search: $search) {
            id
            title {
                english
                romaji
            }
            synonyms
            episodes
            siteUrl
            }
        }
        }
        """
        search_title = episode.fmt_str(delimiter=" ", include_episode_number=False)
        variables = {"search": search_title}

        response = requests.post(
            self.GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        if response.status_code != 200:
            return

        results = nested_get(response.json(), ["data", "anime", "results"])

        anime = self.match_anime(episode, results)
        if not anime:
            return

        anilist_data = AniListData()
        anilist_data.id = anime.get("id")
        anilist_data.titles = anime.get("titles")
        anilist_data.episode_count = anime.get("episodes")
        anilist_data.entry_url = anime.get("siteUrl")
        episode.anilist_data = anilist_data
