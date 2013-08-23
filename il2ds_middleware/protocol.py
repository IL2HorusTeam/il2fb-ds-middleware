# -*- coding: utf-8 -*-

from twisted.internet import reactor
from twisted.internet.protocol import ClientFactory, DatagramProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE,
    DEVICE_LINK_PREFIXES, DEVICE_LINK_CMD_SEPARATOR as DL_CMD_SEP,
    DEVICE_LINK_ARGS_SEPARATOR as DL_ARGS_SEP, )


class ConsoleProtocol(LineOnlyReceiver):

    def connectionMade(self):
        log.msg("Connection established with {0}".format(
            self.transport.getaddress()))

    def connectionLost(self, reason):
        log.err("Connection with {0} lost: {1}".format(
            self.transport.getaddress(), reason))

    def lineReceived(self, line):
        if line == '' or line == "exit\\n":
            log.err("Game server is shut down")
            reactor.stop()
            return
        if line.startswith("<consoleN>"):
            return
        if line.endswith("\\n"):
            line = line[:-2]
        if line.startswith("\\u0020"):
            line = " " + line[6:]


class ConsoleFactory(ClientFactory):

    protocol = ConsoleProtocol
    receiver = None

    def clientConnectionFailed(self, connector, reason):
        log.err("Connection failed: %s" % reason)


class DeviceLinkProtocol(DatagramProtocol):

    def __init__(self, address=None):
        self.address = address

    def datagramReceived(self, data, (host, port)):
        if data.startswith(DEVICE_LINK_PREFIXES['answer']):
            processor = self.answers_received
        elif data.startswith(DEVICE_LINK_PREFIXES['request']):
            processor = self.requests_received
        else:
            log.err("Malformed data from {0}: \"{1}\"")
            return
        prepared_data = data[1:].strip(DL_CMD_SEP)
        payloads = self._parse(prepared_data)
        processor(payloads, (host, port))

    def _parse(self, data):
        results = []
        for chunk in data.split(DL_CMD_SEP):
            command = chunk.split(DL_ARGS_SEP)
            result = {}
            result['command'] = command[0]
            args = command[1:]
            if args:
                result['args'] = args
            results.append(result)
        return results

    def answers_received(self, answers, address):
        raise NotImplementedError

    def requests_received(self, requests, address):
        raise NotImplementedError

    def send_request(self, request, address=None):
        self.send_requests([request, ], address)

    def send_requests(self, requests, address=None):
        self._send_payloads(DEVICE_LINK_PREFIXES['request'], requests, address)

    def send_answer(self, answer, address=None):
        self.send_answers([answer, ], address)

    def send_answers(self, answers, address=None):
        self._send_payloads(DEVICE_LINK_PREFIXES['answer'], answers, address)

    def _send_payloads(self, prefix, payloads, address=None):
        data = DL_CMD_SEP.join(
            [prefix, self._format(payloads), ])
        self.transport.write(data, address or self.address)

    def _format(self, payloads):
        chunks = []
        for payload in payloads:
            chunk = [payload['command'], ]
            raw_args = payload.get('args')
            if raw_args:
                chunk.extend([str(_) for _ in raw_args])
            chunks.append(DL_ARGS_SEP.join(chunk))
        return DL_CMD_SEP.join(chunks)
