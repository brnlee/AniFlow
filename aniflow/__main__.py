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
    DELETE_EPISODE = 6


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
                    case State.DELETE_EPISODE:
                        self.delete_episode()
                    case _:
                        self.state = State.SELECT_EPISODE
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        os.system("cls")

    def select_episode(self):
        reload_episodes_choice = "[Reload Episodes]"

        choices = [reload_episodes_choice] + self.qbittorrent.get_episodes()
        choice = prompt.list("What do you want to watch?", choices)
        if choice is reload_episodes_choice:
            return
        else:
            os.startfile(choice.path)
            self.anilist.find_and_set_data(choice)
            self.episode_choice = choice
            self.state = State.OPEN_REDDIT_DISCUSSION

    def open_reddit_discussion(self):
        self.state = State.AUTH_ANILIST

        reddit_url = self.reddit.get_discussion_url(self.episode_choice)

        open_reddit_discussion = prompt.confirm("Open r/anime discussion thread?")
        if open_reddit_discussion:
            webbrowser.open_new(reddit_url)

    def auth_anilist(self):
        self.state = State.UPDATE_ANILIST

        if not self.anilist.should_auth():
            return

        proceed = prompt.confirm(
            "AniList requires your authorization in order to update your anime list. Proceed?"
        )
        if not proceed:
            self.state = State.OPEN_ANILIST
            return

        self.anilist.open_authorization_page()

        access_token = prompt.password("Paste the token provided by AniList")
        self.anilist.set_access_token(access_token)

    def update_anilist(self):
        self.state = State.OPEN_ANILIST

        if not self.episode_choice.anilist_entry:
            return

        update_anilist = prompt.confirm(
            f'Update progress on AniList for "{self.episode_choice.anilist_entry.titles[0]}"?'
        )
        if update_anilist:
            encountered_auth_error = self.anilist.update_entry(self.episode_choice)
            if encountered_auth_error:
                self.state = State.AUTH_ANILIST

    def open_anilist(self):
        self.state = State.DELETE_EPISODE

        if not self.episode_choice.is_last_episode():
            return

        open_anilist = prompt.confirm("Open AniList page for the anime?")
        if open_anilist:
            webbrowser.open_new(self.episode_choice.anilist_entry.url)

    def delete_episode(self):
        self.state = State.SELECT_EPISODE

        delete_episode = prompt.confirm("Delete episode?", default=False)
        if delete_episode:
            self.qbittorrent.delete(self.episode_choice)


if __name__ == "__main__":
    AniFlow().start()
