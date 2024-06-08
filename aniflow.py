import json
import os
import urllib
import webbrowser
from functools import reduce
from pathlib import Path

import anitopy
import inquirer
import qbittorrentapi

PROGRESS_COMPLETE = 1

REDDIT_SEARCH = "https://www.reddit.com/search?"

REDDIT_SEARCH_JSON = "https://www.reddit.com/search.json?"

RELOAD = "[Reload Episodes]"


class Episode:
    def __init__(self, index, name, path, torrent_hash, can_delete_torrent):
        self.index = index
        self.name = name
        self.path = path
        self.torrent_hash = torrent_hash
        self.can_delete_torrent = can_delete_torrent

        anitopy_options = {"parse_file_extension": False, "parse_release_group": False}
        details = anitopy.parse(self.get_name(), options=anitopy_options)
        self.anime_title = details.get("anime_title")
        episode_number = details.get("episode_number")
        self.episode_number = (
            float(episode_number.lstrip("0")) if episode_number else None
        )
        self.season = details.get("anime_season")

    def get_name(self):
        return self.name.split("/")[-1]

    def get_reddit_searchable_query(self):
        # ["Kaguya-sama wa Kokurasetai", "First Kiss wa Owaranai", "Episode 1"]
        tokens = self.__str__().split(" - ")
        #  "Kaguya-sama wa Kokurasetai" AND "First Kiss wa Owaranai" AND "Episode 1"
        query_with_season = " AND ".join([f'"{token}"' for token in tokens])
        # if len(tokens) == 3 and self.episode_number:
        #     query_without_season = f'"{self.anime_title}" AND "Episode {self.episode_number}"'
        #     return f'({query_with_season} OR {query_without_season})'
        return query_with_season

    def __str__(self):
        season = " "
        if self.season:
            try:
                season = f" - Season {int(self.season)} "
            except ValueError:
                pass

        if self.episode_number:
            return f"{self.anime_title}{season}- Episode {self.episode_number:g}"
        else:
            return self.anime_title


class AniFlow:
    qbittorrent = None
    torrents = {}
    episode_choice: Episode = None
    open_reddit_discussion_asked = False
    delete_torrent_asked = False

    def get_torrents_info(self):
        return self.qbittorrent.torrents_info(category="Anime", sort="name")

    def get_episodes(self, torrent):
        episodes = set()
        for index, file in enumerate(torrent.files):
            if file.get("progress") == PROGRESS_COMPLETE and file.priority == 1:
                path = Path(torrent.save_path) / file.name
                if not path.exists():
                    continue
                episode = Episode(
                    file.index,
                    file.name,
                    str(path),
                    torrent.hash,
                    index == len(torrent.files) - 1,  # can_delete_torrent
                )
                episodes.add(episode)
                self.torrents[episode] = torrent

        return episodes

    def select_episode(self):
        inquirer_episode_choice = "episode choice"
        episodes = set()
        torrents = self.get_torrents_info()
        for torrent in torrents:
            episodes |= self.get_episodes(torrent)

        questions = [
            inquirer.List(
                inquirer_episode_choice,
                message="What do you want to watch?",
                choices=sorted(
                    [episode for episode in episodes],
                    key=lambda ep: (ep.anime_title, ep.season, ep.episode_number),
                )
                + [RELOAD],
                carousel=True,
            )
        ]

        episode_choice = inquirer.prompt(questions, raise_keyboard_interrupt=True).get(
            inquirer_episode_choice
        )
        if episode_choice == RELOAD:
            return
        else:
            self.episode_choice = episode_choice
            os.startfile(self.episode_choice.path)

    def maybe_open_reddit_discussion(self):
        reddit_url = self.get_reddit_discussion_thread_or_search_query()

        inquirer_open_reddit_discussion = "reddit"
        should_open_reddit_discussion = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_open_reddit_discussion,
                    message="Open r/anime discussion thread?",
                    default=True,
                )
            ],
            raise_keyboard_interrupt=True,
        ).get(inquirer_open_reddit_discussion)

        if should_open_reddit_discussion:
            webbrowser.open_new(reddit_url)

        self.open_reddit_discussion_asked = True

    def get_reddit_discussion_thread_or_search_query(self):
        query = [
            "subreddit:anime",
            "flair:episode",
            self.episode_choice.get_reddit_searchable_query(),
        ]
        params = {
            "q": " ".join(query),
            "restrict_sr": "",
            "sort": "new",
            "t": "all",
        }
        encoded_params = urllib.parse.urlencode(params)

        reddit_search = REDDIT_SEARCH_JSON + encoded_params
        with urllib.request.urlopen(reddit_search) as response:
            data = json.load(response)
            posts = nested_get(data, ["data", "children"])
            if posts and len(posts) == 1:
                return nested_get(posts[0], ["data", "url"])

        # Could not confidently find the discussion thread. Open search page instead.
        return REDDIT_SEARCH + encoded_params

    def maybe_delete_file(self):
        inquirer_delete_torrent = "delete"
        should_delete_torrent = inquirer.prompt(
            [inquirer.Confirm(inquirer_delete_torrent, message="Delete torrent?")],
            raise_keyboard_interrupt=True,
        ).get(inquirer_delete_torrent)
        if should_delete_torrent:
            self.delete_torrent()
        self.delete_torrent_asked = True

    def delete_torrent(self):
        if self.episode_choice.can_delete_torrent:
            self.torrents[self.episode_choice].delete(delete_files=True)
        else:
            self.torrents[self.episode_choice].file_priority(
                file_ids=self.episode_choice.index, priority=0
            )
            os.remove(self.episode_choice.path)

    def init(self):
        conn_info = dict(
            host="localhost",
            port=8080,
        )
        self.qbittorrent = qbittorrentapi.Client(**conn_info)

    def start(self):
        try:
            self.init()
            while True:
                if self.episode_choice is None:
                    self.reset()
                    self.select_episode()
                elif not self.open_reddit_discussion_asked:
                    self.maybe_open_reddit_discussion()
                elif not self.delete_torrent_asked:
                    self.maybe_delete_file()
                else:
                    self.reset()
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        self.open_reddit_discussion_asked = False
        self.delete_torrent_asked = False
        os.system("cls")


def nested_get(dic, keys):
    for key in keys:
        if not isinstance(dic, dict):
            return None
        dic = dic.get(key)
    return dic


AniFlow().start()
