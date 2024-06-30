import os
import webbrowser
from enum import Enum

import prompt
from anilist import AniList
from common import Episode
from dotenv import load_dotenv
from qbittorrent import Qbittorrent
from reddit import Reddit


class State(Enum):
    SELECT_EPISODE = 1
    OPEN_REDDIT_DISCUSSION = 2
    AUTH_ANILIST = 3
    UPDATE_ANILIST = 4
    OPEN_ANILIST = 5
    DELETE_FILE = 6


class AniFlow:

    def __init__(self):
        load_dotenv()
        self.qbittorrent = Qbittorrent()
        self.reddit = Reddit()
        self.anilist = AniList()

        self.state = State.SELECT_EPISODE
        self.episode_choice: Episode

    def start(self):
        try:
            while True:
                match (self.state):
                    case State.SELECT_EPISODE:
                        self.reset()
                        self.select_episode()
                    case State.OPEN_REDDIT_DISCUSSION:
                        self.open_reddit_discussion()
                    case State.AUTH_ANILIST:
                        self.auth_anilist()
                    case State.UPDATE_ANILIST:
                        self.update_anilist()
                    case State.OPEN_ANILIST:
                        self.open_anilist()
                    case State.DELETE_FILE:
                        self.delete_file()
                    case _:
                        self.state = State.SELECT_EPISODE
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        os.system("cls")

    def select_episode(self):
        reload_episodes = "[Reload Episodes]"

        choices = sorted(
            [episode for episode in self.qbittorrent.get_episodes()],
            key=lambda ep: (
                ep.anime_title,
                ep.season,
                float(ep.episode_number) if ep.episode_number else None,
            ),
        ) + [reload_episodes]

        choice = prompt.list("What do you want to watch?", choices)
        if choice is reload_episodes:
            return
        else:
            self.state = State.OPEN_REDDIT_DISCUSSION
            self.episode_choice = choice
            os.startfile(self.episode_choice.path)
            self.anilist.find_and_set_data(self.episode_choice)

    def open_reddit_discussion(self):
        self.state = State.AUTH_ANILIST

        reddit_url = self.reddit.get_discussion_url(self.episode_choice)

        should_open_reddit_discussion = prompt.confirm(
            "Open r/anime discussion thread?"
        )
        if should_open_reddit_discussion:
            webbrowser.open_new(reddit_url)

    def auth_anilist(self):
        self.state = State.UPDATE_ANILIST

        if not self.anilist.should_auth():
            return

        should_proceed = prompt.confirm("AniList requires authorization. Proceed?")
        if not should_proceed:
            self.state = State.DELETE_FILE
            return

        self.anilist.get_access_token()

        access_token = prompt.text("Paste the token provided by AniList")
        self.anilist.set_access_token(access_token)

    def update_anilist(self):
        self.state = State.OPEN_ANILIST

        if not self.episode_choice.anilist_data:
            return

        update_anilist_progress = prompt.confirm("Update progress on AniList?")
        if update_anilist_progress:
            encountered_auth_error = self.anilist.update_progress(self.episode_choice)
            if encountered_auth_error:
                self.state = State.AUTH_ANILIST

    def open_anilist(self):
        self.state = State.DELETE_FILE

        if not self.episode_choice.is_last_episode():
            return

        should_open_anilist = prompt.confirm("Open AniList entry?")
        if should_open_anilist:
            webbrowser.open_new(self.episode_choice.anilist_data.entry_url)

    def delete_file(self):
        self.state = State.SELECT_EPISODE

        should_delete_torrent = prompt.confirm("Delete torrent?", default=False)
        if should_delete_torrent:
            self.qbittorrent.delete(self.episode_choice)


if __name__ == "__main__":
    AniFlow().start()
