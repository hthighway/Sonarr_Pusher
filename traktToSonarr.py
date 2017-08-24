import json
import requests
import time
import logging
import sys

################################
# config
################################

timer = 24  # how often (in hours) to check for new shows and add them
traktAPI = ''  # API from your trakt account
sonarrAPI = ''  # API from your sonarr install
traktLimit = '100'  # how many results to request from trakt's list
listName = 'trending'  # Trending or anticipated
sonarr = 'http://localhost:8989'  # URL to sonarr install, normally localhost:8989
quality_profile = ''  # Sonarr quality profile to add shows under
folder_path = ''  # Root folder to download tv shows into

pushover_user_token = ''
pushover_app_token = ''

# Optional filters
tRatings = ''  # Only return results which have Trakt ratings within set range, e.g. 70-100
tGenres = ''  # Only return results within specified genres, e.g. action, adventure, comedy
tLang = 'en'  # Only return results in set language, e.g en or es
tYears = ''  # Only return results from year, or year range, e.g. 2007 or 2007-2015
tCountries = ''  # Only return results from country, e.g. us
tRuntimes = '30-60'  # Only return results where shows have a runtime within range, e.g. 30-60

################################
# setup
################################

logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s: %(message)s', filename='sonarrPush.log',
                    level=logging.INFO)
sonarrHeaders = {'X-Api-Key': sonarrAPI}
pushHeaders = {'Content-Type": "application/x-www-form-urlencoded', 'Content-Length: 180'}
traktHeaders = {'content-type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': traktAPI, }
options = {"ignoreEpisodesWithFiles": False, "ignoreEpisodesWithoutFiles": False, "searchForMissingEpisodes": True}
sent = None
newShows = []
delay_time = timer * 3600


def send_pushover(app_token, user_token, message):
    try:
        payload = {'token': app_token, 'user': user_token, 'title': 'Sonarr Push', 'message': message}
        r = requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'Python'})
        resp = r.status_code
        logging.debug('sending notifcation to pushover')
        return True if resp == 200 else False
    except:
        logging.warning("error sending notification to %r", user_token)
        return False

def trakt_url():
    turl = "https://api.trakt.tv" + "/shows/%s/?limit=%s" % (listName.lower(), traktLimit)
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
    global tvLibList
    tvLibList = []
    tv_lib_raw = r.json()
    for n in tv_lib_raw:
        tvLibList.append(n['tvdbId'])
    return tvLibList


def get_trakt():
    """get trakt list info"""
    r = requests.get(trakt_url(), headers=traktHeaders)
    global traktList
    traktList = []
    if r.status_code == requests.codes.ok:
        traktList = r.json()
        return True
    else:
        logging.error('Trakt list request failed, is trakt.tv down?')
        return False


def send_to_sonarr(a, b):
    """send found tv program to sonarr"""
    payload = {"tvdbId": a, "title": b, "qualityProfileId": qprofile_lookup(), "seasons": [],
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
    get_trakt()
    sonarr_lib()
    n = 0
    added_list = []
    for x in traktList:
        if x['show']['ids']['tvdb'] not in tvLibList:
            title = x['show']['title']
            tvdb = x['show']['ids']['tvdb']
            try:
                logging.info('send show to sonarr: ' + x['show']['title'])
                send_to_sonarr(tvdb, title)
                if sent:
                    logging.info(title + ' has been added to Sonarr')
                    n += 1
                    added_list.append(x['show']['title'])

                else:
                    logging.warning(title + ' failed to be added to Sonarr!')
            except:
                logging.warning('error sending show: ' + title + ' tvdbid: ' + tvdb)
    if pushover_app_token and pushover_user_token:
        send_pushover(pushover_app_token, pushover_user_token,
                      "The following " + str(n) + " TV Show(s) have been added to Sonarr: " + '\n'.join(added_list))


def new_check():
    """check for new trakt items in list"""
    get_trakt()
    sonarr_lib()
    logging.info('checking for new shows in Trakt list')
    for x in traktList:
        logging.debug('checking show from list: ' + x['show']['title'])
        if x['show']['ids']['tvdb'] not in tvLibList:
            logging.info('new show(s) found, adding shows now')
            add_shows()
            break
    logging.info('no new shows to add, checking again in ' + str(timer) + ' hour(s)')
    time.sleep(float(delay_time))
    logging.debug('sleping for ' + str(delay_time) + ' seconds')
    new_check()
    logging.debug('sleep over, checking again')

new_check()