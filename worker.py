# Let's remind people who still have this running to shut it down
from os.path import isfile
from json import loads
from os import environ
import requests
from sys import exit

if "TRACKER_USERNAME" in environ.keys():
    TRACKER_USERNAME = environ["TRACKER_USERNAME"]
elif isfile("config.json"):
    try:
        TRACKER_USERNAME = loads(open("config.json").read())["TRACKER_USERNAME"]
    except:
        TRACKER_USERNAME = "Unnamed"
else:
    TRACKER_USERNAME = "Unnamed"

from threading import Thread
import requests
from time import sleep
from os import mkdir, rmdir, listdir, system, environ
from os.path import isdir, isfile, getsize
from json import loads
import signal
import tracker
from shutil import rmtree, which
from queue import Queue
from gc import collect

from discussions import main as discussion_pull

# useful Queue example: https://stackoverflow.com/a/54658363
jobs = Queue()

try:
    mkdir("out")
except:
    pass

try:
    mkdir("directory")
except:
    pass

HEROKU = False
if isfile("../Procfile"):
    HEROKU = True

assert which("zip") and which("rsync") and which(
    "curl"), "Please ensure the zip, rsync, and curl commands are installed on your system."



# Graceful Shutdown
class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print("Graceful exit process initiated, no longer accepting new tasks but finishing existing ones...")
        self.kill_now = True


gkiller = GracefulKiller()


# microtasks
def threadrunner():
    jobs = Queue()
    while True:
        if not jobs.empty():
            task, vid, args = jobs.get()
            if task == "submitdiscovery":
                tracker.add_item_to_tracker(args, vid)
            elif task == "channel":
                channel_id = desit.split(":", 1)[1]
                try:
                    result = discussion_pull(channel_id)
                    if not result:
                        raise Exception
                    jobs.put(("complete", None, "channel:" + args))
                except:  # TODO
                    print("Error while grabbing discussions. Ignoring and not marking as complete... " + channel_id)

            elif task == "complete":
                size = 0
                # TODO
                if ":" in args:
                    if args.split(":", 1)[0] == "channel":
                        # check if dir is empty, make zip if needed
                        if isdir("out/" + args.split(":", 1)[1]):
                            if not listdir("out/" + args.split(":", 1)[1]):
                                rmdir("out/" + args.split(":", 1)[1])
                            else:
                                # zip it up
                                if not isdir("directory/" + args.split(":", 1)[1]):
                                    mkdir("directory/" + args.split(":", 1)[1])

                                while not isfile(
                                        "directory/" + args.split(":", 1)[1] + "/" + args.split(":", 1)[1] + ".zip"):
                                    print("Attempting to zip item...")
                                    system("zip -9 -r -j directory/" + args.split(":", 1)[1] + "/" + args.split(":", 1)[
                                        1] + ".zip out/" + args.split(":", 1)[1])

                                # get a target
                                targetloc = None
                                while not targetloc:
                                    targetloc = tracker.request_upload_target()
                                    if targetloc:
                                        break
                                    else:
                                        print("Waiting 5 minutes...")
                                        sleep(300)

                                while True:
                                    if targetloc.startswith("rsync"):
                                        exitinfo = system(
                                            "rsync -rltv --timeout=300 --contimeout=300 --progress --bwlimit 0 --recursive --partial --partial-dir .rsync-tmp --min-size 1 --no-compress --compress-level 0 directory/" +
                                            args.split(":", 1)[1] + "/ " + targetloc)
                                    elif targetloc.startswith("http"):
                                        exitinfo = system("curl -F " + args.split(":", 1)[1] + ".zip=@directory/" +
                                                          args.split(":", 1)[1] + "/" + args.split(":", 1)[
                                                              1] + ".zip " + targetloc)

                                    if exitinfo == 0:  # note that on Unix this isn't necessarily the exit code but it's still 0 upon successful exit
                                        break
                                    else:
                                        print("Error in sending data to target, waiting 30 seconds and trying again.")
                                        sleep(30)

                                size = getsize(
                                    "directory/" + args.split(":", 1)[1] + "/" + args.split(":", 1)[1] + ".zip")
                                # cleanup
                                try:
                                    rmtree("directory/" + args.split(":", 1)[1] + "/")
                                    rmdir("directory/" + args.split(":", 1)[1] + "/")
                                    rmtree("out/" + args.split(":", 1)[1] + "/")
                                    rmdir("out/" + args.split(":", 1)[1] + "/")
                                except:
                                    pass
                tracker.mark_item_as_done(args, size)
            jobs.task_done()
        else:
            if not gkiller.kill_now:
                # get a new task from tracker
                collect()  # cleanup

                desit = tracker.request_item_from_tracker()
                print("New task:", desit)

                if desit:
                    if desit.split(":", 1)[0] == "channel":
                        jobs.put(("channel", None, desit.split(":", 1)[1]))
                    else:
                        print("Ignoring item for now", desit)
                else:
                    print("Ignoring item for now", desit)
            else:
                break


threads = []

THREADCNT = 50
if HEROKU:
    THREADCNT = 20
# now create the rest of the threads
for i in range(THREADCNT):
    runthread = Thread(target=threadrunner)
    runthread.start()
    threads.append(runthread)
    del runthread

# https://stackoverflow.com/a/11968881
for x in threads:
    x.join()
    threads.remove(x)
    del x

print("Exiting...")