from base64 import b64decode, b64encode

import requests
from requests import session
from json import loads, dumps
from time import time, sleep
from sys import argv

from datetime import datetime

#todo: check for accuracy, add/test ratelimit checks if needed, additional language locking (headers)/ gl US

#completed: reply pagination, author hearts, retrieval timestamp, handle no votecount, pinned? - not an option

def approxnumtoint(num: str):
    if num[-1] == "K":
        print(num)
        print(int(float(num[:-1].replace(",", ""))*1000))
        return int(float(num[:-1].replace(",", ""))*1000)
    if num[-1] == "M":
        print(num)
        print(int(float(num[:-1].replace(",", ""))*1000000))
        return int(float(num[:-1].replace(",", ""))*1000000)
    return int(num.replace(",", ""))

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
    #print(continuation)
    #print(endpoint)
    tries = 0
    while True:
        try:
            r = mysession.post("https://www.youtube.com/youtubei/v1/"+endpoint+"?key="+API_KEY, json = {"context":{"client":{"hl":"en","clientName":"WEB","clientVersion":API_VERSION,"timeZone": "UTC"}, "user": {"lockedSafetyMode": False}},"continuation": continuation}, headers={"x-youtube-client-name": "1", "x-youtube-client-version": API_VERSION}, allow_redirects=False)
            #print(r.status_code)
            #print(r.text)
            #if r.status_code == 200:
            try:
                #open("test2.json", "w").write(r.text)

                myrjson = r.json()
                myrjsonkeys = myrjson.keys()

                if "error" in myrjsonkeys:
                    if "message" in myrjson["error"].keys():
                        print("WARNING: Error from YouTube: \""+myrjson["error"]["message"]+"\"")
                        if (myrjson["error"]["message"] == "Requested entity was not found." and r.status_code == 404) or (myrjson["error"]["message"] == "The caller does not have permission" and r.status_code == 403):
                            if endpoint == "comment/get_comment_replies":
                                print("INFO: Treating as end of replies.")
                                return [{"appendContinuationItemsAction": {"continuationItems" : [{}]}}]
                            elif endpoint == "browse":
                                print("INFO: Treating as end of comments.")
                                return [{"reloadContinuationItemsCommand": {"continuationItems" : [{}]}}]
                    else:
                        print("WARNING: Error from YouTube, no error message provided")
                elif "contents" in myrjsonkeys:
                    print("WARNING: contents key detected in response, which indicates that we have not received discussion tab data. Retrieving discussion tab data for this channel is likely not possible. This error typically occurs on automatically-generated YouTube channels. Aborting.")
                    return "[fail]"
                elif "continuationContents" in myrjsonkeys:
                    print("WARNING: continuationContents key detected in response, which indicates that we have not received discussion tab data. Retrieving discussion tab data for this channel is likely not possible. This error typically occurs on automatically-generated YouTube channels. Aborting.")
                    return "[fail]"
                elif "onResponseReceivedEndpoints" in myrjsonkeys and r.status_code == 200:
                    return myrjson["onResponseReceivedEndpoints"]
                elif r.status_code == 404:
                    print("WARNING: 404 status code retrieved, aborting.")
                    return "[fail]"
                elif r.status_code != 200:
                    print("WARNING: Non-200 status code received")
                    #print(r.status_code)
                    #print(r.text)
                elif "onResponseReceivedEndpoints" not in myrjsonkeys:
                    print("WARNING: Invalid Response: onResponseReceivedEndpoints missing from response.")
                else:
                    print("WARNING: Other error (type 1)")
            except (IndexError, KeyError, AttributeError, TypeError):
                print("WARNING: Invalid Response: Response is not JSON-formatted")
        except requests.exceptions.RequestException as e:
            print("WARNING: Other error: " + str(e))
        if tries > 5:
            print("WARNING: 5 failed attempts, aborting")
            return "[fail]"
        tries += 1
        timetosleep = 10 * (2 ** (tries-2)) # 5, 10, 20, 40, 80, 160, 320, 640, 1280, 2560 https://findwork.dev/blog/advanced-usage-python-requests-timeouts-retries-hooks/
        print("INFO:", datetime.now(), ": Sleeping", timetosleep, "seconds")
        sleep(timetosleep)

def extractcomment(comment, is_reply=False):
    comment_channel_ids = set()
    commentroot = {}
    try:
        if not is_reply:
            itemint = comment["commentThreadRenderer"]["comment"]["commentRenderer"]
        else:
            itemint = comment["commentRenderer"]
    except:
        print(comment)

    if "simpleText" in itemint["authorText"].keys():
        commentroot["authorText"] = itemint["authorText"]["simpleText"]
    else:
        print("WARNING: Author name not provided, setting to blank.")
        commentroot["authorText"] = ""
    commentroot["authorThumbnail"] = itemint["authorThumbnail"]["thumbnails"][0]["url"] #joinurls(itemint["authorThumbnail"]["thumbnails"])
    if "browseId" in itemint["authorEndpoint"]["browseEndpoint"].keys():
        commentroot["authorEndpoint"] = itemint["authorEndpoint"]["browseEndpoint"]["browseId"]
        comment_channel_ids.add(commentroot["authorEndpoint"])
    else:
        print("WARNING: Author UCID not provided, setting to blank.")
        commentroot["authorEndpoint"] = ""
    if "runs" in itemint["contentText"].keys():
        commentroot["contentText"] = joinruns(itemint["contentText"]["runs"])
    else:
        print("WARNING: Missing contentText runs, setting to blank.")
        commentroot["contentText"] = ""
    commentroot["publishedTimeText"] = joinruns(itemint["publishedTimeText"]["runs"]).removesuffix(" (edited)")
    commentroot["creatorHeart"] = "creatorHeart" in itemint["actionButtons"]["commentActionButtonsRenderer"].keys() #accurate enough?
    commentroot["commentId"] = itemint["commentId"]
    commentroot["edited"] = " (edited)" in joinruns(itemint["publishedTimeText"]["runs"]) # hopefully this works for all languages
    #print(commentroot)
    #print(itemint.keys())
    if "voteCount" in itemint.keys():
        commentroot["voteCount"] = approxnumtoint(itemint["voteCount"]["simpleText"])
    else:
        #print("NO VOTECOUNT")
        commentroot["voteCount"] = 0

    addcnt = 1
    if not is_reply:
        commentroot["replies"] = []
        if "replies" in comment["commentThreadRenderer"].keys():
            creplycntruns = comment["commentThreadRenderer"]["replies"]["commentRepliesRenderer"]["viewReplies"]["buttonRenderer"]["text"]["runs"]
            if len(creplycntruns) == 2 or len(creplycntruns) == 1:
                commentroot["expected_replies"] = 1
            else:
                commentroot["expected_replies"] = int(creplycntruns[1]["text"])
            myjrind = docontinuation(comment["commentThreadRenderer"]["replies"]["commentRepliesRenderer"]["contents"][0]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"], "comment/get_comment_replies")
            if myjrind == "[fail]":
                return "fail", 0, comment_channel_ids
            if "continuationItems" in myjrind[0]["appendContinuationItemsAction"].keys():
                myjr = myjrind[0]["appendContinuationItemsAction"]["continuationItems"]
            else:
                print("WARNING: Missing continuationItems key, treating as end of comments.")
                return commentroot, addcnt, comment_channel_ids

            while True:
                for itemr in myjr:
                    if "commentRenderer" in itemr.keys():
                        reply, _, reply_channel_ids = extractcomment(itemr, True)
                        commentroot["replies"].append(reply)
                        comment_channel_ids.update(reply_channel_ids)
                        addcnt += 1

                if "continuationItemRenderer" in myjr[-1].keys():
                    myjrin = docontinuation(myjr[-1]["continuationItemRenderer"]["button"]["buttonRenderer"]["command"]["continuationCommand"]["token"], "comment/get_comment_replies")
                    if myjrin == "[fail]":
                        return "fail", 0, comment_channel_ids

                    if "continuationItems" in myjrin[0]["appendContinuationItemsAction"].keys():
                        myjr = myjrin[0]["appendContinuationItemsAction"]["continuationItems"]
                    else:
                        print("WARNING: Missing continuationItems key, treating as end of replies.")
                        break
                    #print(str(commentcnt) + "/" + str(commentscount)+", "+str(100*(commentcnt/commentscount))+"%")
                else:
                    break
        else:
            commentroot["expected_replies"] = 0

        if len(commentroot["replies"]) != commentroot["expected_replies"]:
            print("WARNING: Number of retrieved replies does not equal number of expected replies.")

    return commentroot, addcnt, comment_channel_ids


def main(channel_id):
    timestamp = time()

    try:
        cont = docontinuation(_generate_discussion_continuation(channel_id))
        if cont == "[fail]":
            return False, set()

        if "continuationItems" in cont[1]["reloadContinuationItemsCommand"].keys():
            myj = cont[1]["reloadContinuationItemsCommand"]["continuationItems"]
        else:
            myj = [{}]
            print("WARNING: Missing continuationItems key, treating as end of comments.")
        
    except:
        print("Error in processing response: Are you rate-limited or trying to access a terminated or automatically-generated channel?")
        raise

    commentscount = int(cont[0]["reloadContinuationItemsCommand"]["continuationItems"][0]["commentsHeaderRenderer"]["countText"]["runs"][0]["text"].replace(",", ""))

    print(commentscount)

    comments = []
    commentcnt = 0
    channel_ids = set()
    while True:
        for item in myj:
            if "commentThreadRenderer" in item.keys():
                commentfinal, addcnt, comment_channel_ids = extractcomment(item)
                if commentfinal == "fail":
                    return False, set()
                comments.append(commentfinal)
                channel_ids.update(comment_channel_ids)
                commentcnt += addcnt

        if "continuationItemRenderer" in myj[-1].keys():
            myjino = docontinuation(myj[-1]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"])
            if myj == "[fail]":
                return False, set()

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
    open(channel_id+".json", "w").write(dumps({"UCID": channel_id, "expected_count": commentscount, "timestamp": timestamp, "comments": comments}, separators=(',', ':')))

    print("Success!")
    return True, channel_ids
        

if len(argv) == 2:
    res = main(argv[1])
    print(res)
else:
    print("""YouTube Discussion Tab Downloader by tech234a
    ***THIS SCRIPT IS EXPERIMENTAL***
    Rate-limit checks are untested. Additionally, further accuracy checks should be performed.
    USAGE: python3 discussions.py [Channel UCID]
    REQUIREMENTS: requests (pip install requests)
    NOTES: Only provide 1 channel UCID at a time. Usernames/channel URLs are not supported.""")
