import json
import requests

################ config ################
traktAPI = ''  # API from your trakt account
sonarrAPI = ''  # API from your sonarr install
traktType = 'shows'  # shows or movies
listName = 'anticipated'  # trending, popular or anticipated
sonarr = 'http://localhost:8989'  # url to sonarr install, normaly localhost:8989
########################################

# sonarrUrl = sonarr + '/api/series' + '?apikey=' + sonarrAPI
sonarrHeaders = {'X-Api-Key': sonarrAPI}
traktUrl = "https://api.trakt.tv"
traktHeaders = {'content-type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': traktAPI}


def sonarrLib():
    '''get sonarr library in a list of tvdbid ids'''
    s = requests.get(sonarr + '/api/series', headers=sonarrHeaders)
    return s.json()


def getJson():
    '''get trakt info'''
    r = requests.get(traktUrl + "/%s/%s/" % (traktType, listName), headers=traktHeaders)
    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        print 'Request failed'


def sendToSonarr():
    '''send found tv program to sonarr'''
    requests.post(sonarr + '/api/series', headers=sonarrHeaders,)
                  data={'tvdbId': tvdbId, 'title': title, 'qualityProfileId': '', 'titleSlug': slug, 'images': '',
                        'seasons': ''})


# Turn sonarr library json info into list
tvLibJson = sonarrLib()
tvLibList = []
for n in tvLibJson:
    tvLibList.append(n['tvdbId'])

# Check new shows & add missing
data = getJson()
for x in data:
    if x['show']['ids']['tvdb'] in tvLibList:
        pass
    else:
        title = x['show']['title']
        tvdbId = x['show']['ids']['tvdb']
        slug = x['show']['ids']['slug']
        sendToSonarr(tvdbId, title, qualityProfileId, titleSlug, images, seasons)
