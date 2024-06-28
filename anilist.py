import requests

from common import AniListData, Episode, nested_get

URL = "https://graphql.anilist.co"


def clean_string(string):
    """Removes all non-alphanumeric characters for string comparison"""
    return "".join(char for char in string if char.isalnum()).lower()


def do_titles_match(episode: Episode, title_to_compare: str):
    if not title_to_compare:
        return False

    clean_title = clean_string(episode.anime_title)
    clean_title_to_compare = clean_string(title_to_compare)
    season = episode.season

    if not season:
        return clean_title == clean_title_to_compare

    if clean_title not in clean_title_to_compare:
        return False
    return (
        clean_title_to_compare.endswith(season)
        or clean_string(f"Season {season}") in clean_title_to_compare
        or clean_string(f"S{season}") in clean_title_to_compare
    )


def match_title(episode, results):
    for anime in results:
        anime["titles"] = list(anime.get("title").values()) + sorted(
            anime.get("synonyms")
        )
        if any(map(lambda title: do_titles_match(episode, title), anime["titles"])):
            return anime


def find_and_set_data(episode: Episode):
    query = """
    query ($search: String) {
    anime: Page(perPage: 10) {
        results: media(type: ANIME, search: $search) {
        title {
            english
            romaji
        }
        synonyms
        episodes
        siteUrl
        }
    }
    }
    """
    search_title = episode.fmt_str(delimiter=" ", include_episode_number=False)
    variables = {"search": search_title}

    response = requests.post(URL, json={"query": query, "variables": variables})
    if response.status_code != 200:
        return

    results = nested_get(response.json(), ["data", "anime", "results"])

    anime = match_title(episode, results)
    if not anime:
        return

    anilist_data = AniListData()
    anilist_data.titles = anime.get("titles")
    anilist_data.episode_count = anime.get("episodes")
    anilist_data.entry_url = anime.get("siteUrl")
    episode.anilist_data = anilist_data
