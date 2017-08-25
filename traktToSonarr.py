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
traktLimit = ''  # how many results to request from trakt's list
listName = ''  # Trending or anticipated
sonarr = 'http://localhost:8989'  # URL to sonarr install, normally localhost:8989
quality_profile = ''  # Sonarr quality profile to add shows under
folder_path = ''  # root folder to download tv shows into
debug_level = 'info' # level of debugging for logs: info, debug, warning and error
add_limit = 0 # limit the number of shows to add per cycle, use 0 for no limit

# Optional pushover notifications
pushover_user_token = ''
pushover_app_token = ''

# Optional tvdb extra filter

tvdb_api = '' # tvdb api key

ended = True # allow the adding of ended shows

# Optional filters
tRatings = '70-100'  # Only return results which have Trakt ratings within set range, e.g. 70-100
tGenres = ''  # Only return results within specified genres, e.g. action, adventure, comedy
tLang = 'en'  # Only return results in set language, e.g en or es
tYears = ''  # Only return results from year, or year range, e.g. 2007 or 2007-2015
tCountries = ''  # Only return results from country, e.g. us
tRuntimes = '30-60'  # Only return results where shows have a runtime within range, e.g. 30-60

################################
# setup
################################

logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s: %(message)s', filename='sonarrPush.log',
                    level=logging.debug_level.upper())
sent = None
newShows = []
delay_time = timer * 3600 
sonarrHeaders = {'X-Api-Key': sonarrAPI}
traktHeaders = {'content-type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': traktAPI, }
tvdbHeaders = {'Authorization': 'Bearer' get_tvdb_token()}
options = {"ignoreEpisodesWithFiles": False, "ignoreEpisodesWithoutFiles": False, "searchForMissingEpisodes": True}


################################
# Main
################################

def get_tvdb_token():
    r = requests.post('https://api.thetvdb.com/login', data={"apikey":"A9FD3F7467C44BB8"})
    token = r.json
    token = r.json[0]['token']
    resp = r.status_code
    return token if resp == 200 else logging.warning('tvdb auth failed, check api key')


def tvdb_status(tvdb_id):
    url = 'https://api.thetvdb.com//series/' + str(tvdb_id)
    header = { "Accept": "application/json", 'Authorization' : 'Bearer ' + get_tvdb_token()"  }
    r = requests.post(url, headers=header})
    output = r.json
    return True if 'Ended' in output[0]['data']['status']


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
    limit = 0
    for x in traktList:
        if x['show']['ids']['tvdb'] not in tvLibList and ended = True:
            title = x['show']['title']
            tvdb = x['show']['ids']['tvdb']
            try:
                logging.info('send show to sonarr: ' + x['show']['title'])
                send_to_sonarr(tvdb, title)
                if sent:
                    logging.info(title + ' has been added to Sonarr')
                    n += 1
                    added_list.append(x['show']['title'])
                    if add_limit > 0 and limit == add_limit:
                        logging.info(str(limit) + ' shows added limit reached')
                        break
                    elif add_limit > 0 and not limit == add_limit:
                        add_limit += 1
                else:
                    logging.warning(title + ' failed to be added to Sonarr!')
            except:
                logging.warning('error sending show: ' + title + ' tvdbid: ' + tvdb)
    if pushover_app_token and pushover_user_token:
        send_pushover(pushover_app_token, pushover_user_token,
                      "The following " + str(n) + " TV Show(s) have been added to Sonarr: " + '\n' + '\n'.join(added_list))


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
    logging.debug('sleping for ' + str(delay_time) + ' seconds')
    time.sleep(float(delay_time))
    logging.debug('sleep over, checking again')
    new_check()

new_check()
