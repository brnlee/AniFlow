import os
import webbrowser

import inquirer
from dotenv import load_dotenv

from anilist import AniList
from common import Episode
from qbittorrent import Qbittorrent
from reddit import Reddit

RELOAD = "[Reload Episodes]"


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

    def select_episode(self):
        inquirer_episode_choice = "episode choice"
        questions = [
            inquirer.List(
                inquirer_episode_choice,
                message="What do you want to watch?",
                choices=sorted(
                    [episode for episode in self.qbittorrent.get_episodes()],
                    key=lambda ep: (
                        ep.anime_title,
                        ep.season,
                        float(ep.episode_number) if ep.episode_number else None,
                    ),
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
            self.anilist.find_and_set_data(self.episode_choice)

    def maybe_open_reddit_discussion(self):
        reddit_url = self.reddit.get_discussion_url(self.episode_choice)

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

    def maybe_auth_anilist(self):
        if not self.anilist.should_auth():
            self.auth_anilist_asked = True
            return

        self.anilist.get_access_token()

        inquirer_anilist_auth = "anilist_auth"
        access_token = inquirer.prompt(
            [
                inquirer.Text(
                    inquirer_anilist_auth,
                    message="Enter the Auth Pin from AniList",
                )
            ],
            raise_keyboard_interrupt=True,
        ).get(inquirer_anilist_auth)
        self.anilist.set_access_token(access_token)

        self.auth_anilist_asked = True

    def maybe_update_anilist_progress(self):
        if not self.episode_choice.anilist_data:
            self.update_anilist_progress_asked = True
            return

        inquirer_update_anilist_progress = "update_anilist_progress"
        update_anilist_progress = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_update_anilist_progress,
                    message="Update progress on AniList?",
                    default=True,
                )
            ],
            raise_keyboard_interrupt=True,
        ).get(inquirer_update_anilist_progress)

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

        inquirer_open_anilist = "anilist"
        should_open_anilist = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_open_anilist,
                    message="Open AniList entry?",
                    default=True,
                )
            ],
            raise_keyboard_interrupt=True,
        ).get(inquirer_open_anilist)

        if should_open_anilist:
            webbrowser.open_new(self.episode_choice.anilist_data.entry_url)

    def maybe_delete_file(self):
        inquirer_delete_torrent = "delete"
        should_delete_torrent = inquirer.prompt(
            [inquirer.Confirm(inquirer_delete_torrent, message="Delete torrent?")],
            raise_keyboard_interrupt=True,
        ).get(inquirer_delete_torrent)

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


AniFlow().start()
