# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import (ClientFactory, DatagramProtocol, )
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE,
    DEVICE_LINK_PREFIXES, DEVICE_LINK_CMD_SEPARATOR as DL_CMD_SEP,
    DEVICE_LINK_ARGS_SEPARATOR as DL_ARGS_SEP, )


class ConsoleClientProtocol(LineOnlyReceiver):

    def connectionMade(self):
        self.factory.clientConnectionMade()

    def lineReceived(self, line):
        if line == '' or line == "exit\\n":
            log.err("Game server is shutting down")
            self.transport.loseConnection()
            return
        if line.startswith("<consoleN><"):
            return
        self.factory.got_line(
            line.replace("\\n", '').replace("\\u0020", ' '))


class ConsoleClientFactory(ClientFactory):

    protocol = ConsoleClientProtocol
    request_timeout = 0.1

    def __init__(self, parser=None):
        self._parser = parser
        self._client = None
        self._request_id = 0
        self._responce_id = None
        self.on_connecting = defer.Deferred()
        self.on_connection_lost = defer.Deferred()
        # { request_id: ([results], deferred, timeout, ), }
        self._requests = {}

    def buildProtocol(self, addr):
        self._client = ClientFactory.buildProtocol(self, addr)
        return self._client

    def clientConnectionMade(self):
        if self.on_connecting is not None:
            d, self.on_connecting = self.on_connecting, None
            d.callback(None)

    def clientConnectionFailed(self, connector, reason):
        if self.on_connecting is not None:
            d, self.on_connecting = self.on_connecting, None
            d.errback(reason)

    def clientConnectionLost(self, connector, reason):
        if self.on_connection_lost is not None:
            d, self.on_connection_lost = self.on_connection_lost, None
            if isinstance(reason.value, ConnectionDone):
                d.callback(None)
            else:
                d.errback(reason)

    def _generate_request_id(self):
        self._request_id += 1
        return self._request_id

    def _send(self, data):
        try:
            self._client.sendLine(data)
        except Exception as e:
            return defer.fail(e)
        else:
            return defer.succeed(None)

    def _send_request(self, request):
        rid = self._generate_request_id()
        d = defer.Deferred()

        def on_timeout(_):
            del self._requests[rid]
            defer.timeout(d)

        from twisted.internet import reactor
        timeout = reactor.callLater(self.request_timeout, on_timeout, None)

        self._requests[rid] = ([], d, timeout)
        wrapper = "rid|{0}".format(rid)
        try:
            self._client.sendLine(wrapper)
            self._client.sendLine(request)
            self._client.sendLine(wrapper)
        except Exception as e:
            timeout.cancel()
            del self._requests[rid]
            return defer.fail(e)
        else:
            return d

    def got_line(self, line):
        if line.startswith("Command not found: rid"):
            self._process_responce_id(line)
        elif self._responce_id:
            self._requests[self._responce_id][0].append(line)
        elif self._parser:
            self._parser.parse_line(line)

    def _process_responce_id(self, line):
        try:
            rid = int(line.split('|')[1])
        except Exception as e:
            log.err("Could not get rid value from \"{0}\"".format(line))
        else:
            if rid not in self._requests:
                log.err("Unexpected rid: {0}".format(rid))
                return
            if self._responce_id is None:
                # start request processing
                self._responce_id = rid
            elif self._responce_id == rid:
                # end request processing, send results to callback
                self._responce_id = None
                results, d, timeout = self._requests[rid]
                timeout.cancel()
                del self._requests[rid]
                d.callback(results)

    def server_info(self):
        d = self._send_request("server")
        if self._parser:
            d.addCallback(self._parser.server_info)
        return d

    def mission_status(self):
        d = self._send_request("mission")
        if self._parser:
            d.addCallback(self._parser.mission_status)
        return d


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
