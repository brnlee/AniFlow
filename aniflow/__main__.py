import os
import webbrowser
from enum import Enum, auto

import prompt
from anilist import AniList
from common import Episode
from dotenv import load_dotenv
from qbittorrent import Qbittorrent
from reddit import Reddit


class State(Enum):
    SELECT_EPISODE = auto()
    PLAY_VIDEO = auto()
    GET_AND_SET_EPISODE_METADATA = auto()
    OPEN_REDDIT_DISCUSSION = auto()
    AUTH_ANILIST = auto()
    UPDATE_ANILIST = auto()
    OPEN_ANILIST = auto()
    DELETE_EPISODE = auto()


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
                        self.state = self.select_episode()
                    case State.PLAY_VIDEO:
                        self.state = self.play_video()
                    case State.GET_AND_SET_EPISODE_METADATA:
                        self.state = self.get_and_set_episode_metadata()
                    case State.OPEN_REDDIT_DISCUSSION:
                        self.state = self.open_reddit_discussion()
                    case State.AUTH_ANILIST:
                        self.state = self.auth_anilist()
                    case State.UPDATE_ANILIST:
                        self.state = self.update_anilist()
                    case State.OPEN_ANILIST:
                        self.state = self.open_anilist()
                    case State.DELETE_EPISODE:
                        self.state = self.delete_episode()
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
        choice = prompt.list("Select an episode", choices)
        if choice is reload_episodes_choice:
            return State.SELECT_EPISODE
        else:
            self.episode_choice = choice
            return State.PLAY_VIDEO

    def play_video(self):
        play_video = prompt.confirm("Play video?")
        if play_video:
            os.startfile(self.episode_choice.path)
        return State.GET_AND_SET_EPISODE_METADATA

    def get_and_set_episode_metadata(self):
        self.anilist.find_and_set_data(self.episode_choice)
        return State.OPEN_REDDIT_DISCUSSION

    def open_reddit_discussion(self):
        reddit_thread = self.reddit.get_discussion_thread(self.episode_choice)
        open_reddit_discussion = prompt.confirm("Open r/anime discussion thread?")
        if open_reddit_discussion:
            if reddit_thread:
                reddit_thread.upvote()
                url = reddit_thread.url
            else:
                url = self.reddit.get_generic_search_url(self.episode_choice)
            webbrowser.open_new(url)
        return State.AUTH_ANILIST

    def auth_anilist(self):
        if self.anilist.should_auth():
            proceed = prompt.confirm(
                "AniList requires your authorization in order to update your anime list. Proceed?"
            )
            if not proceed:
                return State.OPEN_ANILIST

            self.anilist.open_authorization_page()
            access_token = prompt.password("Paste the token provided by AniList")
            self.anilist.set_access_token(access_token)
        return State.UPDATE_ANILIST

    def update_anilist(self):
        if not self.episode_choice.anilist_entry:
            return State.DELETE_EPISODE

        update_anilist = prompt.confirm(
            f'Update progress on AniList for "{self.episode_choice.anilist_entry.titles[0]}"?'
        )
        if update_anilist:
            encountered_auth_error = self.anilist.update_entry(self.episode_choice)
            if encountered_auth_error:
                return State.AUTH_ANILIST
        return State.OPEN_ANILIST

    def open_anilist(self):
        if self.episode_choice.is_last_episode():
            open_anilist = prompt.confirm("Open AniList page for the anime?")
            if open_anilist:
                webbrowser.open_new(self.episode_choice.anilist_entry.url)
        return State.DELETE_EPISODE

    def delete_episode(self):
        delete_episode = prompt.confirm("Delete episode?", default=False)
        if delete_episode:
            self.qbittorrent.delete(self.episode_choice)
        return State.SELECT_EPISODE


if __name__ == "__main__":
    AniFlow().start()
