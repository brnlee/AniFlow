import urllib
from os import getenv

import praw
import requests

from common import Episode


class Reddit:

    def __init__(self) -> None:
        self.USERNAME = getenv("REDDIT_USERNAME")
        self.PASSWORD = getenv("REDDIT_PASSWORD")
        self.USER_AGENT = getenv("REDDIT_USER_AGENT")
        self.APP_CLIENT_ID = getenv("REDDIT_APP_CLIENT_ID")
        self.APP_CLIENT_SECRET = getenv("REDDIT_APP_CLIENT_SECRET")

        self.reddit_token = self._get_reddit_token()
        reddit = praw.Reddit(
            client_id=self.APP_CLIENT_ID,
            client_secret=self.APP_CLIENT_SECRET,
            user_agent=self.USER_AGENT,
        )
        self.anime_subreddit = reddit.subreddit("anime")

    def get_discussion_url(self, episode: Episode) -> str:
        query = self._create_reddit_search_query(episode)
        if query:
            submissions = self.anime_subreddit.search(query)
            submission = next(submissions, None)
            # Only return a URL here if there is only a single matching submission
            if submission and not next(submissions, None):
                return submission.url
        return self._get_blind_search_url(episode)

    def _get_blind_search_url(self, episode: Episode):
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

    def _get_reddit_token(self):
        client_auth = requests.auth.HTTPBasicAuth(
            self.APP_CLIENT_ID,
            self.APP_CLIENT_SECRET,
        )
        post_data = {
            "grant_type": "password",
            "username": self.USERNAME,
            "password": self.PASSWORD,
        }
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=client_auth,
            data=post_data,
            headers=headers,
        )
        return response.json().get("access_token")

    def _create_reddit_search_query(self, episode: Episode):
        if not episode.anilist_data:
            return None
        title_terms = " OR ".join(
            [f'"{title}"' for title in episode.anilist_data.titles]
        )
        query = f"flair:episode ({title_terms})"
        if episode.episode_number:
            query += f' AND "Episode {episode.episode_number}"'
        return query
