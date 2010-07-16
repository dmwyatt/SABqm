from datetime import datetime
import json
import os
import re
import shutil
import time
import urllib
import urllib2

def sab_api(url, port, values, apikey):
    url = "%s:%i/sabnzbd/api" % (url, port)

    values['apikey'] = apikey

    data = urllib.urlencode(values)
    req = urllib2.Request(url, data)
    response = urllib2.urlopen(req)
    the_response = response.read()

    return the_response

def get_queue(url, port, apikey):
    """ Fetches the SABnzbd+ queue.
        url: "http://server/"
        port: 8080
    """

    values={
            'mode': 'queue',
            'output': 'json'}
    try:
        queue = json.loads(sab_api(url, port, values, apikey))
    except ValueError:
        screen_log("Invalid api response from SABnzbd+")
        raise

    return queue

def sab_available(url, port, apikey):
    values={
            'mode': 'version',
            'output': 'json'}

    count = 0
    while 1:
        try:
            return json.loads(sab_api(url, port, values, apikey))
        except:
            #If SABnzbd+ is unresponsive, wait 5 seconds and try again
            screen_log("SABnzbd+ unresponsive, waiting 5 seconds (%i retries)" % count)
            count += 1
            time.sleep(5)

def queue_ready(url, port, apikey, q_len):
    """ Returns True if queue (data structure returned by get_queue) is short
        enough (specified by q_len) to accept another NZB.
    """
    count = 0

    if sab_available(url, port, apikey):
        curr_q_len = len(get_queue(url, port, apikey)['queue']['slots'])

    if curr_q_len < q_len:
        return True
    else:
        return False

def screen_log(msg):
    print "(%s) %s" % (datetime.today(), msg)

def get_nzb(directory, usenet_age_sort = False):
    """ Returns path to an NZB from directory.
        If usenet_age_sort is False we return the NZB downloaded longest ago. If
        usenet_age_sort is True we return the NZB that was posted to usenet longest ago

        TODO:  Persist ages so we don't have to get them all each time.
    """

    #get list of nzbs
    nzbs = {}
    for root, dirs, files in os.walk(directory):
        for f in files:
            p = os.path.join(root, f)
            if os.path.splitext(p)[1].lower() == ".nzb":
                nzbs[p] = None

    if not len(nzbs):
        return

    if usenet_age_sort:
        for nzb in nzbs:
            f = open(nzb, 'r')
            contents = f.read()
            f.close()
            #Yes, I'm using a regex instead of properly parsing the XML.
            #I'm so awesome.
            timestamp = int(re.search(r'date="(?P<timestamp>\d{10})"', contents).groups('timestamp')[0])
            nzbs[nzb] = datetime.today() - datetime.fromtimestamp(timestamp)

    else:
        for nzb in nzbs:
            nzbs[nzb] = os.path.getmtime(nzb)

    return sorted(nzbs, key=nzbs.get)[0]

def sab_add_by_path(url, port, apikey, path, category):

    values = {'mode': 'addlocalfile',
              'name': path,
              'cat': category}

    response = sab_api(url, port, values, apikey)

    if response.strip() != 'ok':
        raise ValueError("Failed to add %s" % path)

    return response.strip()

#--------------CONFIGURE THESE ITEMS--------------------
sab_category = 'tv'
sb_blackhole = r"SICKBEARDS BLACKHOLE DIR HERE"
url = r"URL FOR SABnzbd+ HERE (e.g. http://server)"
port = 8080
apikey = "SABnzbd+ APIKEY HERE"

#seconds between checks of the sickbeard blackhole directory and SABnzbd+ queue
sleep_seconds = 10

#maximum length you want your SABnzbd+ queue to be
q_length = 2
#--------------STOP CONFIGURING-------------------------


while 1:
    if queue_ready(url, port, apikey, q_length):
        nzb = get_nzb(sb_blackhole, usenet_age_sort = False)
        if nzb:
            screen_log("Adding %s" % os.path.basename(nzb))
            try:
                screen_log(sab_add_by_path(url, port, apikey, nzb, sab_category))

                #keep trying to delete the nzb for ~60 seconds giving SAB time to retrieve it
                for i in range(60):
                    try:
                        os.remove(nzb)
                        break
                    except:
                        time.sleep(1)
            except:
                screen_log("failed to add %s" % os.path.basename(nzb))
                shutil.move(nzb, nzb + ".fail")

    time.sleep(sleep_seconds)
