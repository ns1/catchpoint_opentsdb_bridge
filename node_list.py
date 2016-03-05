#!/usr/bin/env python

import requests
import catchpoint
import pickle
import json
import re
import os
import time


requests.packages.urllib3.disable_warnings()


class catchpoint_nodes:

    _node_list = None
    _node_list_mtime = 0

    def __init__(self, key, secret):
        self._key = key
        self._secret = secret

    def update_node_list(self):
        try:
            st = os.stat('node_list.pickle')
            self._node_list_mtime = st.st_mtime
            age = time.time() - self._node_list_mtime
            # only reload from catchpoint if > 1d old
            if age <= 86400 * 5:
                self._node_list = pickle.load(open('node_list.pickle', 'rb'))
                return
        except:
            pass

        asn_re = re.compile('^AS(\d+)')
        creds = {
            'client_id': self._key,
            'client_secret': self._secret
            }
        cp = catchpoint.Catchpoint()
        raw_node_list = cp.nodes(creds)

        node_list = {}
        for node in raw_node_list['items']:
            matches = re.match(asn_re, node.get('asn', {}).get('value', ''))
            if matches:
                asn = int(matches.group(1))
            else:
                asn = None
            nid = int(str(node['id']))
            node_list[nid] = {
                'asn': asn,
                'continent': node.get('continent', {}).get('name', None),
                'network_type': node.get('network_type', {}).get('name', None),
                'city': node.get('city', {}).get('name', None),
                'country': node.get('country', {}).get('name', None),
                'region': node.get('region', {}).get('name', None),
                'isp': node.get('isp', {}).get('name', None),
                'nodeid': nid,
                }
            for k in ('continent', 'city', 'country', 'region', 'isp'):
                if node_list[nid][k] is not None:
                    node_list[nid][k] = node_list[nid][k].replace(' ', '_')

            pickle.dump(node_list, open('node_list.pickle', 'wb'))
            self._node_list = node_list

    def get_node(self, nodeid):
        if self._node_list is None:
            self.update_node_list()
        node = self._node_list.get(int(nodeid), None)
        if node is None and time.time() - self._node_list_mtime > 86400:
            self.update_node_list()
            node = self._node_list.get(int(nodeid), None)
        return node
