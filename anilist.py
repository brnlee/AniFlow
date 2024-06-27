import requests

from common import nested_get

URL = "https://graphql.anilist.co"


def clean_string(string):
    """Removes all non-alphanumeric characters for string comparison"""
    return "".join(char for char in string if char.isalnum())


def get_titles(anime_title):
    clean_title = clean_string(anime_title)

    query = """
    query ($search: String) {
    anime: Page(perPage: 10) {
        pageInfo {
        total
        }
        results: media(type: ANIME, search: $search) {
        id
        title {
            english
            romaji
        }
        synonyms
        }
    }
    }
    """
    variables = {"search": anime_title}

    response = requests.post(URL, json={"query": query, "variables": variables})
    if response.status_code != 200:
        return None

    results = nested_get(response.json(), ["data", "anime", "results"])
    for media in results:
        titles = list(media.get("title").values()) + sorted(media.get("synonyms"))
        for title in titles:
            if not title:
                continue
            if clean_title == clean_string(title):
                return titles

    return [anime_title]
