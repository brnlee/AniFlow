from pathlib import Path

import anitopy


class Episode:
    def __init__(self, index, name, path, torrent_hash, can_delete_torrent):
        self.index = index
        self.file_name = name
        self.path = path
        self.torrent_hash = torrent_hash
        self.can_delete_torrent = can_delete_torrent

        anitopy_options = {
            "parse_file_extension": False,
            "parse_release_group": False,
            "allowed_delimiters": " _&+,|",
        }
        details = anitopy.parse(self._get_file_name(), options=anitopy_options)
        self.anime_title = details.get("anime_title")

        episode_number = details.get("episode_number")
        self.episode_number = (
            float(episode_number.lstrip("0")) if episode_number else None
        )
        if self.episode_number:
            self.episode_number = f"{self.episode_number:g}"
        self.absolute_episode_number = None
        self.season = int(details.get("anime_season", 0))
        self.anilist_entry: AniListEntry = None

    def is_last_episode(self):
        if not self.anilist_entry:
            return False
        elif not self.episode_number:
            return True

        return int(self.episode_number) is int(self.anilist_entry.episode_count)

    def _get_file_name(self):
        """Returns the file name after removing any directory paths"""
        return self.file_name.split("/")[-1]

    def __str__(self):
        return self.fmt_str()

    def fmt_str_tokens(
        self,
        include_title=True,
        include_season=True,
        include_episode_number=True,
    ):
        tokens = []

        if include_title:
            tokens.append(self.anime_title)

        if include_season and self.season:
            tokens.append(f"Season {int(self.season)}")

        if include_episode_number and self.episode_number:
            tokens.append(f"Episode {self.episode_number}")

        return tokens

    def fmt_str(self, delimiter=" • ", **kwargs):
        return delimiter.join(self.fmt_str_tokens(**kwargs))


class AniListEntry:

    prequel = None
    sequel = None

    def __init__(self, anime: dict) -> None:
        self.id = anime.get("id")
        self.titles = anime.get("titles")
        self.url = anime.get("siteUrl")
        self.episode_count = anime.get("episodes")

    def __str__(self) -> str:
        return f"{self.id} {self.titles} {self.url} prequel={self.prequel} sequel={self.sequel}"

    def __repr__(self) -> str:
        return self.__str__()


def nested_get(dic, keys):
    for key in keys:
        if not isinstance(dic, dict):
            return None
        dic = dic.get(key)
    return dic


def get_root_dir():
    return Path(__file__).parent.parent
