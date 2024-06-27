import requests

from common import Episode, nested_get

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


def get_titles(episode: Episode):
    search_title = episode.fmt_str(delimiter=" ", include_episode_number=False)
    query = """
    query ($search: String) {
    anime: Page(perPage: 10) {
        results: media(type: ANIME, search: $search) {
        title {
            english
            romaji
        }
        synonyms
        }
    }
    }
    """
    variables = {"search": search_title}

    response = requests.post(URL, json={"query": query, "variables": variables})
    if response.status_code != 200:
        return None

    results = nested_get(response.json(), ["data", "anime", "results"])
    for media in results:
        titles = list(media.get("title").values()) + sorted(media.get("synonyms"))
        if any(map(lambda title: do_titles_match(episode, title), titles)):
            return titles

    return [search_title]
