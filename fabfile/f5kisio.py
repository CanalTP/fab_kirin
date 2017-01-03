# -*- coding: utf-8 -*-
""" Simple F5 nodes managment """

from __future__ import print_function
import bigsuds
# avoid 'No handlers could be found for logger "suds.client"'
import logging
logging.getLogger('suds.client').setLevel(logging.CRITICAL)

from os import environ
import getpass
import socket
from fabric.api import env


class F5NodesManagment:
    def disable_node(self, node):
        pass

    def enable_node(self, node):
        pass


class NullF5NodesManagment(F5NodesManagment):
    def disable_node(self, node):
        """ Null impl """

    def enable_node(self, node):
        """ Null impl """


class SimpleF5NodesManagment(F5NodesManagment):
    """ Simple F5 nodes managment """
    def __init__(self, hostname, verbose=False):
        """ If ADC_LOGIN & ADC_PASSWORD not defined, prompt for it """
        if not environ.get('ADC_LOGIN') or not environ.get('ADC_PASSWORD'):
            self.username = raw_input("%s username: " % env.ADC_HOSTNAME)
            self.password = getpass.getpass("%s password: " % env.ADC_HOSTNAME)
        else:
            self.username = environ.get('ADC_LOGIN')
            self.password = environ.get('ADC_PASSWORD')

        self.hostname = hostname
        try:
            self.connection = bigsuds.BIGIP(
            hostname = self.hostname, \
            username = self.username, \
            password = self.password \
            )
            self.connection.System.SystemInfo.get_version()
        except Exception as error:
            print("Error when connecting to %s: %s" % (env.ADC_HOSTNAME, error))
            exit(1)
        self.verbose = verbose

    def disable_node(self, node):
        """ Disable F5 ADC node by hostname or ip address"""

        node = self.hostname2node(node)

        if self.verbose:
            print("Disable {} node".format(node))
        try:
            self.connection.LocalLB.NodeAddressV2.set_monitor_state(nodes=[node], states=['STATE_DISABLED'])
            self.connection.LocalLB.NodeAddressV2.set_session_enabled_state(nodes=[node], states=['STATE_DISABLED'])
        except Exception as error:
            print("Error when disabling {node}: {err}"
                    .format(node=node, err=error))
            exit(1)

    def enable_node(self, node):
        """ Enable F5 ADC node by hostname or ip address"""
        node = self.hostname2node(node)

        if self.verbose:
            print("Enable {} node".format(node))
        try:
            self.connection.LocalLB.NodeAddressV2.set_monitor_state(nodes=[node],
                                                                    states=['STATE_ENABLED'])
            self.connection.LocalLB.NodeAddressV2.set_session_enabled_state(nodes=[node],
                                                                            states=['STATE_ENABLED'])
        except Exception as error:
            print("Error when enabling {node}: {err}"
                    .format(node=node, err=error))
            exit(1)

    def hostname2node(self, host):
        """ Return the node name equivalent to hostname or ip address """
        # clean the host which can contain usernames from fabric
        host_only = host.replace('root@', '')

        # next step, search the ip corresponding to the hostname
        try:
            host_ip = socket.gethostbyname(host_only) \
                    .replace(env.HOSTNAME_SUFFIX, '')
        except socket.gaierror as error:
            print("Error when resolving {}: {}".format(host_only, error))
            exit(1)

        # final step, give the F5 object corresponding to this ip
        # the node object is unique in F5 BIG-IP
        nodes = self.get_nodes_address()

        if host_ip in nodes:
            return nodes[host_ip]
        else:
            print("Error: {} not found in {}".format(host_ip, self.hostname))
            exit(1)

    def get_nodes_address(self):
        """ Get all nodes names and all corresponding ip to build a dict """
        nodes = self.connection.LocalLB.NodeAddressV2.get_list()
        addresses = \
                self.connection.LocalLB.NodeAddressV2.get_address(nodes=nodes)

        return dict(zip(addresses, nodes))
