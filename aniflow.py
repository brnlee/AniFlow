import os
import webbrowser
from pathlib import Path

import inquirer
import qbittorrentapi

from common import Episode
from reddit import Reddit

PROGRESS_COMPLETE = 1

RELOAD = "[Reload Episodes]"


class AniFlow:
    qbittorrent = None
    reddit = None
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
            # os.startfile(self.episode_choice.path)

    def maybe_open_reddit_discussion(self):
        reddit_url = self.reddit.get_discussion_url(self.episode_choice)
        if not reddit_url:
            self.open_reddit_discussion_asked = True
            return

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

        self.reddit = Reddit()

    def start(self):
        try:
            self.init()
            while True:
                if self.episode_choice is None:
                    self.reset()
                    self.select_episode()
                elif not self.open_reddit_discussion_asked:
                    self.maybe_open_reddit_discussion()
                # elif not self.delete_torrent_asked:
                #     self.maybe_delete_file()
                else:
                    self.reset()
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        self.open_reddit_discussion_asked = False
        self.delete_torrent_asked = False
        os.system("cls")


AniFlow().start()
