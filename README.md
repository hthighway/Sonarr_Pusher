# Sonarr Pusher
Python script that checks certain lists on [Trakt](http://trakt.tv), and if they meet your configured filters, adds them to your sonarr library. Sonarr Pusher will check the trakt.tv lists every 24 hours by default to keep sonarr constaly updated with new TV shows

Currently only supports:
1. [Trakt trending](https://trakt.tv/shows/trending)
2. [Trakt anticipated](https://trakt.tv/shows/anticipated)

## Getting Started

You will need a trakt.tv account with a [Trakt api key](https://trakt.tv/oauth/applications/new), as well as your sonarr API.

Quick warning when setting up the script. If you set `traktLimit` to a large number (above `100`) with no filters, you will get that amount of shows added. At minium it is reconmended to use the language code filter.

### Prerequisites

1. Python 2.7
2. requests 2.18.4

`
sudo apt-get install python
`

`
pip install requests
`

### Installing

`git clone https://github.com/Dec64/Sonarr_Pusher.git`

`cd Sonarr_Pusher`

`nano traktToSonarr.py`

Edit your settings as needed.

```
timer = 24  # how often (in hours) to check for new shows and add them
traktAPI = ''  # API from your trakt account
sonarrAPI = ''  # API from your sonarr install
traktLimit = '100'  # how many results to request from trakt's list
listName = 'trending'  # Trending or anticipated
sonarr = 'http://localhost:8989'  # URL to sonarr install, normally localhost:8989
quality_profile = ''  # Sonarr quality profile to add shows under
folder_path = ''  # Root folder to download tv shows into

pushover_user_token = '' # Pushover user token
pushover_app_token = '' # Pushover app token

# Optional filters
tRatings = ''  # Only return results which have Trakt ratings within set range, e.g. 70-100
tGenres = ''  # Only return results within specified genres, e.g. action, adventure, comedy
tLang = 'en'  # Only return results in set language, e.g en or es
tYears = ''  # Only return results from year, or year range, e.g. 2007 or 2007-2015
tCountries = ''  # Only return results from country, e.g. us
tRuntimes = '30-60'  # Only return results where shows have a runtime within range, e.g. 30-60
```

Then to run, simply run:

`python traktToSonarr.py`

If you intend to leave it running, it would be best to use systemd startup or screen.

`screen -S SonarrPusher python traktToSonarr.py`

Check it's all running fine by tailing the log

`tail -f sonarrPush.log`

You should see something similar to:

```
2017-08-25 10:47:06,931 - INFO: checking for new shows in Trakt list
2017-08-25 10:47:06,931 - INFO: new show(s) found, adding shows now
2017-08-25 10:51:29,086 - INFO: send show to sonarr: Alaskan Bush People
2017-08-25 10:51:29,553 - INFO: Alaskan Bush People has been added to Sonarr
2017-08-25 10:51:29,554 - INFO: send show to sonarr: Wynonna Earp
2017-08-25 10:51:30,105 - INFO: Wynonna Earp has been added to Sonarr
2017-08-25 10:51:30,105 - INFO: send show to sonarr: Penn & Teller: Fool Us
```
