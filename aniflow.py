import requests
import os
import inquirer
import anitopy
import urllib
import webbrowser
from pathlib import Path

QBITTORRENT_API = 'http://localhost:8080/api/v2'
TORRENTS_INFO = '/torrents/info'
TORRENTS_FILES = '/torrents/files'
TORRENTS_DELETE = '/torrents/delete'
TORRENTS_RECHECK = '/torrents/recheck'
PROGRESS_COMPLETE = 1

REDDIT = 'https://old.reddit.com/search?'

RELOAD = '[Reload Episodes]'

class Episode:
    def __init__(self, name, path, torrent_hash, can_delete_torrent):
        self.name = name
        self.path = path
        self.torrent_hash = torrent_hash
        self.can_delete_torrent = can_delete_torrent

        anitopy_options = {
            'parse_file_extension': False,
            'parse_release_group': False
        }
        details = anitopy.parse(self.get_name(), options=anitopy_options)
        # print(details)
        self.anime_title = details.get('anime_title')
        episode_number = details.get('episode_number')
        self.episode_number = float(episode_number.lstrip('0')) if episode_number else None
        self.season = details.get('anime_season')

    def get_name(self):
        return self.name.split('/')[-1]

    def get_reddit_searchable_query(self):
        # ["Kaguya-sama wa Kokurasetai", "First Kiss wa Owaranai", "Episode 1"]
        tokens = self.__str__().split(' - ')
        #  "Kaguya-sama wa Kokurasetai" AND "First Kiss wa Owaranai" AND "Episode 1"
        query_with_season = ' AND '.join([f'"{token}"' for token in tokens])
        # if len(tokens) == 3 and self.episode_number:
        #     query_without_season = f'"{self.anime_title}" AND "Episode {self.episode_number}"'
        #     return f'({query_with_season} OR {query_without_season})'
        return query_with_season


    def __str__(self):
        season = ' '
        if self.season:
            try:
                season = f' - Season {int(self.season)} '
            except ValueError:
                pass

        if self.episode_number:
            return f'{self.anime_title}{season}- Episode {self.episode_number:g}'
        else:
            return self.anime_title


class AniFlow:
    episode_choice: Episode = None
    open_reddit_discussion_asked = False
    update_anilist_asked = False
    delete_torrent_asked = False

    def get_torrents_info(self):
        params = {
            'category': 'Anime',
            'sort': 'name',
        }
        request = requests.get(QBITTORRENT_API + TORRENTS_INFO, params)
        torrents_info = request.json()
        return torrents_info

    def get_episodes(self, torrent):
        torrent_hash = torrent.get('hash')
        params = {
            'hash': torrent_hash
        }
        torrent_path = torrent.get('save_path')
        request = requests.get(QBITTORRENT_API + TORRENTS_FILES, params)
        files = request.json()
        episodes = {}
        for index, file in enumerate(files):
            if file.get('progress') == PROGRESS_COMPLETE:
                name = file.get('name')
                path = Path(torrent_path) / name
                if not path.exists():
                    continue
                episodes[name] = Episode(
                    name,
                    str(path),
                    torrent_hash,
                    index == len(files) - 1 # can_delete_torrent
                )
        return episodes

    def select_episode(self):
        inquirer_episode_choice = 'episode choice'
        episodes = {}
        torrents = self.get_torrents_info()
        for torrent in torrents:
            episodes |= self.get_episodes(torrent)

        questions = [
            inquirer.List(
                inquirer_episode_choice,
                message="What do you want to watch?",
                choices=sorted([episode for episode in episodes.values()], key=lambda ep: (ep.anime_title, ep.season, ep.episode_number)) + [RELOAD],
                carousel=True
            )
        ]

        episode_choice = inquirer.prompt(questions, raise_keyboard_interrupt=True).get(inquirer_episode_choice)
        if episode_choice == RELOAD:
            return
        else:
            self.episode_choice = episode_choice  
            os.startfile(self.episode_choice.path)

    def maybe_open_reddit_discussion(self):
        inquirer_open_reddit_discussion = 'reddit'
        should_open_reddit_discussion = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_open_reddit_discussion,
                    message="Open r/anime discussion thread?",
                    default=True
                )
            ],
            raise_keyboard_interrupt=True).get(inquirer_open_reddit_discussion)

        query = [
            'subreddit:anime',
            'flair:episode',
            self.episode_choice.get_reddit_searchable_query()
        ]

        if should_open_reddit_discussion:
            params = {
                'q': ' '.join(query),
                'restrict_sr': '',
                'sort': 'new',
                't': 'all'
            }
            reddit_search = REDDIT + urllib.parse.urlencode(params)
            webbrowser.open_new(reddit_search)

        self.open_reddit_discussion_asked = True

    def maybe_update_anilist(self):
        inquirer_update_anilist = 'anilist'
        should_update_anilist = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_update_anilist,
                    message="Update AniList?",
                    default=True
                )
            ],
            raise_keyboard_interrupt=True
        ).get(inquirer_update_anilist)

        if should_update_anilist:
            print('Updating AniList')

        self.update_anilist_asked = True

    def maybe_delete_file(self):
        inquirer_delete_torrent = 'delete'
        should_delete_torrent = inquirer.prompt(
            [
                inquirer.Confirm(
                    inquirer_delete_torrent,
                    message="Delete torrent?"
                )
            ],
            raise_keyboard_interrupt=True
        ).get(inquirer_delete_torrent)
        if should_delete_torrent:
            self.delete_torrent()
        self.delete_torrent_asked = True

    def delete_torrent(self):
        if self.episode_choice.can_delete_torrent:
            params = {
                'hashes': self.episode_choice.torrent_hash,
                'deleteFiles': 'true',
            }
            requests.post(QBITTORRENT_API + TORRENTS_DELETE, params)
        else:
            os.remove(self.episode_choice.path)
            params = {  
                'hashes': self.episode_choice.torrent_hash,
            }
            requests.post(QBITTORRENT_API + TORRENTS_RECHECK, params)

    def start(self):
        try:
            while True:
                if self.episode_choice is None:
                    self.reset()
                    self.select_episode()
                elif not self.open_reddit_discussion_asked:
                    self.maybe_open_reddit_discussion()
                # elif self.should_update_anilist is None:
                #     self.update_anilist()
                elif not self.delete_torrent_asked:
                    self.maybe_delete_file()
                else:
                    self.reset()
        except KeyboardInterrupt:
            exit()
        finally:
            # In case I close the program before remembering to delete a watched episode first.
            print()
            if self.open_reddit_discussion_asked:
                self.delete_torrent()

    def reset(self):
        self.episode_choice = None
        self.open_reddit_discussion_asked = False
        self.update_anilist_asked = False
        self.delete_torrent_asked = False
        os.system('cls')


AniFlow().start()
