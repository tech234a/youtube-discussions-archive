import base64
from requests import session
from json import loads, dumps
from time import time
from sys import argv

#todo: reply pagination, check for accuracy, add ratelimit checks if needed, additional language locking (headers)/ gl US
#data questions: add author URLs, simplify profile picture URLs

#completed: author hearts, retrieval timestamp, handle no votecount, pinned? - not an option

def getinitialdata(html: str):
    for line in html.splitlines():
        if line.strip().startswith('window["ytInitialData"] = '):
            return loads(line.split('window["ytInitialData"] = ', 1)[1].strip()[:-1])
    return {}

def getapikey(html: str):
    return html.split('"INNERTUBE_API_KEY":"', 1)[-1].split('"', 1)[0]

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

def joinurls(urls):
    myl = []
    for url in urls:
        myl.append(url["url"])
    return myl

mysession = session()

#extract latest version automatically
homepage = mysession.get("https://www.youtube.com/").text

API_KEY = getapikey(homepage)

params = (
    ('key', API_KEY),
)

API_VERSION = getlver(getinitialdata(homepage))

# function from coletdjnz https://github.com/coletdjnz/yt-dlp-dev/blob/3ed23d92b524811d9afa3d95358687b083326e58/yt_dlp/extractor/youtube.py#L4392-L4406
def _generate_discussion_continuation(channel_id):
    """
    Generates initial discussion section continuation token from given video id
    """
    ch_id = bytes(channel_id.encode('utf-8'))

    def _generate_secondary_token():
        first = base64.b64decode('EgpkaXNjdXNzaW9uqgM2IiASGA==')
        second = base64.b64decode('KAEwAXgCOAFCEGNvbW1lbnRzLXNlY3Rpb24=')
        return base64.b64encode(first + ch_id + second)

    first = base64.b64decode('4qmFsgJ4Ehg=')
    second = base64.b64decode('Glw=')
    return base64.b64encode(first + ch_id + second + _generate_secondary_token()).decode('utf-8')

def docontinuation(continuation, endpoint="browse"):
    r = mysession.post("https://www.youtube.com/youtubei/v1/"+endpoint+"?key="+API_KEY, json = {"context":{"client":{"hl":"en","clientName":"WEB","clientVersion":API_VERSION,"timeZone": "UTC"}, "user": {"lockedSafetyMode": False}},"continuation": continuation}, headers={"x-youtube-client-name": "1", "x-youtube-client-version": API_VERSION})

    #open("test2.json", "w").write(r.text)

    return r.json()["onResponseReceivedEndpoints"]

def extractcomment(comment, is_reply=False):
    commentroot = {}
    if not is_reply:
        itemint = comment["commentThreadRenderer"]["comment"]["commentRenderer"]
    else:
        itemint = comment["commentRenderer"]

    commentroot["authorText"] = itemint["authorText"]["simpleText"]
    commentroot["authorThumbnail"] = joinurls(itemint["authorThumbnail"]["thumbnails"])
    commentroot["authorEndpoint"] = itemint["authorEndpoint"]["browseEndpoint"]["browseId"]
    commentroot["contentText"] = joinruns(itemint["contentText"]["runs"])
    commentroot["publishedTimeText"] = joinruns(itemint["publishedTimeText"]["runs"])
    commentroot["creatorHeart"] = "creatorHeart" in itemint["actionButtons"]["commentActionButtonsRenderer"].keys() #accurate enough?
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
            myjr = docontinuation(comment["commentThreadRenderer"]["replies"]["commentRepliesRenderer"]["contents"][0]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"], "comment/get_comment_replies")[0]["appendContinuationItemsAction"]["continuationItems"]
            for itemr in myjr:
                commentroot["replies"].append(extractcomment(itemr, True)[0])
                addcnt += 1

    return commentroot, addcnt


def main(channel_id):
    timestamp = time()

    cont = docontinuation(_generate_discussion_continuation(channel_id))

    myj = cont[1]["reloadContinuationItemsCommand"]["continuationItems"]

    commentscount = int(cont[0]["reloadContinuationItemsCommand"]["continuationItems"][0]["commentsHeaderRenderer"]["countText"]["runs"][0]["text"].replace(",", ""))

    print(commentscount)

    comments = []
    commentcnt = 0

    while True:
        for item in myj:
            if "commentThreadRenderer" in item.keys():
                commentfinal, addcnt = extractcomment(item)
                comments.append(commentfinal)
                commentcnt += addcnt

        if "continuationItemRenderer" in myj[-1].keys():
            myj = docontinuation(item["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"])[0]["appendContinuationItemsAction"]["continuationItems"]
            print(str(commentcnt) + "/" + str(commentscount)+", "+str(100*(commentcnt/commentscount))+"%")
        else:
            break


    open(channel_id+".json", "w").write(dumps({"timestamp": timestamp, "comments": comments}))

    print("Success!")

if len(argv) == 2:
    main(argv[1])
else:
    print("""YouTube Discussion Tab Downloader by tech234a
    ***THIS SCRIPT IS EXPERIMENTAL***
    Reply pagination is not yet implemented, nor are rate-limit checks. Additionally, further accuracy checks should be performed.
    USAGE: python3 discussions.py [Channel UCID]
    REQUIREMENTS: requests (pip install requests)
    NOTES: Only provide 1 channel UCID at a time. Usernames/channel URLs are not supported.""")
