# YouTube Discussions Archiving Script

### Note: As of 2021-10-19, this script is no longer functional, as Discussion tab data was made inaccessible from the InnerTube API depended on by these scripts. That said, as of 2021-10-20, [YouTube's public data API](https://developers.google.com/youtube/v3/docs/commentThreads/list?apix=true&apix_params=%7B%22part%22%3A%5B%22snippet%2Creplies%22%5D%2C%22channelId%22%3A%22UCAuUUnT6oDeKwE6v1NGQxug%22%7D) still supports retrieving Discussions on all channels including on channels with hidden Discussion tabs and on channels with Discussion tabs that have been replaced by Community Tabs.

### Download discussions manually
~~Simply run `python3 discussions.py <UC channel id>`~~
