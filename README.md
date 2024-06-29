# AniFlow
An all-in-one command-line program to streamline your anime experience from start to finish.

## Features
* List ready-to-watch episodes from [qBittorrent](https://www.qbittorrent.org/)
* Open the episode you want watch with your video player
* Bring up the [r/anime](https://reddit.com/r/anime/) episode discussion thread
* Update the progress after each episode in AniList
* Open the AniList entry after the final episode has been watched
* Remove the episode from your system & qBittorrent

## Setup
### Dependencies
```console
pip install -r requirements.txt
```

### Secrets
Various secrets are required:
* Reddit: Create an application on [Reddit](https://reddit.com/prefs/apps/)
* AniList: Create a client on [Aniflow](https://anilist.co/settings/developer)

Create a ".env" file in the project root directory in the format of "[.env.sample](.env.sample)" and add the secrets for each service.

## Usage
```console
python ./aniflow.py
```

## Platform Support
This script has only been tested on Windows.

