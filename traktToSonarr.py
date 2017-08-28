# TODO Add config for debug level
# TODO Merge trakt type lists into one global list based on config options
# TODO Add log rotate
# TODO Add user response based config generation on first run (low priority)

import json
import requests
import time
import logging
import sys
import os   

from logging.handlers import RotatingFileHandler

################################
# config
################################

timer = 0  # how often (in hours) to check for new shows and add them - use 0 to only check once
traktAPI = os.environ["trakt_api"]
sonarrAPI = os.environ["sonarr_api"]
traktLimit = '50'  # how many results to request from trakt's list
listName = os.environ["trakt_type"]
sonarr = 'http://localhost:8989/sonarr'  # URL to sonarr install, normally localhost:8989 or localhost:8989/sonarr
quality_profile = 'HD - 720p/1080p'  # Sonarr quality profile to add shows under
folder_path = '/plexmedia/media/TV Shows/'  # root folder to download tv shows into, make sure to leave trailing / e.g /home/user/media/tv/
add_limit = os.environ["dailylimit"]
log_level = 'info'  # set log and console output to debug or info

# Optional pushover notifications
pushover_user_token = ''
pushover_app_token = ''

# Optional Slack Webhook Integration

slack_webhook_url = os.environ["webhook"]
slack_user = 'bot'  # can be anything you like
slack_channel = 'sonarr_pusher'  # can be anything you like (sonarr_pusher)

# Optional tvdb extra filter

tvdb_api = ''  # tvdb api key

allow_ended = True  # allow the adding of ended shows

# Optional filters
tRatings = ''  # Only return results which have Trakt ratings within set range, e.g. 70-100
tGenres = ''  # Only return results within specified genres, e.g. action, adventure, comedy
tLang = 'en'  # Only return results in set language, e.g en or es
tYears = ''  # Only return results from year, or year range, e.g. 2007 or 2007-2015
tCountries = 'us'  # Only return results from country, e.g. us
tRuntimes = ''  # Only return results where shows have a runtime within range, e.g. 30-60

################################
# setup
################################

sent = None
newShows = []
delay_time = timer * 3600
sonarrHeaders = {'X-Api-Key': sonarrAPI}
traktHeaders = {'content-type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': traktAPI, }
options = {"ignoreEpisodesWithFiles": False, "ignoreEpisodesWithoutFiles": False, "searchForMissingEpisodes": True}
tvLibList = []
traktList = []
num = 0

################################
# Logging
################################


logging.basicConfig(stream=sys.stdout, format='%(asctime)s - %(levelname)s: %(message)s')

logger = logging.getLogger("Rotating Log")
consoleHandler = logging.StreamHandler()

handler = RotatingFileHandler('sonarrPush.log', maxBytes=1024 * 1024 * 2, backupCount=1)
logger.addHandler(handler)

if log_level.lower() == 'info':
    logger.setLevel(logging.INFO)
    consoleHandler.setLevel(logging.INFO)
elif log_level.lower() == 'debug':
    logger.setLevel(logging.DEBUG)
    consoleHandler.setLevel(logging.DEBUG)

consoleHandler = logging.StreamHandler()


################################
# Main
################################


def get_tvdb_token():
    """
    Grab token for tvdb api auth
    """
    x = {"apikey": "A9FD3F7467C44BB8"}
    r = requests.post('https://api.thetvdb.com/login', headers={'Content-Type': 'application/json'}, data=json.dumps(x))
    token = r.json()
    token = token['token']
    resp = r.status_code
    return token if resp == 200 else logger.warning('tvdb auth failed, check api key')


def tvdb_status(tvdb_id):
    """
    Check if a tv show is still being aired
    """
    url = 'https://api.thetvdb.com//series/' + str(tvdb_id)
    header = {"Accept": "application/json", "Authorization": "Bearer " + get_tvdb_token(), }
    r = requests.post(url, headers=header)
    output = r.json()
    logger.debug('checked tvdb if show is still airing, status code: ' + str(r.status_code))
    return True if 'Ended' in output['data']['status'] else logger.info('Show is still being aired, continue to add')


def send_pushover(app_token, user_token, message):
    """
    Send message to pushover client
    """
    try:
        payload = {'token': app_token, 'user': user_token, 'title': 'Sonarr Push', 'message': message}
        r = requests.post('https://api.pushover.net/1/messages.json', data=payload, headers={'User-Agent': 'Python'})
        resp = r.status_code
        logger.debug('sending notifcation to pushover')
        return True if resp == 200 else False
    except:
        logger.warning("error sending notification to %r", user_token)
        return False


def trakt_url():
    """
    Generate the url for trakt api with filters as needed
    """
    url = "https://api.trakt.tv" + "/shows/%s/?limit=%s" % (listName.lower(), traktLimit)
    if tRatings:
        url += '&ratings=' + tRatings
    if tGenres:
        url += '&genres=' + tGenres.lower()
    if tLang:
        url += '&languages=' + tLang.lower()
    if tYears:
        url += '&years=' + tYears.lower()
    if tCountries:
        url += '&countries=' + tCountries.lower()
    if tRuntimes:
        url += '&runtimes=' + tRuntimes
    return url


def qprofile_lookup():
    """
    Check sonarr quality profile ID
    """
    r = requests.get(sonarr + '/api/profile', headers=sonarrHeaders)
    qprofile_id = r.json()
    x = 0
    for _ in qprofile_id:
        if qprofile_id[x]['name'].lower() == quality_profile.lower():
            return qprofile_id[x]['id']
        else:
            x += 1


def sonarr_lib():
    """
    Get sonarr library in a list of tvdbid ids
    """
    r = requests.get(sonarr + '/api/series', headers=sonarrHeaders)
    global tvLibList
    tv_lib_raw = r.json()
    for n in tv_lib_raw:
        tvLibList.append(n['tvdbId'])
    return tvLibList


def get_trakt():
    """
    Get trakt list info
    """
    r = requests.get(trakt_url(), headers=traktHeaders)
    global traktList
    traktList = []
    if r.status_code == requests.codes.ok:
        traktList = r.json()
        logger.debug('got trakt list successfully')
        return True
    else:
        logger.error('Trakt list request failed, is trakt.tv down?')
        logger.debug('failed to get trakt list, code return: ' + r.status_code)
        return False


def send_to_sonarr(a, b):
    """
    Send found tv program to sonarr
    """
    payload = {"tvdbId": a, "title": b, "qualityProfileId": qprofile_lookup(), "seasons": [], "seasonFolder": True,
               "rootFolderPath": folder_path, "addOptions": options, "images": []}
    r = requests.post(sonarr + '/api/series', headers=sonarrHeaders, data=json.dumps(payload))
    global sent
    sent = payload
    if r.status_code == 201:
        sent = True
        logger.debug('sent to sonarr successfully')
    else:
        sent = False
        logger.debug('failed to send to sonarr, code return: ' + r.status_code)
    return sent


def num_to_add():
    """
    Return how many shows are to be added outside of limit
    """
    n = 0
    for x in traktList:
        if x['show']['ids']['tvdb'] not in tvLibList and allow_ended:
            n += 1
        elif x['show']['ids']['tvdb'] not in tvLibList and tvdb_status(x['show']['ids']['tvdb']):
            n += 1
    global num
    num = n
    return n


def add_shows():
    """
    Check new shows & add missing
    """
    get_trakt()
    sonarr_lib()
    num_to_add()
    n = 0
    added_list = []
    global add_limit
    y = add_limit
    for x in traktList:
        if x['show']['ids']['tvdb'] not in tvLibList and allow_ended:
            title = x['show']['title']
            tvdb = x['show']['ids']['tvdb']
            try:
                logger.info('send show to sonarr: ' + x['show']['title'])
                send_to_sonarr(tvdb, title)
                if sent:
                    logger.info(title + ' has been added to Sonarr')
                    n += 1
                    added_list.append(x['show']['title'])
                    if 0 < y == n:
                        logger.info(str(n) + ' shows added limit reached')
                        break
                    elif y > 0 and not n == y:
                        logger.debug('limit not yet reached: ' + str(n))
                else:
                    logger.warning(title + ' failed to be added to Sonarr!')
            except:
                logger.warning('error sending show: ' + title + ' tvdbid: ' + str(tvdb))
        elif x['show']['ids']['tvdb'] not in tvLibList and not tvdb_status(x['show']['ids']['tvdb']):
            title = x['show']['title']
            tvdb = x['show']['ids']['tvdb']
            logger.debug('adding shows if not ended ' + title + ' ' + str(tvdb_status(x['show']['ids']['tvdb'])))
            try:
                logger.info('send show to sonarr: ' + x['show']['title'])
                send_to_sonarr(tvdb, title)
                if sent:
                    logger.info(title + ' has been added to Sonarr')
                    n += 1
                    added_list.append(x['show']['title'])
                    if 0 < y == n:
                        logger.info(str(n) + ' shows added limit reached')
                        break
                    elif y > 0 and not n == y:
                        logger.debug('limit not yet reached: ' + str(n))
                else:
                    logger.warning(title + ' failed to be added to Sonarr!')
            except:
                logger.warning('error sending show: ' + title + ' tvdbid: ' + str(tvdb))
    if pushover_app_token and pushover_user_token and n != 0:
        send_pushover(pushover_app_token, pushover_user_token, "The following " + str(n) + " TV Show(s) out of " + str(
            num) + " have been added to Sonarr: " + '\n' + '\n'.join(added_list))
    if slack_webhook_url and n != 0:
        slack_data = "The following " + str(n) + " " + listName + " TV Show(s) out of " + str(
            num) + " have been added to Sonarr: " + '\n' + '\n'.join(added_list)
        payload = {"text": slack_data, "username": slack_user, "channel": slack_channel}
        requests.post(slack_webhook_url, json.dumps(payload), headers={'content-type': 'application/json'})


def new_check():
    """
    Check for new trakt items in list
    """
    get_trakt()
    sonarr_lib()
    logger.info('checking for new shows in Trakt list')
    for x in traktList:
        logger.debug('checking show from list: ' + x['show']['title'])
        if x['show']['ids']['tvdb'] not in tvLibList and allow_ended:
            logger.info('new show(s) found, adding shows now')
            add_shows()
            break
        elif x['show']['ids']['tvdb'] not in tvLibList and not tvdb_status(x['show']['ids']['tvdb']):
            logger.info('new continuing show(s) found, adding shows now')
            add_shows()
            break
    if timer != 0:
        logger.info('no new shows to add, checking again in ' + str(timer) + ' hour(s)')
        logger.debug('sleping for ' + str(delay_time) + ' seconds')
        time.sleep(float(delay_time))
        logger.debug('sleep over, checking again')
        new_check()
    else:
        logger.info('nothing left to add, shutting down')
        sys.exit()

new_check()
