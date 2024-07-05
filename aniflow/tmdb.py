import json
from collections import defaultdict
from os import getenv

import github
import tmdbsimple as tmdb
from common import Episode, get_root_dir


class TMDB:

    anilist_to_tmdb = {}
    tmdb_to_anilist = defaultdict(list)
    types = {"TV", "SPECIALS"}

    def __init__(self) -> None:
        self._db_path = get_root_dir() / "anime-list-full.json"
        github.update_file_if_necessary(
            repo="Fribb/anime-lists",
            path="anime-list-full.json",
            local_file_path=self._db_path,
        )
        with open(self._db_path, "r") as f:
            for entry in json.load(f):
                anilist_id = entry.get("anilist_id")
                tmdb_id = entry.get("themoviedb_id")
                type = entry.get("type")
                if anilist_id and tmdb_id and type in self.types:
                    self.anilist_to_tmdb[anilist_id] = tmdb_id
                    self.tmdb_to_anilist[tmdb_id].append(anilist_id)
        tmdb.API_KEY = getenv("TMDB_API_KEY")

    def get_tmdb_id(self, anilist_id: str):
        return self.anilist_to_tmdb[anilist_id]

    def get_anilist_entries(self, tmdb_id: int):
        return self.tmdb_to_anilist[tmdb_id]

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
                        return self.get_anilist_entries(id), start + ep_number - 1
                if ep_number <= end:
                    return self.get_anilist_entries(id), ep_number
        return None, None