# -*- coding: utf-8 -*-
"""
This test module requires real IL-2 FB DS running. Its host and address must
be set as evn variable called 'IL2_FB_TEST_DS_ADDRESS' which is described as:

    IL2_FB_TEST_DS_ADDRESS=[host:]port
"""

import asyncore
import os
import time
import threading
import unittest

from il2_server_connector.console import PlainTextConsoleClient


def get_address():
    address = os.environ.get('IL2_FB_TEST_DS_ADDRESS')
    
    if ':' in address:
        host, port = address.split(':', 1)
    else:
        host = "localhost"
        port = address
        
    port = int(port) if port.isdigit() else None
    return host, port


host, port = get_address()


@unittest.skipUnless(host and port, "requires 'host' and 'port' of IL-2 FB DS")
class PlainTextConsoleClientTestCase(unittest.TestCase):

    def setUp(self):
        self.client = PlainTextConsoleClient()

    def tearDown(self):
        if self.client.connected:
            self.client.close()
        del self.client

    def test_connection_with_wrong_address(self):
        evt = self.client.connect(address=("localhost", 0))
        loop_thread = threading.Thread(target=asyncore.loop)
        self.daemon = True
        loop_thread.start()
        evt.wait(0.1)
        assert self.client.connected == False
        loop_thread.join(0.1)

    def test_connection(self):
        evt = self.client.connect(address=(host, port))
        loop_thread = threading.Thread(target=asyncore.loop)
        self.daemon = True
        loop_thread.start()
        evt.wait(0.1)
        assert self.client.connected
        self.client.close()
        loop_thread.join(0.1)

    def test_multiline_response(self):
        lines = []

        def accumulator(string):
            lines.append(string)

        evt = self.client.connect(address=(host, port))
        loop_thread = threading.Thread(target=asyncore.loop)
        self.daemon = True
        loop_thread.start()
        evt.wait(0.1)
        assert self.client.connected

        self.client.register_processor(accumulator)
        self.client.tell("server")
        time.sleep(1)
        self.client.unregister_processor(accumulator)

        assert len(lines) == 3
        assert lines[0].startswith("Type:")
        assert lines[1].startswith("Name:")
        assert lines[2].startswith("Description:")

        self.client.close()
        loop_thread.join(0.1)
