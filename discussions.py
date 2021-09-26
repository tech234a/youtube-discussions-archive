from base64 import b64decode, b64encode
from requests import session
from json import loads, dumps
from time import time, sleep
from sys import argv

from datetime import datetime

#todo: check for accuracy, add/test ratelimit checks if needed, additional language locking (headers)/ gl US

#completed: reply pagination, author hearts, retrieval timestamp, handle no votecount, pinned? - not an option

def getinitialdata(html: str):
    for line in html.splitlines():
        if line.strip().startswith('window["ytInitialData"] = '):
            return loads(line.split('window["ytInitialData"] = ', 1)[1].strip()[:-1])
    return {}

def getapikey(html: str):
    if '"INNERTUBE_API_KEY":"' in html:
        return html.split('"INNERTUBE_API_KEY":"', 1)[-1].split('"', 1)[0]
    else:
        return "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"

#extract latest version automatically
def getlver(initialdata: dict):
    try:
        return initialdata["responseContext"]["serviceTrackingParams"][2]["params"][2]["value"]
    except:
        return "2.20210924.00.00"

def joinruns(runs):
    mys = ""
    for run in runs:
        mys += run["text"]
    return mys

# def joinurls(urls):
#     myl = []
#     for url in urls:
#         myl.append(url["url"])
#     return myl


mysession = session()

#extract latest version automatically
homepage = mysession.get("https://www.youtube.com/").text

API_KEY = getapikey(homepage)

API_VERSION = getlver(getinitialdata(homepage))

# function from coletdjnz https://github.com/coletdjnz/yt-dlp-dev/blob/3ed23d92b524811d9afa3d95358687b083326e58/yt_dlp/extractor/youtube.py#L4392-L4406
def _generate_discussion_continuation(channel_id):
    """
    Generates initial discussion section continuation token from given video id
    """
    ch_id = bytes(channel_id.encode('utf-8'))

    def _generate_secondary_token():
        first = b64decode('EgpkaXNjdXNzaW9uqgM2IiASGA==')
        second = b64decode('KAEwAXgCOAFCEGNvbW1lbnRzLXNlY3Rpb24=')
        return b64encode(first + ch_id + second)

    first = b64decode('4qmFsgJ4Ehg=')
    second = b64decode('Glw=')
    return b64encode(first + ch_id + second + _generate_secondary_token()).decode('utf-8')

def docontinuation(continuation, endpoint="browse"):
    tries = 0
    while True:
        try:
            r = mysession.post("https://www.youtube.com/youtubei/v1/"+endpoint+"?key="+API_KEY, json = {"context":{"client":{"hl":"en","clientName":"WEB","clientVersion":API_VERSION,"timeZone": "UTC"}, "user": {"lockedSafetyMode": False}},"continuation": continuation}, headers={"x-youtube-client-name": "1", "x-youtube-client-version": API_VERSION}, allow_redirects=False)
            #print(r.text)
            #if r.status_code == 200:
            try:
                #open("test2.json", "w").write(r.text)

                myrjson = r.json()
                myrjsonkeys = myrjson.keys()

                if "error" in myrjsonkeys:
                    if "message" in myrjson["error"].keys():
                        print("WARNING: Error from YouTube: \""+myrjson["error"]["message"]+"\"")
                    else:
                        print("WARNING: Error from YouTube, no error message provided")
                elif "onResponseReceivedEndpoints" in myrjsonkeys and r.status_code == 200:
                    return myrjson["onResponseReceivedEndpoints"]
                elif r.status_code != 200:
                    print("WARNING: Non-200 status code received")
                    #print(r.status_code)
                    #print(r.text)
                elif "onResponseReceivedEndpoints" not in myrjsonkeys:
                    print("WARNING: Invalid Response: onResponseReceivedEndpoints missing from response.")
                else:
                    print("WARNING: Other error (type 1)")
            except:
                print("WARNING: Invalid Response: Response is not JSON-formatted")
                
            #else:

        except:
            print("WARNING: Other error (type 2)")
        if tries > 9:
            print("WARNING: 10 failed attempts, aborting")
            return "[fail]"
        tries += 1
        timetosleep = 10 * (2 ** (tries-2)) # 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560 https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
        print("INFO:", datetime.now(), ": Sleeping", timetosleep, "seconds")
        sleep(timetosleep)

def extractcomment(comment, is_reply=False):
    commentroot = {}
    try:
        if not is_reply:
            itemint = comment["commentThreadRenderer"]["comment"]["commentRenderer"]
        else:
            itemint = comment["commentRenderer"]
    except:
        print(comment)

    commentroot["authorText"] = itemint["authorText"]["simpleText"]
    commentroot["authorThumbnail"] = itemint["authorThumbnail"]["thumbnails"][0] #joinurls(itemint["authorThumbnail"]["thumbnails"])
    commentroot["authorEndpoint"] = itemint["authorEndpoint"]["browseEndpoint"]["browseId"]
    commentroot["contentText"] = joinruns(itemint["contentText"]["runs"])
    commentroot["publishedTimeText"] = joinruns(itemint["publishedTimeText"]["runs"]).removesuffix(" (edited)")
    commentroot["creatorHeart"] = "creatorHeart" in itemint["actionButtons"]["commentActionButtonsRenderer"].keys() #accurate enough?
    commentroot["commentId"] = itemint["commentId"]
    commentroot["edited"] = " (edited)" in joinruns(itemint["publishedTimeText"]["runs"]) # hopefully this works for all languages
    #print(commentroot)
    #print(itemint.keys())
    if "voteCount" in itemint.keys():
        commentroot["voteCount"] = int(itemint["voteCount"]["simpleText"].replace(",", ""))
    else:
        #print("NO VOTECOUNT")
        commentroot["voteCount"] = 0

    addcnt = 1
    if not is_reply:
        commentroot["replies"] = []
        if "replies" in comment["commentThreadRenderer"].keys():
            myjrind = docontinuation(comment["commentThreadRenderer"]["replies"]["commentRepliesRenderer"]["contents"][0]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"], "comment/get_comment_replies")
            if myjrind == "[fail]":
                return "fail", 0
            if "continuationItems" in myjrind[0]["appendContinuationItemsAction"].keys():
                myjr = myjrind[0]["appendContinuationItemsAction"]["continuationItems"]
            else:
                print("WARNING: Missing continuationItems key, treating as end of comments.")
                return commentroot, addcnt

            while True:
                for itemr in myjr:
                    if "commentRenderer" in itemr.keys():
                        commentroot["replies"].append(extractcomment(itemr, True)[0])
                        addcnt += 1

                if "continuationItemRenderer" in myjr[-1].keys():
                    myjrin = docontinuation(myjr[-1]["continuationItemRenderer"]["button"]["buttonRenderer"]["command"]["continuationCommand"]["token"], "comment/get_comment_replies")
                    if myjrin == "[fail]":
                        return "fail", 0

                    if "continuationItems" in myjrin[0]["appendContinuationItemsAction"].keys():
                        myjr = myjrin[0]["appendContinuationItemsAction"]["continuationItems"]
                    else:
                        print("WARNING: Missing continuationItems key, treating as end of replies.")
                        break
                    #print(str(commentcnt) + "/" + str(commentscount)+", "+str(100*(commentcnt/commentscount))+"%")
                else:
                    break

    return commentroot, addcnt


def main(channel_id):
    timestamp = time()

    try:
        cont = docontinuation(_generate_discussion_continuation(channel_id))
        if cont == "[fail]":
            return

        if "continuationItems" in cont[1]["reloadContinuationItemsCommand"].keys():
            myj = cont[1]["reloadContinuationItemsCommand"]["continuationItems"]
        else:
            myj = [{}]
            print("WARNING: Missing continuationItems key, treating as end of comments.")
        
    except:
        print("Error in processing response: Are you rate-limited or trying to access a terminated or automatically-generated channel?")
        raise
        return

    commentscount = int(cont[0]["reloadContinuationItemsCommand"]["continuationItems"][0]["commentsHeaderRenderer"]["countText"]["runs"][0]["text"].replace(",", ""))

    print(commentscount)

    comments = []
    commentcnt = 0

    while True:
        for item in myj:
            if "commentThreadRenderer" in item.keys():
                commentfinal, addcnt = extractcomment(item)
                if commentfinal == "fail":
                    return
                comments.append(commentfinal)
                commentcnt += addcnt

        if "continuationItemRenderer" in myj[-1].keys():
            myjino = docontinuation(myj[-1]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"])
            if myj == "[fail]":
                return

            if "continuationItems" in myjino[0]["appendContinuationItemsAction"].keys():
                myj = myjino[0]["appendContinuationItemsAction"]["continuationItems"]
            else:
                print("WARNING: Missing continuationItems key, treating as end of comments.")
                break

            print(str(commentcnt) + "/" + str(commentscount)+", "+str(100*(commentcnt/commentscount))+"%")
        else:
            try:
                print(str(commentcnt) + "/" + str(commentscount)+", "+str(100*(commentcnt/commentscount))+"%")
            except ZeroDivisionError:
                print("0/0, 100.0%")
            break

    if commentcnt != commentscount:
        print("INFO: Number of retrieved comments does not equal expected count. This is a common occurence due to inaccuracies in YouTube's counting system and can safely be ignored in most cases.")

    # minify JSON https://stackoverflow.com/a/33233406
    open(channel_id+".json", "w").write(dumps({"timestamp": timestamp, "comments": comments}, separators=(',', ':')))

    print("Success!")
        

if len(argv) == 2:
    main(argv[1])
else:
    print("""YouTube Discussion Tab Downloader by tech234a
    ***THIS SCRIPT IS EXPERIMENTAL***
    Rate-limit checks are untested. Additionally, further accuracy checks should be performed.
    USAGE: python3 discussions.py [Channel UCID]
    REQUIREMENTS: requests (pip install requests)
    NOTES: Only provide 1 channel UCID at a time. Usernames/channel URLs are not supported.""")
