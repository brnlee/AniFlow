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
        for index, file in enumerate(torrent.files):
            if (
                file.get("progress") == self.PROGRESS_COMPLETE
                and file.priority != self.PRIORITY_DO_NOT_DOWNLOAD
            ):
                path = Path(torrent.save_path) / file.name
                if not path.exists() or not self._is_video_file(path):
                    continue
                episode = Episode(
                    file.index,
                    file.name,
                    str(path),
                    torrent.hash,
                    can_delete_torrent=index == len(torrent.files) - 1,
                )
                episodes.append(episode)
                self.torrents[episode] = torrent
        return episodes

    def _is_video_file(self, path):
        return guess_type(path)[0].startswith("video")
