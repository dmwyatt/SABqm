from datetime import datetime
import json
import os
import re
import shutil
import time
import urllib
import urllib2


def get_queue(url, port, apikey):
    """ Fetches the SABnzbd+ queue.
        url: "http://server/"
        port: 8080
    """
    if url[-1] == "/":
        url = url[:-1]

    url = "%s:%i/sabnzbd/api" % (url, port)

    values={'apikey': apikey,
            'mode': 'queue',
            'output': 'json'}

    data = urllib.urlencode(values)

    req = urllib2.Request(url, data)

    response = urllib2.urlopen(req)
    try:
        queue = json.load(response)
    except:
        import pdb; pdb.set_trace()

    return queue

def queue_ready(url, port, apikey, q_len):
    """ Returns True if queue (data structure returned by get_queue) is short
        enough (specified by q_len) to accept another NZB.
    """
    curr_q_len = len(get_queue(url, port, apikey)['queue']['slots'])

    if curr_q_len < q_len:
        return True
    else:
        return False

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
            #Yes, I'm using a regex instead of properly parsing the XML.
            #I'm so awesome.
            timestamp = int(re.search(r'date="(?P<timestamp>\d{10})"', contents).groups('timestamp')[0])
            nzbs[nzb] = datetime.today() - datetime.fromtimestamp(timestamp)



    else:
        for nzb in nzbs:
            nzbs[nzb] = os.path.getmtime(nzb)

    return sorted(nzbs, key=nzbs.get)[-1]

#--------------CONFIGURE THESE ITEMS--------------------
sab_tv_nzb_blackhole = r"SABs BLACKHOLE DIR HERE"
sb_blackhole = r"SICKBEARDS BLACKHOLE DIR HERE"
url = r"URL FOR SABnzbd+ HERE (e.g. http://server/)"
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
            print "(%s) Moving %s" % (datetime.today(), os.path.basename(nzb))
            shutil.move(nzb, sab_tv_nzb_blackhole)


    time.sleep(sleep_seconds)
