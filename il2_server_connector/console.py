# -*- coding: utf-8 -*-

import asynchat
import asyncore
import logging
import socket
import sys

from gettext import gettext as _
from threading import Lock, Event

LOG = logging.getLogger(__name__)


class PlainTextConsoleClient(asynchat.async_chat):

    """
    Allows to connect to IL-2 FB DS console in a plain text mode, where all
    messages are passed as plain strings and are separated by '\t\n' terminator.

    Sending and receiving messages is asynchronous. Sending is done by calling
    'send' method. Recieved messages are propagating to the processors, which
    can be registered via 'register_processor' method.
    """

    def __init__(self, sock=None, map=None):
        self.received_data = []
        self.processors = []
        self.processors_mx = Lock()
        self.connection_evt = Event()
        asynchat.async_chat.__init__(self, sock, map)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self, address):
        self.connection_evt.clear()
        asynchat.async_chat.connect(self, address)
        return self.connection_event

    def handle_connect(self):
        self.set_terminator("\r\n")
        self.connection_evt.set()

    def handle_close(self):
        if self.connecting:
            self.connection_evt.set()
        self.close()

    def collect_incoming_data(self, data):
        self.received_data.append(data)

    def found_terminator(self):
        received_message = ''.join(self.received_data)
        self.received_data = []
        with self.processors_mx:
            for processor in self.processors:
                processor.process(line)

    def tell(self, message):
        self.push(message + '\r\n')

    def register_processor(self, processor):
        with self.processors_mx:
            if processor in self.processors:
                LOG.warning(
                    "Console processor {0} is already registered".format(
                        processor))
            else:
                self.processors.append(processor)

    def unregister_processor(self, processor):
        with self.processors_mx:
            if processor in self.processors:
                self.processors.remove(processor)
            else:
                LOG.warning(
                    "Console processor {0} is not registered yet".format(
                        processor))

    @property
    def connection_event(self):
        return self.connection_evt
