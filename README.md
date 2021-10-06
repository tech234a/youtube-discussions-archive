# YouTube Discussion  Archiving Worker
Worker for the `Save Discussions` project: Archiving YouTube channel discussions

## Current Stats
See how much has been archived so far.


## Setup

## Primary Usage

### Heroku⭐️⭐️⭐️ (Minimal Setup! Minimal Maintenance!)
A wrapper repo for free and easy deployment and environment configuration, as well automatic updates every 24-27.6 hours is available. Deploy up to 5 instances of it to a free Heroku account (total max monthly runtime 550 hours) with no need for credit card verification by clicking the button below.


TODO?
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Data-Horde/ytcc-archive-heroku)

### Archiving Worker⭐️
After completing the above setup steps, simply run 
```bash
python3 worker.py
```

### Docker image⭐️⭐️

Stable Docker Image:
```bash
docker pull TODO/TODO
```

Run:
```bash
docker container run --restart=unless-stopped --network=host -d --tmpfs /grab/out --name=grab_ext-yt-discussions-e TRACKER_USERNAME=Fusl -e PYTHONUNBUFFERED=1 TODO/TODO
```
## Bonus Features
### Download discussions manually
Simply run `python3 discussions.py <UC channel id>`
