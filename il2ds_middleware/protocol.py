# -*- coding: utf-8 -*-

from twisted.internet import defer
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import (ClientFactory, DatagramProtocol, )
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE as DL_OPCODE,
    DEVICE_LINK_PREFIXES, DEVICE_LINK_CMD_SEPARATOR as DL_CMD_SEP,
    DEVICE_LINK_ARGS_SEPARATOR as DL_ARGS_SEP, DEVICE_LINK_CMD_GROUP_MAX_SIZE,
    REQUEST_TIMEOUT, REQUEST_MISSION_LOAD_TIMEOUT, )
from il2ds_middleware.requests import (
    REQ_SERVER_INFO, REQ_MISSION_STATUS, REQ_MISSION_LOAD, REQ_MISSION_BEGIN,
    REQ_MISSION_END, REQ_MISSION_DESTROY, )


class ConsoleClient(LineOnlyReceiver):

    def __init__(self, parser=None):
        self._parser = parser
        self._request_id = 0
        self._responce_id = None
        # { request_id: ([results], deferred, timeout, ), }
        self._requests = {}

    def connectionMade(self):
        self.factory.clientConnectionMade(self)

    def _generate_request_id(self):
        self._request_id += 1
        return self._request_id

    def _make_request(self, d, timeout_value):
        rid = self._generate_request_id()

        def on_timeout(_):
            del self._requests[rid]
            defer.timeout(d)

        from twisted.internet import reactor
        timeout = reactor.callLater(
            timeout_value or REQUEST_TIMEOUT, on_timeout, None)
        return rid, ([], d, timeout, )

    def _send_request(self, line, timeout_value=None):
        d = defer.Deferred()
        rid, request = self._make_request(d, timeout_value)
        self._requests[rid] = request

        wrapper = "rid|{0}".format(rid)
        self.sendLine(wrapper)
        self.sendLine(line)
        self.sendLine(wrapper)
        return d

    def lineReceived(self, line):
        if line.startswith("<consoleN><"):
            return
        self.got_line(line.replace("\\n", '').replace("\\u0020", ' '))

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
        except IndexError:
            log.err("RID format is malformed in \"{0}\"".format(line))
        except ValueError:
            log.err("Could not get RID value from \"{0}\"".format(line))
        else:
            if rid not in self._requests:
                log.err("Unexpected RID: {0}".format(rid))
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
        d = self._send_request(REQ_SERVER_INFO)
        if self._parser:
            d.addCallback(self._parser.server_info)
        return d

    def mission_status(self):
        d = self._send_request(REQ_MISSION_STATUS)
        if self._parser:
            d.addCallback(self._parser.mission_status)
        return d

    def mission_load(self, mission):
        d = self._send_request(
            REQ_MISSION_LOAD.format(mission), REQUEST_MISSION_LOAD_TIMEOUT)
        if self._parser:
            d.addCallback(self._parser.mission_load)
        return d

    def mission_begin(self):
        d = self._send_request(REQ_MISSION_BEGIN)
        if self._parser:
            d.addCallback(self._parser.mission_begin)
        return d

    def mission_end(self):
        d = self._send_request(REQ_MISSION_END)
        d.addCallback(lambda _: self.mission_status())
        if self._parser:
            d.addCallback(self._parser.mission_end)
        return d

    def mission_destroy(self):
        d = self._send_request(REQ_MISSION_DESTROY)
        d.addCallback(lambda _: self.mission_status())
        if self._parser:
            d.addCallback(self._parser.mission_destroy)
        return d


class ConsoleClientFactory(ClientFactory):

    protocol = ConsoleClient

    def __init__(self, parser=None):
        self._client = None
        self.on_connecting = defer.Deferred()
        self.on_connection_lost = defer.Deferred()

    def buildProtocol(self, addr):
        self._client = ClientFactory.buildProtocol(self, addr)
        return self._client

    def clientConnectionMade(self, client):
        if self.on_connecting is not None:
            d, self.on_connecting = self.on_connecting, None
            d.callback(client)

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
            arg = command[1:]
            results.append((command[0], arg[0] if arg else None, ))
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
            cmd, arg = payload
            chunks.append(
                DL_ARGS_SEP.join([cmd, str(arg)]) if arg is not None else cmd)
        return DL_CMD_SEP.join(chunks)


class DeviceLinkClient(DeviceLinkProtocol):

    cmd_group_max_size = DEVICE_LINK_CMD_GROUP_MAX_SIZE

    def __init__(self, address):
        DeviceLinkProtocol.__init__(self, address)
        # [ (opcode, deferred, timeout), ]
        self._requests = []

    def answers_received(self, answers, address):
        if address == self.address:
            for answer in answers:
                self._answer_received(answer)

    def _answer_received(self, answer):
        cmd, arg = answer
        for request in self._requests:
            opcode, d, timeout = request
            if opcode == cmd:
                timeout.cancel()
                self._requests.remove(request)
                d.callback(arg)
                break

    def _make_request(self, command, d, timeout_value=None):

        def on_timeout(_):
            self._requests.remove(request)
            defer.timeout(d)

        from twisted.internet import reactor
        timeout = reactor.callLater(
            timeout_value or REQUEST_TIMEOUT, on_timeout, None)
        request = (command[0], d, timeout, )
        return request

    def _deferred_request(self, command, timeout_value=None):
        d = defer.Deferred()
        self._requests.append(
            self._make_request(command, d, timeout_value))
        self.send_request(command)
        return d

    def _deferred_requests_iterator(self, commands):
        step = self.cmd_group_max_size
        count = len(commands)
        for i in xrange((count/step)+1):
            start = i*step
            yield commands[start:start+min((count-start), step)]

    def _deferred_requests_group(self, iterator, timeout_value=None):
        try:
            group = iterator.next()
        except StopIteration:
            return defer.succeed(None)
        else:
            dlist = []
            for cmd in group:
                d = defer.Deferred()
                self._requests.append(
                    self._make_request(cmd, d, timeout_value))
                dlist.append(d)
            self.send_requests(group)
            return defer.gatherResults(dlist)

    def _deferred_requests(self, commands, timeout_value=None):
        """
        Send requests in portions. Each next portion is send after result
        of the previous one was received. All results are collected in one
        place and are returned if there no requests has left.
        """
        all_results = []
        iterator = self._deferred_requests_iterator(commands)

        def on_results(results):
            if results:
                all_results.extend(results)
                return do_next()
            else:
                return all_results

        def do_next():
            return self._deferred_requests_group(
                iterator, timeout_value).addCallback(on_results)

        return do_next()

    def refresh_radar(self):
        self.send_request(DL_OPCODE.RADAR_REFRESH.make_command())
        return defer.succeed(None)

    def pilot_count(self):
        return self._deferred_request(DL_OPCODE.PILOT_COUNT.make_command())

    def pilot_pos(self, index):
        return self._deferred_request(DL_OPCODE.PILOT_POS.make_command(index))

    def all_pilots_pos(self):
        return self._all_pos(self.pilot_count, DL_OPCODE.PILOT_POS)

    def static_count(self):
        return self._deferred_request(DL_OPCODE.STATIC_COUNT.make_command())

    def static_pos(self, index):
        return self._deferred_request(DL_OPCODE.STATIC_POS.make_command(index))

    def all_static_pos(self):
        return self._all_pos(self.static_count, DL_OPCODE.STATIC_POS)

    def _all_pos(self, get_count, pos_opcode):

        def on_count(result):
            count = int(result)
            if not count:
                return []
            return self._deferred_requests([
                pos_opcode.make_command(i) for i in xrange(count)])

        return get_count().addCallback(on_count)
