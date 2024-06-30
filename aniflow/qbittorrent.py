import os
from os import getenv
from pathlib import Path

from qbittorrentapi import Client

from common import Episode


class Qbittorrent:

    PROGRESS_COMPLETE = 1

    def __init__(self) -> None:
        self.client = Client(
            host=getenv("QBITTORRENT_HOST"),
            username=getenv("QBITTORRENT_USERNAME"),
            password=getenv("QBITTORRENT_PASSWORD"),
        )
        self.torrents = {}

    def get_episodes(self):
        episodes = []
        for torrent in self._get_torrents():
            episodes.extend(self._get_episodes_per_torrent(torrent))
        return sorted(
            episodes,
            key=lambda ep: (
                ep.anime_title,
                ep.season,
                float(ep.episode_number) if ep.episode_number else None,
            ),
        )

    def delete(self, episode: Episode):
        if episode.can_delete_torrent:
            self.torrents[episode].delete(delete_files=True)
        else:
            self.torrents[episode].file_priority(file_ids=episode.index, priority=0)
            os.remove(episode.path)

    def _get_torrents(self):
        return self.client.torrents_info(category="Anime", sort="name")

    def _get_episodes_per_torrent(self, torrent):
        episodes = []
        for index, file in enumerate(torrent.files):
            if file.get("progress") == self.PROGRESS_COMPLETE and file.priority == 1:
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
                episodes.append(episode)
                self.torrents[episode] = torrent
        return episodes
