import string
import webbrowser
from difflib import SequenceMatcher
from os import getenv
from typing import List

import requests
import tmdb
from common import AniListEntry, Episode, nested_get
from dotenv import find_dotenv, set_key, unset_key


class AniList:

    GRAPHQL_URL = "https://graphql.anilist.co"
    KEY_ANILIST_CLIENT_ID = "ANILIST_CLIENT_ID"
    KEY_ANILIST_TOKEN = "ANILIST_TOKEN"
    MIN_TITLE_SIMILARITY_RATIO = 0.9
    ACCEPTABLE_CHARS = set(string.printable)

    def __init__(self) -> None:
        self._token = getenv("ANILIST_TOKEN")
        self.tmdb = tmdb.TMDB()

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
            "mediaId": episode.anilist_entry.id,
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
                        romaji
                        english
                    }
                    synonyms
                    episodes
                    siteUrl
                    relations {
                        edges {
                            relationType
                        }
                        nodes {
                            id
                        }
                    }
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
            print("Failed to confidently find anime on AniList")
            entry_ids, absolute_episode_number = self.tmdb.search(episode)
            if not entry_ids:
                print("Could not find anime on TMDB")
                return
            graph = {}
            head_node_id = self._build_graph(entry_ids, graph)
            entry_id, relative_episode_number = self._find_entry_based_on_abs_ep_number(
                absolute_episode_number, graph, head_node_id
            )
            if absolute_episode_number != relative_episode_number:
                episode.absolute_episode_number = str(absolute_episode_number)
                episode.episode_number = str(relative_episode_number)
            episode.anilist_entry = graph.get(entry_id)
            if episode.anilist_entry:
                print("Found AniList entry after falling back to TMDB")
            else:
                print("Could not find any AniList entry falling back to TMDB")
            return

        episode.anilist_entry = AniListEntry(anime)

    def _is_valid_title(self, title) -> bool:
        """Returns True if all characters in the title argument are acceptable"""
        return title and all((c in self.ACCEPTABLE_CHARS for c in title))

    def _get_titles(self, anime) -> List[str]:
        titles = list(anime.get("title").values()) + anime.get("synonyms", [])
        return list(filter(self._is_valid_title, titles))

    def _titles_match(self, sequence_matcher, titles) -> bool:
        for title in titles:
            sequence_matcher.set_seq1(self._prepare_string_for_comparison(title))
            if sequence_matcher.ratio() >= self.MIN_TITLE_SIMILARITY_RATIO:
                return True
        return False

    def _prepare_string_for_comparison(self, string):
        return "".join(filter(str.isalnum, string.lower()))

    def _match_anime(self, episode: Episode, results) -> dict:
        title = episode.fmt_str(include_episode_number=False, delimiter=" ")
        sequence_matcher = SequenceMatcher(
            isjunk=None,
            a=None,
            b=self._prepare_string_for_comparison(title),
        )
        for anime in results:
            titles = self._get_titles(anime)
            if self._titles_match(sequence_matcher, titles):
                episode_count = anime.get("episodes")
                if (
                    episode.episode_number
                    and episode_count
                    and int(episode.episode_number) > episode_count
                ):
                    continue
                anime["titles"] = titles
                return anime

    def _build_graph(self, ids: List[int], graph):
        query = """
        query ($id: Int) {
            Media(type: ANIME, id: $id) {
                id
                title {
                    romaji
                    english
                }
                synonyms
                episodes
                siteUrl
                relations {
                    edges {
                        relationType
                    }
                    nodes {
                        id
                    }
                }
            }
        }
        """
        head_node_id = None
        for id in ids:
            if id in graph:
                continue

            variables = {"id": id}
            response = requests.post(
                self.GRAPHQL_URL, json={"query": query, "variables": variables}
            )
            if response.status_code != 200:
                print("ERROR")
                continue

            anime = nested_get(response.json(), ["data", "Media"])
            anime["titles"] = self._get_titles(anime)
            edges = nested_get(anime, ["relations", "edges"])
            nodes = nested_get(anime, ["relations", "nodes"])
            if not edges and not nodes:
                continue

            curr_node = AniListEntry(anime)
            graph[id] = curr_node

            for edge, node in zip(edges, nodes):
                relation_type = edge.get("relationType")
                if relation_type not in {"PREQUEL", "SEQUEL"}:
                    continue

                related_node_id = node.get("id")
                if related_node_id not in ids:
                    continue

                head_node_id = head_node_id or self._build_graph(ids, graph)
                related_node = graph[related_node_id]
                match relation_type:
                    case "PREQUEL":
                        curr_node.prequel = related_node_id
                        related_node.sequel = id
                    case "SEQUEL":
                        curr_node.sequel = related_node.id
                        related_node.prequel = id

            if not curr_node.prequel:
                head_node_id = id
        return head_node_id

    def _find_entry_based_on_abs_ep_number(
        self, absolute_episode_number, graph: dict[int, AniListEntry], head_id
    ):
        id = head_id
        cumulative_episode_count = 0
        while id:
            node = graph[id]
            start = cumulative_episode_count + 1
            end = start + node.episode_count - 1
            if start <= absolute_episode_number <= end:
                relative_episode_number = (
                    absolute_episode_number - cumulative_episode_count
                )
                return id, relative_episode_number
            id = node.sequel
            cumulative_episode_count += node.episode_count
