import json
import requests
import time
import logging

################################
# config
################################

timer = 1  # how often (in hours) to check for new shows and add them
traktAPI = ''  # API from your trakt account
sonarrAPI = ''  # API from your sonarr install
traktLimit = '100'  # how many results to request from trakt's list
listName = 'anticipated'  # Trending, popular or anticipated
sonarr = 'http://localhost:8989'  # URL to sonarr install, normally localhost:8989
quality_profile = 'any'  # Sonarr quality profile to add shows under
folder_path = '/tv/'  # Root folder to download tv shows into

# Optional filters
tRatings = ''  # Only return results which have Trakt ratings within set range, e.g. 70-100
tGenres = ''  # Only return results within specified genres, e.g. action, adventure, comedy
tLang = 'en'  # Only return results in set language, e.g en or es
tYears = ''  # Only return results from year, or year range, e.g. 2007 or 2007-2015
tCountries = ''  # Only return results from country, e.g. us
tRuntimes = '30-240'  # Only return results where shows have a runtime within range, e.g. 30-60

################################
# setup
################################

logging.basicConfig(format='%(asctime)s - %(levelname)s: %(message)s', filename='sonarrPush.log', level=logging.DEBUG)
sonarrHeaders = {'X-Api-Key': sonarrAPI}
traktHeaders = {'content-type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': traktAPI, }
options = {"ignoreEpisodesWithFiles": False, "ignoreEpisodesWithoutFiles": False, "searchForMissingEpisodes": True}
sent = None
newShows = []


def trakt_url():
    turl = "https://api.trakt.tv" + "/shows/%s/?limit=%s" % (listName, traktLimit)
    if tRatings:
        turl += '&ratings=' + tRatings
    if tGenres:
        turl += '&genres=' + tGenres.lower()
    if tLang:
        turl += '&languages=' + tLang.lower()
    if tYears:
        turl += '&years=' + tYears.lower()
    if tCountries:
        turl += '&countries=' + tCountries.lower()
    if tRuntimes:
        turl += '&runtimes=' + tRuntimes
    return turl


def qprofile_lookup():
    """Check sonarr quality profile ID"""
    r = requests.get(sonarr + '/api/profile', headers=sonarrHeaders)
    qprofile_id = r.json()
    x = 0
    for l in qprofile_id:
        if qprofile_id[x]['name'].lower() == quality_profile.lower():
            return qprofile_id[x]['id']
        else:
            x += 1


def sonarr_lib():
    """get sonarr library in a list of tvdbid ids"""
    r = requests.get(sonarr + '/api/series', headers=sonarrHeaders)
    tvLibList = []
    global tvLibList
    tv_lib_raw = r.json()
    for n in tv_lib_raw:
        tvLibList.append(n['tvdbId'])
    return tvLibList


def get_trakt():
    """get trakt list info"""
    r = requests.get(trakt_url(), headers=traktHeaders)
    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        logging.error('Trakt list request failed, is trakt.tv down?')


def send_to_sonarr():
    """send found tv program to sonarr"""
    payload = {"tvdbId": tvdbId, "title": title, "qualityProfileId": qprofile_lookup(), "seasons": [],
               "seasonFolder": True, "rootFolderPath": folder_path, "addOptions": options, "images": []}
    r = requests.post(sonarr + '/api/series', headers=sonarrHeaders, data=json.dumps(payload))
    global sent
    sent = payload
    if r.status_code == 201:
        sent = True
    else:
        sent = False
    return sent


def add_shows():
    """Check new shows & add missing"""
    sonarr_lib()
    for x in get_trakt():
        if x['show']['ids']['tvdb'] not in tvLibList:
            title = ''
            tvdbId = ''
            global tvdbId
            global title
            tvdbId = (x['show']['ids']['tvdb'])
            title = (x['show']['title'])
            try:
                logging.debug('send show to sonarr: ' + title)
                send_to_sonarr()
                if sent:
                    logging.info(title + ' has been added to Sonarr')
                else:
                    logging.warning(title + ' failed to be added to Sonarr!')
            except:
                logging.warning('error sending, check tvdb - ID movie: ' + title + ' tvdbid: ' + str(tvdbId))


def new_check():
    """check for new trakt items in list"""
    logging.info('checking for new shows in Trakt list')
    for x in get_trakt():
        logging.debug('checking show from list: ' + x['show']['title'])
        if x['show']['ids']['tvdb'] not in sonarr_lib():
            logging.info('adding shows')
            add_shows()
        else:
            logging.info('no new shows to add, checking again in ' + str(timer) + ' hour(s)')
            time.sleep(120)
            new_check()


new_check()
