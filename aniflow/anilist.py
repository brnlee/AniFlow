import webbrowser
from difflib import SequenceMatcher
from os import getenv

import requests
from common import Episode, nested_get
from dotenv import find_dotenv, set_key, unset_key


class AniList:

    GRAPHQL_URL = "https://graphql.anilist.co"
    KEY_ANILIST_CLIENT_ID = "ANILIST_CLIENT_ID"
    KEY_ANILIST_TOKEN = "ANILIST_TOKEN"

    MIN_TITLE_SIMILARITY_RATIO = 0.95

    def __init__(self) -> None:
        self._token = getenv("ANILIST_TOKEN")

    def should_auth(self):
        return not self._token

    def open_authorization_page(self):
        client_id = getenv(self.KEY_ANILIST_CLIENT_ID)
        url = f"https://anilist.co/api/v2/oauth/authorize?client_id={client_id}&response_type=token"
        webbrowser.open(url)

    def set_access_token(self, token):
        self._token = token
        set_key(find_dotenv(), self.KEY_ANILIST_TOKEN, self._token)

    def clear_access_token(self):
        self._token = None
        unset_key(find_dotenv(), self.KEY_ANILIST_TOKEN)

    def clean_string(self, string):
        """Removes all non-alphanumeric characters for string comparison"""
        return "".join(char for char in string if char.isalnum()).lower()

    def _titles_match(self, sequence_matcher, titles, season):
        for title in titles:
            if not title:
                continue
            clean_title = self.clean_string(title)

            sequence_matcher.set_seq1(clean_title)
            if sequence_matcher.ratio() < self.MIN_TITLE_SIMILARITY_RATIO:
                continue

            if (
                not season
                or clean_title.endswith(season)
                or self.clean_string(f"Season {season}") in clean_title
                or self.clean_string(f"S{season}") in clean_title
            ):
                return True
        return False

    def match_anime(self, episode: Episode, results):
        sequence_matcher = SequenceMatcher(
            None, a=None, b=self.clean_string(episode.anime_title)
        )
        for anime in results:
            titles = [title for title in anime.get("title").values() if title]
            titles.extend(sorted(anime.get("synonyms", [])))
            if self._titles_match(sequence_matcher, titles, episode.season):
                anime["titles"] = titles
                return anime

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
        anime: Page(perPage: 2) {
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
            print("Failed to find anime on AniList")
            return
        episode.set_anilist_data(anime)
