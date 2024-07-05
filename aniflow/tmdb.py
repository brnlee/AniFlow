import json
from collections import defaultdict
from os import getenv

import tmdbsimple as tmdb
from common import Episode, get_root_dir


class TMDB:

    anilist_to_tmdb = {}
    tmdb_to_anilist = defaultdict(list)

    def __init__(self) -> None:
        with open(get_root_dir() / "anime-list-full.json", "r") as f:
            for entry in json.load(f):
                anilist_id = entry.get("anilist_id")
                tmdb_id = entry.get("themoviedb_id")
                if anilist_id and tmdb_id:
                    self.anilist_to_tmdb[anilist_id] = tmdb_id
                    self.tmdb_to_anilist[tmdb_id].append(anilist_id)
        tmdb.API_KEY = getenv("TMDB_API_KEY")

    def get_tmdb_id(self, anilist_id: str):
        return self.anilist_to_tmdb[anilist_id]

    def get_anilist_entries(self, tmdb_id: int):
        return self.tmdb_to_anilist[tmdb_id]

    def _get_seasons(self, anilist_id=None, tmdb_id=None):
        if not anilist_id and not tmdb_id:
            print("Missing IDs")
            return None
        elif not tmdb_id:
            tmdb_id = self.get_tmdb_id(anilist_id)
        entry = tmdb.TV(tmdb_id)
        seasons = []
        cumulative_episode_count = 0
        entry.info()
        for season in entry.seasons:
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
            seasons = self._get_seasons(tmdb_id=id)
            ep_number = int(episode.episode_number)
            for season_num, ep_count, abs_ep_range in seasons:
                start, end = abs_ep_range
                if episode.season and episode.season == season_num:
                    if ep_number <= ep_count:
                        return self.get_anilist_entries(id), start + ep_number - 1
                if ep_number <= end:
                    return self.get_anilist_entries(id), ep_number
