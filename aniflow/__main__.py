import os
import webbrowser

import prompt
from anilist import AniList
from common import Episode
from dotenv import load_dotenv
from qbittorrent import Qbittorrent
from reddit import Reddit


class AniFlow:
    qbittorrent = None
    reddit = None
    anilist = None
    episode_choice: Episode = None
    open_reddit_discussion_asked = False
    auth_anilist_asked = False
    update_anilist_progress_asked = False
    open_anilist_asked = False
    delete_torrent_asked = False
    RELOAD = "[Reload Episodes]"

    def select_episode(self):
        choices = sorted(
            [episode for episode in self.qbittorrent.get_episodes()],
            key=lambda ep: (
                ep.anime_title,
                ep.season,
                float(ep.episode_number) if ep.episode_number else None,
            ),
        ) + [self.RELOAD]

        episode_choice = prompt.list("What do you want to watch?", choices)
        if episode_choice == self.RELOAD:
            return
        else:
            self.episode_choice = episode_choice
            os.startfile(self.episode_choice.path)
            self.anilist.find_and_set_data(self.episode_choice)

    def maybe_open_reddit_discussion(self):
        reddit_url = self.reddit.get_discussion_url(self.episode_choice)

        should_open_reddit_discussion = prompt.confirm(
            "Open r/anime discussion thread?"
        )

        if should_open_reddit_discussion:
            webbrowser.open_new(reddit_url)

        self.open_reddit_discussion_asked = True

    def maybe_auth_anilist(self):
        if not self.anilist.should_auth():
            self.auth_anilist_asked = True
            return

        self.anilist.get_access_token()

        access_token = prompt.text("Enter the Auth Pin from AniList")
        self.anilist.set_access_token(access_token)

        self.auth_anilist_asked = True

    def maybe_update_anilist_progress(self):
        if not self.episode_choice.anilist_data:
            self.update_anilist_progress_asked = True
            return

        update_anilist_progress = prompt.confirm("Update progress on AniList?")
        if update_anilist_progress:
            encountered_auth_error = self.anilist.update_progress(self.episode_choice)
            if encountered_auth_error:
                self.auth_anilist_asked = False
                return

        self.update_anilist_progress_asked = True

    def maybe_open_anilist(self):
        self.open_anilist_asked = True

        if not self.episode_choice.is_last_episode():
            return

        should_open_anilist = prompt.confirm("Open AniList entry?")
        if should_open_anilist:
            webbrowser.open_new(self.episode_choice.anilist_data.entry_url)

    def maybe_delete_file(self):
        should_delete_torrent = prompt.confirm("Delete torrent?", default=False)
        if should_delete_torrent:
            self.qbittorrent.delete(self.episode_choice)
        self.delete_torrent_asked = True

    def init(self):
        load_dotenv()
        self.qbittorrent = Qbittorrent()
        self.reddit = Reddit()
        self.anilist = AniList()

    def start(self):
        try:
            self.init()
            while True:
                if self.episode_choice is None:
                    self.reset()
                    self.select_episode()
                elif not self.open_reddit_discussion_asked:
                    self.maybe_open_reddit_discussion()
                elif not self.auth_anilist_asked:
                    self.maybe_auth_anilist()
                elif not self.update_anilist_progress_asked:
                    self.maybe_update_anilist_progress()
                elif not self.open_anilist_asked:
                    self.maybe_open_anilist()
                elif not self.delete_torrent_asked:
                    self.maybe_delete_file()
                else:
                    self.reset()
        except KeyboardInterrupt:
            exit()

    def reset(self):
        self.episode_choice = None
        self.open_reddit_discussion_asked = False
        self.auth_anilist_asked = False
        self.update_anilist_progress_asked = False
        self.open_anilist_asked = False
        self.delete_torrent_asked = False
        os.system("cls")


if __name__ == "__main__":
    AniFlow().start()
