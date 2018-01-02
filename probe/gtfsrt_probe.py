#!/usr/bin/env python
import sys, os, urllib2
import gtfs_realtime_pb2
import time

#usage : ./gtfsrt_probe <feed_url> <timeout>
#timeout in seconds
def main():
    try:
        gtfs_realtime = gtfs_realtime_pb2.FeedMessage()
        gtfs_realtime.ParseFromString(urllib2.urlopen(sys.argv[1]).read())
    except:
        sys.exit('Cannot parse pb from url {}'.format(sys.argv[1]))

    try:
        ts = int(gtfs_realtime.header.timestamp)
    except:
        sys.exit('No "header.timestamp" field in feed.')

    if int(time.time()) - ts >  int(sys.argv[2]):
        sys.exit('The feed provided is more than {}s old, timestamp:{}'.format(sys.argv[2], ts))

    print('Feed on  {} looks OK'.format(sys.argv[1]))
    sys.exit(os.EX_OK)

if __name__ == '__main__':
    main()
