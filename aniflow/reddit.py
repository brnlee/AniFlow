import urllib
from os import getenv

import praw
import requests
from common import Episode
from praw.models import Submission
import logging


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
            username=self.USERNAME,
            password=self.PASSWORD,
        )
        self.anime_subreddit = reddit.subreddit("anime")

    def find_discussion(
        self, episode: Episode, use_synonyms: bool = False
    ) -> Submission:
        query = self._create_reddit_search_query(episode, use_synonyms)
        if query:
            submissions = self.anime_subreddit.search(query)
            submission = next(submissions, None)
            # Return here if there is only a single matching submission
            if submission and not next(submissions, None):
                return submission
            elif not use_synonyms:
                logging.info("Could not find exact Reddit thread")
                return self.find_discussion(episode, use_synonyms=True)
            else:
                return None

    def get_generic_search_url(self, episode: Episode) -> str:
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

    def _create_reddit_search_query(
        self, episode: Episode, use_synonyms=False
    ) -> str | None:
        if not episode.anilist_entry:
            return None

        titles = episode.anilist_entry.titles
        if use_synonyms and episode.anilist_entry.synonyms:
            titles.extend(episode.anilist_entry.synonyms)
        title_terms = " OR ".join({f'"{title}"' for title in titles})
        query = f"flair:episode (selftext:({title_terms}) OR title:({title_terms}))"

        episode_numbers = filter(
            None, [episode.episode_number, episode.absolute_episode_number]
        )
        episode_terms = " OR ".join([f'"Episode {n}"' for n in episode_numbers])
        if episode_terms:
            query += f" title:({episode_terms})"

        return query
