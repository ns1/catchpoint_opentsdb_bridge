# Catchpoint Push API to OpenTSDB bridge
> This project is [inactive](https://github.com/ns1/community/blob/master/project_status/INACTIVE.md).

## Description

Catchpoint's Push API shoves raw datapoints gathered by Catchpoint's
global monitoring network into an HTTP endpoint.  This quick and dirty
server accepts Catchpoint Push messages and renders them into a few
OpenTSDB metrics.

At [NS1](https://ns1.com) we use Catchpoint to measure DNS network
performance and reliability, so this server is focused on accepting
very simple RTT and error rate metrics and dropping them in OpenTSDB.
Once the data is in OpenTSDB, it's easy to leverage it in other tools
like Grafana for dashboarding, Bosun for alerting, etc.

The server also uses Catchpoint's REST API to regularly pull a list of
Catchpoint nodes so Push API metrics can be tagged by geographic and
network metadata in OpenTSDB.

## Requirements

Tested on Python 2.7.x

Requires [Twisted](https://twistedmatrix.com/trac/),
[Cyclone](http://cyclone.io/), requests, pytz.

This repository includes code (catchpoint.py) from
https://github.com/jasonarewhy/catchpoint-api-python for convenience,
although of course you can install that module directly.

## Usage

You must authorize the public IP of the server to access the
Catchpoint REST API.  You must also generate a key/secret and enable
the Catchpoint Push API for at least one of your tests.

Run the server like:

`./catchpoint_opentsdb_bridge.py -l <listen port> -t <tsdb host> -p <tsdb port> -k <key> -s <secret>`

Depending on your environment, it may be useful to run the server
using Upstart or a similar process management system.

## Metrics

Our use case is to track performance and reliability of various DNS
networks across geographies and ISPs.  We generate OpenTSDB metrics
pre-sliced in a few ways: by node, ASN, continent, city, country,
region, and ISP.  It would be easy to add more, or add additional
tagging to the existing metrics.  We are optimizing for display-time
simplicity/speed in our use case.

Contributions
---
Pull Requests and issues are welcome. See the [NS1 Contribution Guidelines](https://github.com/ns1/community) for more information.

## License

GPL v2
