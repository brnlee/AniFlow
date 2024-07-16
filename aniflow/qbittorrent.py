import os
from mimetypes import guess_type
from os import getenv
from pathlib import Path

from common import Episode
from qbittorrentapi import Client


class Qbittorrent:

    # https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)#get-torrent-contents
    PROGRESS_COMPLETE = 1
    PRIORITY_DO_NOT_DOWNLOAD = 0

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
        files = self._filter_torrent_files(torrent)
        is_torrent_with_single_file = len(files) == 1
        for file in files:
            episode = Episode(
                file.index,
                file.name,
                str(Path(torrent.save_path) / file.name),
                torrent.hash,
                can_delete_torrent=is_torrent_with_single_file,
            )
            episodes.append(episode)
            self.torrents[episode] = torrent
        return episodes

    def _is_video_file(self, path):
        return guess_type(path)[0].startswith("video")

    def _filter_torrent_files(self, torrent):
        files = []
        for file in torrent.files:
            if (
                file.get("progress") == self.PROGRESS_COMPLETE
                and file.priority != self.PRIORITY_DO_NOT_DOWNLOAD
            ):
                path = Path(torrent.save_path) / file.name
                if path.exists() and self._is_video_file(path):
                    files.append(file)
        return files
