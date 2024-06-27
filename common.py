import anitopy


class Episode:
    def __init__(self, index, name, path, torrent_hash, can_delete_torrent):
        self.index = index
        self.file_name = name
        self.path = path
        self.torrent_hash = torrent_hash
        self.can_delete_torrent = can_delete_torrent

        anitopy_options = {"parse_file_extension": False, "parse_release_group": False}
        details = anitopy.parse(self._get_file_name(), options=anitopy_options)
        self.anime_title = details.get("anime_title")

        episode_number = details.get("episode_number")
        self.episode_number = (
            float(episode_number.lstrip("0")) if episode_number else None
        )
        self.season = details.get("anime_season")

    def _get_file_name(self):
        """Returns the file name after removing any directory paths"""
        return self.file_name.split("/")[-1]

    def __str__(self):
        return self.fmt_str()

    def fmt_str_tokens(
        self, include_title=True, include_season=True, include_episode_number=True
    ):
        tokens = []

        if include_title:
            tokens.append(self.anime_title)

        if include_season and self.season:
            try:
                tokens.append(f"Season {int(self.season)}")
            except ValueError:
                pass

        if include_episode_number and self.episode_number:
            tokens.append(f"Episode {self.episode_number:g}")

        return tokens

    def fmt_str(self, delimiter=" - ", **kwargs):
        return delimiter.join(self.fmt_str_tokens(**kwargs))


def nested_get(dic, keys):
    for key in keys:
        if not isinstance(dic, dict):
            return None
        dic = dic.get(key)
    return dic