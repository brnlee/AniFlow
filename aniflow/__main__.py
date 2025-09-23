import os
import subprocess
import webbrowser
from enum import Enum, auto
from threading import Thread

import prompt
from anilist import AniList
from common import Episode, ResultThread
from dotenv import load_dotenv
from qbittorrent import Qbittorrent
from reddit import Reddit


class State(Enum):
    SELECT_EPISODE = auto()
    PLAY_VIDEO = auto()
    PREFETCH_DATA = auto()
    AUTH_ANILIST = auto()
    UPDATE_ANILIST = auto()
    OPEN_REDDIT_DISCUSSION = auto()
    OPEN_ANILIST = auto()
    DELETE_EPISODE = auto()
    CLEAN_UP = auto()


class AniFlow:

    episode_choice: Episode
    advance_to_clean_up: bool
    prefetch_data_thread: ResultThread
    update_anilist_thread: ResultThread

    def __init__(self):
        load_dotenv()

        self.qbittorrent = Qbittorrent()
        self.reddit = Reddit()
        self.anilist = AniList()

        self.state = State.SELECT_EPISODE

    def start(self):
        try:
            while True:
                match (self.state):
                    case State.SELECT_EPISODE:
                        self.reset()
                        self.state = self.select_episode()
                    case State.PLAY_VIDEO:
                        self.state = self.play_video()
                    case State.AUTH_ANILIST:
                        self.state = self.auth_anilist()
                    case State.UPDATE_ANILIST:
                        self.state = self.update_anilist()
                    case State.OPEN_REDDIT_DISCUSSION:
                        self.state = self.open_reddit_discussion()
                    case State.OPEN_ANILIST:
                        self.state = self.open_anilist()
                    case State.DELETE_EPISODE:
                        self.state = self.delete_episode()
                    case State.CLEAN_UP:
                        self.state = self.clean_up()
                    case _:
                        self.state = State.SELECT_EPISODE
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        self.advance_to_clean_up = False
        self.prefetch_data_thread = None
        self.update_anilist_thread = None
        if os.name == 'nt':
            os.system("cls")
        else:
            os.system('clear')

    def select_episode(self):
        reload_episodes_choice = "[Reload Episodes]"
        choices = [reload_episodes_choice] + self.qbittorrent.get_episodes()
        choice = prompt.list("Select an episode", choices)
        if choice is reload_episodes_choice:
            return State.SELECT_EPISODE
        else:
            self.episode_choice = choice
            self.prefetch_data_thread = ResultThread(target=self.prefetch_data)
            self.prefetch_data_thread.start()
            return State.PLAY_VIDEO

    def play_video(self):
        play_video = prompt.confirm("Play video?")
        if play_video:
            if os.name  == 'nt':
                os.startfile(self.episode_choice.path)
            else:
                subprocess.call(['xdg-open', self.episode_choice.path])
        return State.AUTH_ANILIST

    def auth_anilist(self):
        if self.anilist.should_auth():
            proceed = prompt.confirm(
                "AniList requires your authorization in order to update your anime list. Proceed?"
            )
            if not proceed:
                return State.OPEN_REDDIT_DISCUSSION

            self.anilist.open_authorization_page()
            access_token = prompt.password("Paste the token provided by AniList")
            self.anilist.set_access_token(access_token)
        return State.UPDATE_ANILIST

    def update_anilist(self):
        self.prefetch_data_thread.join()
        if not self.episode_choice.anilist_entry:
            return State.OPEN_REDDIT_DISCUSSION

        update_anilist = prompt.confirm(
            f'Update progress on AniList for "{self.episode_choice.anilist_entry.titles[0]}"?'
        )
        if update_anilist:
            self.update_anilist_thread = ResultThread(
                target=self.anilist.update_entry, args=[self.episode_choice]
            )
            self.update_anilist_thread.start()

        return (
            State.CLEAN_UP if self.advance_to_clean_up else State.OPEN_REDDIT_DISCUSSION
        )

    def open_reddit_discussion(self):
        open_reddit_discussion = prompt.confirm("Open r/anime discussion thread?")
        if open_reddit_discussion:
            self.prefetch_data_thread.join()
            reddit_discussion = self.prefetch_data_thread.result
            if reddit_discussion:
                Thread(target=reddit_discussion.upvote).start()
                url = reddit_discussion.url
            else:
                url = self.reddit.get_generic_search_url(self.episode_choice)
            webbrowser.open_new(url)
        return State.OPEN_ANILIST

    def open_anilist(self):
        if self.episode_choice.anilist_entry and self.episode_choice.is_last_episode():
            open_anilist = prompt.confirm("Open AniList page for the anime?")
            if open_anilist:
                webbrowser.open_new(self.episode_choice.anilist_entry.url)
        return State.DELETE_EPISODE

    def delete_episode(self):
        delete_episode = prompt.confirm("Delete episode?", default=False)
        if delete_episode:
            self.qbittorrent.delete(self.episode_choice)
        return State.CLEAN_UP

    def clean_up(self):
        if self.update_anilist_thread:
            self.update_anilist_thread.join()
            encountered_auth_error = self.update_anilist_thread.result
            self.update_anilist_thread = None
            if encountered_auth_error:
                self.advance_to_clean_up = True
                return State.AUTH_ANILIST

        return State.SELECT_EPISODE

    def prefetch_data(self):
        self.anilist.update_episode_with_anilist_data(self.episode_choice)
        return self.reddit.find_discussion(self.episode_choice)


if __name__ == "__main__":
    AniFlow().start()
