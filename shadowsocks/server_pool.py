#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 clowwindy
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import logging
import utils
import time
import eventloop
import tcprelay
import udprelay
import asyncdns
import thread
import threading
import sys
import asyncmgr


class ServerPool(object):

    instance = None

    def __init__(self):
        utils.check_python()
        self.config = utils.get_config(False)
        utils.print_shadowsocks()
        self.dns_resolver = asyncdns.DNSResolver()

        self.tcp_servers_pool = {}
        #self.udp_servers_pool = {}

        self.loop = eventloop.EventLoop()
        thread.start_new_thread(ServerPool.run_server, (self.loop, self.dns_resolver))

    @staticmethod
    def get_instance():
        if ServerPool.instance is None:
            ServerPool.instance = ServerPool()
        return ServerPool.instance

    @staticmethod
    def run_server(loop, dns_resolver):
        try:
            mgr = asyncmgr.ServerMgr()
            mgr.add_to_loop(loop)
            dns_resolver.add_to_loop(loop)
            loop.run()
        except (KeyboardInterrupt, IOError, OSError) as e:
            logging.error(e)
            import traceback
            traceback.print_exc()
            os.exit(0)

    def server_is_run(self, port):
        port = int(port)
        if port in self.tcp_servers_pool:
            return True
        return False

    def new_server(self, port, password):
        ret = True
        port = int(port)
        if self.server_is_run(port):
            logging.info("server already at %s:%d" %(self.config['server'], port))
            return 'this port server is already running'

        a_config = self.config.copy()
        a_config['server_port'] = port
        a_config['password'] = password
        logging.info("starting server at %s:%d" %(a_config['server'], port))
        try:
            tcp_server = tcprelay.TCPRelay(a_config, self.dns_resolver, False)
            #udp_server = udprelay.UDPRelay(a_config, self.dns_resolver, False)
        except Exception, e:
            logging.warn(e)
            return e
        try:
            #add is safe
            tcp_server.add_to_loop(self.loop)
            self.tcp_servers_pool.update({port: tcp_server})
            #self.udp_servers_pool.update({port: tcp_server})
        except Exception, e:
            logging.warn(e)
            ret = e
        return ret

    def cb_del_server(self, port):
        port = int(port)
        ret = True
        if port not in self.tcp_servers_pool:
            logging.info("stopped server at %s:%d already stop" % (self.config['server'], int(port)))
            return True
        logging.info("stopped server at %s:%d" % (self.config['server'], int(port)))
        try:
            self.tcp_servers_pool[int(port)].destroy()
            del self.tcp_servers_pool[int(port)]
            #del self.udp_servers_pool[int(port)]
        except Exception, e:
            ret = e
            logging.warn(e)
            import traceback
            traceback.print_exc()
        return ret

    def get_server_transfer(self, port):
        port = int(port)
        if port in self.tcp_servers_pool:
            return [self.tcp_servers_pool[port].server_transfer_ul, self.tcp_servers_pool[port].server_transfer_dl]
        return [0,0]

    def get_servers_transfer(self):
        ret = {}
        for server_port in self.tcp_servers_pool.keys():
            ret[server_port] = [self.tcp_servers_pool[server_port].server_transfer_ul
                                     ,self.tcp_servers_pool[server_port].server_transfer_dl]
        return ret
