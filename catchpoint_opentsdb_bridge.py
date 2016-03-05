#!/usr/bin/env python

import argparse
from node_list import catchpoint_nodes
from cyclone import web
import sys
import logging
from twisted.internet import epollreactor
if 'twisted.internet.reactor' not in sys.modules:
    epollreactor.install()
from twisted.internet import reactor, defer
from twisted.internet.protocol import Protocol, ReconnectingClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.python import log as twisted_log
import time
import json


loglevel = 'INFO'
#loglevel = 'DEBUG'


class OpenTSDBProtocol(Protocol):

    @defer.inlineCallbacks
    def put(self, metric_base, D, valkey, tagkeys=()):
        metric = '%s.%s' % (metric_base, D['testid'])
        tags = ' '.join(['%s=%s' % (k, str(D[k]) if D[k] is not None else '') for k in tagkeys])
        putline = 'put %s %d %f %s\n' % (metric, D['timestamp'], float(D[valkey]), tags)
        yield self.transport.write(putline)
        defer.succeed(True)


class OpenTSDBFactory(ReconnectingClientFactory):

    myproto = None

    def buildProtocol(self, addr):
        self.resetDelay()
        if self.myproto is None:
           self.myproto = OpenTSDBProtocol()
        return self.myproto

    def clientConnectionLost(self, connector, reason):
        self.myproto = None
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        self.myproto = None
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


class cp_push_request(web.RequestHandler):

    _tsdb = None

    def initialize(self, tsdb):
        self._tsdb = tsdb

    # {"Version":3,"V":3,"TestDetail":{"Name":"Test Name","TypeId":5,"MonitorTypeId":13},"TestId":12345,"ReportWindow":"201602260100","NodeId":312,"NodeName":"Jinan, CN - Unicom","Asn":4837,"DivisionId":1033,"ClientId":1234,"Summary":{"V":1,"Timestamp":"20160226010449609","Timing":{"Total":158},"Address":"1.2.3.4","Request":"www.example.com"}}

    def post(self):
        if self._tsdb.myproto is None:
            return  # not connected to tsdb, drop this datapoint
        try:
            body = json.loads(self.request.body)
            nodeid = body.get('NodeId', None)
            D = {
                'testid': body['TestId'],
                'timestamp': body.get('Summary', {}).get('Timestamp', None),
                'rtt': body.get('Summary', {}).get('Timing', {}).get('Total', None),
                'error': body.get('Summary', {}).get('Error', {}).get('Code', None),
                }
        except:
            raise web.HTTPError(400, 'bad body')

        try:
            node = nodes.get_node(int(nodeid))
        except:
            raise web.HTTPError(400, 'bad node id')

        try:
            ts = time.mktime(time.strptime(D['timestamp'][:-3], '%Y%m%d%H%M%S'))
            D['timestamp'] = int(ts)
        except:
            D['timestamp'] = int(time.time())

        D['counter'] = 1  # silly hack, will assign either 'error' or 'ok' as status
        D['status'] = 'ok' if D['error'] is None else 'error'

        D.update(node)

        # put each of these in tsdb, and tag the by_xxx, and nodeid so
        # we can agg across all nodes
        self._tsdb.myproto.put('catchpoint.rtt.by_node', D, 'rtt', ['nodeid'])
        self._tsdb.myproto.put('catchpoint.status.by_node', D, 'counter', ['nodeid', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_asn', D, 'rtt', ['nodeid', 'asn'])
        self._tsdb.myproto.put('catchpoint.status.by_asn', D, 'counter', ['nodeid', 'asn', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_continent', D, 'rtt', ['nodeid', 'continent'])
        self._tsdb.myproto.put('catchpoint.status.by_continent', D, 'counter', ['nodeid', 'continent', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_city', D, 'rtt', ['nodeid', 'city'])
        self._tsdb.myproto.put('catchpoint.status.by_city', D, 'counter', ['nodeid', 'city', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_country', D, 'rtt', ['nodeid', 'country'])
        self._tsdb.myproto.put('catchpoint.status.by_country', D, 'counter', ['nodeid', 'country', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_region', D, 'rtt', ['nodeid', 'region'])
        self._tsdb.myproto.put('catchpoint.status.by_region', D, 'counter', ['nodeid', 'region', 'status'])
        self._tsdb.myproto.put('catchpoint.rtt.by_isp', D, 'rtt', ['nodeid', 'isp'])
        self._tsdb.myproto.put('catchpoint.status.by_isp', D, 'counter', ['nodeid', 'isp', 'status'])

        defer.succeed(True)


if __name__ == '__main__':

    ap = argparse.ArgumentParser(description='Catchpoint Push API -> OpenTSDB bridge')
    ap.add_argument('-l', '--listen', default=8080, help='Listen port', type=int)
    ap.add_argument('-t', '--tsdb-host', default='localhost', help='OpenTSDB host')
    ap.add_argument('-p', '--tsdb-port', default=4242, help='OpenTSDB port', type=int)
    ap.add_argument('-k', '--key', help='Catchpoint Push API key', required=True)
    ap.add_argument('-s' ,'--secret', help='Catchpoint Push API secret', required=True)
    args = ap.parse_args()

    l = logging.getLogger()
    l.setLevel(loglevel)
    format_str = '[cp_pushd' \
        + ':%(module)s:%(name)s:%(lineno)d] ' \
        '%(levelname)s: %(message)s'
    term_format = logging.Formatter(fmt='%(asctime)s ' + format_str)

    # log to stdout for now
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(term_format)
    l.addHandler(h)

    obs = twisted_log.PythonLoggingObserver()
    obs.start()

    # init catchpoint node list
    nodes = catchpoint_nodes(args.key, args.secret)
    nodes.update_node_list()

    tsdb = OpenTSDBFactory()
    reactor.connectTCP(args.tsdb_host, args.tsdb_port, tsdb)

    app = web.Application([(r'/', cp_push_request, dict(tsdb=tsdb))], xheaders=True, debug=True)
    reactor.listenTCP(port=args.listen, factory=app)

    reactor.run()
