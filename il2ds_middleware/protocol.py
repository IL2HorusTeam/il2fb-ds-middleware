# -*- coding: utf-8 -*-
import socket

from twisted.internet import defer
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import ClientFactory, DatagramProtocol
from twisted.protocols.basic import LineOnlyReceiver
from twisted.python import log

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE as DL_OPCODE,
    DEVICE_LINK_PREFIXES, DEVICE_LINK_CMD_SEPARATOR as DL_CMD_SEP,
    DEVICE_LINK_ARGS_SEPARATOR as DL_ARGS_SEP, DEVICE_LINK_CMD_GROUP_MAX_SIZE,
    REQUEST_TIMEOUT, REQUEST_MISSION_LOAD_TIMEOUT, CHAT_MAX_LENGTH, )
from il2ds_middleware.parser import (ConsolePassthroughParser,
    DeviceLinkPassthroughParser, )
from il2ds_middleware.requests import (
    REQ_SERVER_INFO, REQ_MISSION_STATUS, REQ_MISSION_LOAD, REQ_MISSION_BEGIN,
    REQ_MISSION_END, REQ_MISSION_DESTROY, REQ_CHAT, CHAT_ALL, CHAT_USER,
    CHAT_ARMY, )


class ConsoleClient(LineOnlyReceiver):

    """
    Server console client protocol. To capture server's output, every request
    to server gets own request ID (rid) which is send before and after request.
    All undone requests are stored in '_requests' dictionary as tuple of
    server's output strings list, deferred object to call and timeout object to
    cancel. Structure:
    {                       # undone requests dictionary
        rid:                # integer ID key to access request's context
        (                   # a tuple with request's context
            ["results"],    # a list of strings returned by server
            deferred,       # a deferred object to call
            timeout,        # timeout object to cancel if request was executed
                            # in time
        ),                  #
    }                       #

    Parser and timeout_value are set up by factory.
    """

    parser = None
    timeout_value = None

    def __init__(self):
        self._request_id = 0
        self._responce_id = None
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
            timeout_value or self.timeout_value, on_timeout, None)
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
        """Process a line from server's output."""
        if line.startswith("Command not found: rid"):
            self._process_responce_id(line)
        elif self._responce_id:
            self._requests[self._responce_id][0].append(line)
        else:
            self.parser.parse_line(line)

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
        """
        Request server info.

        Output:
        Deferred object.
        """
        d = self._send_request(REQ_SERVER_INFO)
        d.addCallback(self.parser.server_info)
        return d

    def mission_status(self, *args):
        """
        Request mission status

        Output:
        Deferred object.
        """
        d = self._send_request(REQ_MISSION_STATUS)
        d.addCallback(self.parser.mission_status)
        return d

    def mission_load(self, mission):
        """
        Request to load mission.

        Input:
        `mission`       # mission name to load. E.g. "test/test.mis"

        Output:
        Deferred object.
        """
        d = self._send_request(
            REQ_MISSION_LOAD.format(mission), REQUEST_MISSION_LOAD_TIMEOUT)
        d.addCallback(self.parser.mission_status)
        return d

    def mission_begin(self):
        """
        Request to begin mission.

        Output:
        Deferred object.
        """
        d = self._send_request(REQ_MISSION_BEGIN)
        d.addCallback(self.parser.mission_status)
        return d

    def mission_end(self):
        """
        Request to end mission.

        Output:
        Deferred object.
        """
        d = self._send_request(REQ_MISSION_END)
        d.addCallback(lambda _: self.mission_status())
        return d

    def mission_destroy(self):
        """
        Request to end mission.

        Output:
        Deferred object.
        """
        d = self._send_request(REQ_MISSION_DESTROY)
        d.addCallback(lambda _: self.mission_status())
        return d

    def chat_all(self, message):
        """
        Send chat message to all users.

        Input:
        `message`       # a string to send
        """
        self._chat(message, CHAT_ALL)

    def chat_user(self, message, callsign):
        """
        Send chat message to one user.

        Input:
        `message`       # a string to send
        `callsign`      # addressee's callsign
        """
        self._chat(message, CHAT_USER.format(callsign))

    def chat_army(self, message, army):
        """
        Send chat message to one army.

        Input:
        `message`       # a string to send
        `army`          # target army's name
        """
        self._chat(message, CHAT_ARMY.format(army))

    def _chat(self, message, suffix):
        last = 0
        total = len(message)
        while last < total:
            step = min(CHAT_MAX_LENGTH, total-last)
            chunk = message[last:last+step]
            self.sendLine(
                REQ_CHAT.format(chunk.encode('unicode-escape'), suffix))
            last += step


class ConsoleClientFactory(ClientFactory):

    """Factory for building server console's client protocols."""

    protocol = ConsoleClient

    def __init__(self, parser=None, timeout_value=REQUEST_TIMEOUT):
        """
        Input:
        `parser`        # an object implementing IConsoleParser interface
        `timeout_value` # float value for server requests timeout in seconds
        """
        self._client = None
        self.parser = parser
        self.timeout_value = timeout_value
        self.on_connecting = defer.Deferred()
        self.on_connection_lost = defer.Deferred()

    def buildProtocol(self, addr):
        self._client = ClientFactory.buildProtocol(self, addr)
        parser, self.parser = self.parser or ConsolePassthroughParser(), None
        tv, self.timeout_value = self.timeout_value, None
        self._client.parser = parser
        self._client.timeout_value = tv
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
    """
    Base protocol for communicating with server's DeviceLink interface.
    """

    def __init__(self, address=None):
        if address:
            host, port = address
            address = (socket.gethostbyname(host), port)
        self.address = address
        self.on_start = defer.Deferred()

    def startProtocol(self):
        if self.on_start is not None:
            d, self.on_start = self.on_start, None
            d.callback(None)

    def datagramReceived(self, data, address):
        if self.address is not None and address != self.address:
            log.msg("Message from unknown peer: {0}:{1}.".format(*address))
            return
        if data.startswith(DEVICE_LINK_PREFIXES['answer']):
            processor = self.answers_received
        elif data.startswith(DEVICE_LINK_PREFIXES['request']):
            processor = self.requests_received
        else:
            log.err("Malformed data from {0}: \"{1}\"")
            return
        prepared_data = data[1:].strip(DL_CMD_SEP)
        payloads = self._parse(prepared_data)
        processor(payloads, address)

    def _parse(self, data):
        results = []
        for chunk in data.split(DL_CMD_SEP):
            command = chunk.split(DL_ARGS_SEP)
            arg = command[1:]
            results.append((command[0], arg[0] if arg else None, ))
        return results

    def answers_received(self, answers, address):
        """Process received answers from server."""

    def requests_received(self, requests, address):
        """Process received requests from client."""

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

    """Default DeviceLink client protocol."""

    cmd_group_max_size = DEVICE_LINK_CMD_GROUP_MAX_SIZE

    def __init__(self, address, parser=None, timeout_value=REQUEST_TIMEOUT):
        """
        Input:
        `address`       # server's address for filtering messages
        `parser`        # an object implementing IDeviceLinkParser interface
        `timeout_value` # float value for server requests timeout in seconds
        """
        DeviceLinkProtocol.__init__(self, address)
        self.timeout_value = timeout_value
        self.parser = parser or DeviceLinkPassthroughParser()
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
            timeout_value or self.timeout_value, on_timeout, None)
        request = (command[0], d, timeout, )
        return request

    def _deferred_request(self, command, timeout_value=None):
        d = defer.Deferred()
        self._requests.append(
            self._make_request(command, d, timeout_value))
        self.send_request(command)
        return d

    @defer.inlineCallbacks
    def _deferred_requests(self, commands, timeout_value=None):

        def on_results(results):
            all_results.extend(results)

        all_results = []
        step = self.cmd_group_max_size
        count = len(commands)
        for i in xrange((count/step)+1):
            start = i*step
            group = commands[start:start+min((count-start), step)]
            dlist = []
            for cmd in group:
                d = defer.Deferred()
                self._requests.append(
                    self._make_request(cmd, d, timeout_value))
                dlist.append(d)
            self.send_requests(group)
            yield defer.gatherResults(dlist).addCallback(on_results)
        defer.returnValue(all_results)

    def refresh_radar(self):
        """Request DeviceLink radar refreshing."""
        self.send_request(DL_OPCODE.RADAR_REFRESH.make_command())
        return defer.succeed(None)

    def pilot_count(self):
        """
        Request active pilots count.

        Output:
        Deferred object.
        """
        d = self._deferred_request(DL_OPCODE.PILOT_COUNT.make_command())
        d.addCallback(self.parser.pilot_count)
        return d

    def pilot_pos(self, index):
        """
        Request active pilot position.

        Input:
        `index`         # pilot's integer DeviceLink ID value

        Output:
        Deferred object.
        """
        d = self._deferred_request(DL_OPCODE.PILOT_POS.make_command(index))
        d.addCallback(self.parser.pilot_pos)
        return d

    def all_pilots_pos(self):
        """
        Request list of positions of all active pilots.

        Output:
        Deferred object.
        """
        d = self._all_pos(self.pilot_count, DL_OPCODE.PILOT_POS)
        d.addCallback(self.parser.all_pilots_pos)
        return d

    def static_count(self):
        """
        Request active static objects count.

        Output:
        Deferred object.
        """
        d = self._deferred_request(DL_OPCODE.STATIC_COUNT.make_command())
        d.addCallback(self.parser.static_count)
        return d

    def static_pos(self, index):
        """
        Request active static object position.

        Input:
        `index`         # static object's integer DeviceLink ID value

        Output:
        Deferred object.
        """
        d = self._deferred_request(DL_OPCODE.STATIC_POS.make_command(index))
        d.addCallback(self.parser.static_pos)
        return d

    def all_static_pos(self):
        """
        Request list of positions of all active static objects.

        Output:
        Deferred object.
        """
        d = self._all_pos(self.static_count, DL_OPCODE.STATIC_POS)
        d.addCallback(self.parser.all_static_pos)
        return d

    def _all_pos(self, get_count, pos_opcode):

        def on_count(result):
            count = int(result)
            if not count:
                return []
            return self._deferred_requests([
                pos_opcode.make_command(i) for i in xrange(count)])

        return get_count().addCallback(on_count)
