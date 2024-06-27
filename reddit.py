import urllib

import praw
import requests

import credentials
from anilist import get_titles
from common import Episode


class Reddit:

    def __init__(self) -> None:
        self.reddit_token = Reddit._get_reddit_token()

        reddit = praw.Reddit(
            client_id=credentials.APP_CLIENT_ID,
            client_secret=credentials.APP_CLIENT_SECRET,
            user_agent=credentials.USER_AGENT,
        )
        self.anime_subreddit = reddit.subreddit("anime")

    def get_discussion_url(self, episode: Episode) -> str:
        titles = get_titles(episode.fmt_str(include_episode_number=False))
        for title in titles:
            query = Reddit._create_reddit_search_query(title, episode.episode_number)
            submissions = self.anime_subreddit.search(query, sort="new")
            submission = next(submissions, None)
            if submission and not next(submissions, None):
                return submission.url
        return Reddit._get_blind_search_url(episode)

    @staticmethod
    def _get_blind_search_url(episode: Episode):
        query = [
            "flair:episode",
            episode.anime_title,
        ]
        params = {
            "q": " ".join(query),
            "sort": "new",
            "t": "all",
            "restrict_sr": "on",
        }
        encoded_params = urllib.parse.urlencode(params)
        return f"https://www.reddit.com/r/anime/search?{encoded_params}"

    @staticmethod
    def _get_reddit_token():
        client_auth = requests.auth.HTTPBasicAuth(
            credentials.APP_CLIENT_ID, credentials.APP_CLIENT_SECRET
        )
        post_data = {
            "grant_type": "password",
            "username": credentials.USERNAME,
            "password": credentials.PASSWORD,
        }
        headers = {"User-Agent": credentials.USER_AGENT}
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=client_auth,
            data=post_data,
            headers=headers,
        )
        return response.json().get("access_token")

    @staticmethod
    def _create_reddit_search_query(title: str, episode_number: int):
        search_args = [f'"{title}"']
        if episode_number:
            search_args.append(f'"Episode {episode_number:g}"')
        return " ".join(["flair:episode", " AND ".join(search_args)])
