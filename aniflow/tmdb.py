import json
from collections import defaultdict
from os import getenv

import github
import tmdbsimple as tmdb
from common import Episode, get_root_dir


class TMDB:

    tmdb_to_anilist = defaultdict(list)
    types = {"TV", "SPECIALS"}
    ANIME_ID_DB_FILE_NAME = "anime-list-full.json"

    def __init__(self) -> None:
        anime_id_db_path = get_root_dir() / self.ANIME_ID_DB_FILE_NAME
        github.update_file_if_necessary(
            repo="Fribb/anime-lists",
            path=self.ANIME_ID_DB_FILE_NAME,
            local_file_path=anime_id_db_path,
        )
        with open(anime_id_db_path, "r") as anime_id_db:
            for entry in json.load(anime_id_db):
                anilist_id = entry.get("anilist_id")
                tmdb_id = entry.get("themoviedb_id")
                type = entry.get("type")
                if anilist_id and tmdb_id and type in self.types:
                    self.tmdb_to_anilist[tmdb_id].append(anilist_id)
        tmdb.API_KEY = getenv("TMDB_API_KEY")

    def search(self, episode: Episode):
        search_results = tmdb.Search().tv(query=episode.anime_title).get("results")
        for result in search_results:
            id = result.get("id")
            seasons = self._get_seasons(id)
            ep_number = int(episode.episode_number)
            for season_num, ep_count, abs_ep_range in seasons:
                start, end = abs_ep_range
                if episode.season and episode.season == season_num:
                    if ep_number <= ep_count:
                        return self._get_anilist_entries(id), start + ep_number - 1
                if ep_number <= end:
                    return self._get_anilist_entries(id), ep_number
        return None, None

    def _get_seasons(self, tmdb_id):
        if not tmdb_id:
            print("Missing ID")
            return []

        entry = tmdb.TV(tmdb_id)

        seasons = []
        cumulative_episode_count = 0

        for season in entry.info().get("seasons"):
            name = season.get("name")
            episode_count = season.get("episode_count")
            if name == "Specials" or not episode_count:
                continue

            ep_range = [
                cumulative_episode_count + 1,
                cumulative_episode_count + episode_count,
            ]
            cumulative_episode_count += episode_count
            seasons.append(
                (
                    season.get("season_number"),
                    episode_count,
                    ep_range,
                )
            )
        return seasons

    def _get_anilist_entries(self, tmdb_id: int):
        return self.tmdb_to_anilist[tmdb_id]
