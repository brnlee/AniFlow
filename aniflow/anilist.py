import string
from typing import List
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
    MIN_TITLE_SIMILARITY_RATIO = 0.9
    ACCEPTABLE_CHARS = set(string.printable)

    def __init__(self) -> None:
        self._token = getenv("ANILIST_TOKEN")

    def should_auth(self) -> bool:
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

        anime = self._match_anime(episode, results)
        if not anime:
            print("Failed to find anime on AniList")
            return
        episode.set_anilist_data(anime)

    def _is_valid_title(self, title) -> bool:
        """Returns True if all characters in the title argument are acceptable"""
        return title and all((c in self.ACCEPTABLE_CHARS for c in title))

    def _get_titles(self, anime) -> List[str]:
        titles = list(anime.get("title").values()) + anime.get("synonyms", [])
        return list(filter(self._is_valid_title, titles))

    def _titles_match(self, sequence_matcher, titles) -> bool:
        for title in titles:
            sequence_matcher.set_seq1(title.lower())
            if sequence_matcher.ratio() >= self.MIN_TITLE_SIMILARITY_RATIO:
                return True
        return False

    def _match_anime(self, episode: Episode, results) -> dict:
        title = episode.fmt_str(include_episode_number=False)
        sequence_matcher = SequenceMatcher(
            isjunk=lambda c: not c.isalnum(),
            a=None,
            b=title.lower(),
        )
        for anime in results:
            titles = self._get_titles(anime)
            if self._titles_match(sequence_matcher, titles):
                anime["titles"] = titles
                return anime
