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
        query = Reddit._create_reddit_search_query(episode)
        submissions = self.anime_subreddit.search(query)

        submission = next(submissions, None)
        # Only return a URL here if there is only a single matching submission
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
    def _create_reddit_search_query(episode: Episode):
        title_terms = " OR ".join([f'"{title}"' for title in get_titles(episode)])
        query = f"flair:episode ({title_terms})"
        if episode.episode_number:
            query += f' AND "Episode {episode.episode_number}"'
        return query
