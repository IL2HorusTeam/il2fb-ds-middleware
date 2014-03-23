# -*- coding: utf-8 -*-
import socket
import tx_logging

from collections import namedtuple, deque

from twisted.internet import defer
from twisted.internet.error import ConnectionDone
from twisted.internet.protocol import (ClientFactory,
    ReconnectingClientFactory, DatagramProtocol, )
from twisted.protocols.basic import LineOnlyReceiver

from il2ds_middleware.constants import (DEVICE_LINK_OPCODE as DL_OPCODE,
    DEVICE_LINK_PREFIXES, DEVICE_LINK_CMD_SEPARATOR as DL_CMD_SEP,
    DEVICE_LINK_ARGS_SEPARATOR as DL_ARGS_SEP, DEVICE_LINK_CMD_GROUP_MAX_SIZE,
    REQUEST_TIMEOUT, REQUEST_MISSION_LOAD_TIMEOUT, CHAT_MAX_LENGTH, )
from il2ds_middleware.parser import (ConsolePassthroughParser,
    DeviceLinkPassthroughParser, )
from il2ds_middleware.requests import *


LOG = tx_logging.getLogger(__name__)


ConsoleRequest = namedtuple('ConsoleRequest', 'rid results deferred')
DeviceLinkRequest = namedtuple('DeviceLinkRequest', 'opcode deferred')


class ConsoleClient(LineOnlyReceiver):
    """
    Server console client protocol. To capture server's output, every request
    to server gets own request ID (rid) which is send before and after request.

    Parser and timeout are set up by factory.
    """

    parser = None
    timeout = None

    def __init__(self):
        self._request_id = 0
        self._request = None
        self._requests = deque()

    def connectionMade(self):
        self.factory.clientConnectionMade(self)

    def _generate_request_id(self):
        request_id = self._request_id
        self._request_id = (self._request_id + 1) % 1000
        return request_id

    def _make_request(self, timeout):

        def on_timeout():
            LOG.error("Console request #{0} is timed out".format(rid))
            self._requests.remove(request)
            defer.timeout(deferred)

        rid = self._generate_request_id()
        results = []

        deferred = defer.Deferred()
        deferred.addCallback(lambda unused: watchdog.cancel())

        from twisted.internet import reactor
        watchdog = reactor.callLater(timeout,
                                     lambda: deferred.called or on_timeout())

        request = ConsoleRequest(rid, results, deferred)
        self._requests.append(request)
        return request

    def _send_request(self, line, timeout=None):
        request = self._make_request(timeout or self.timeout)
        wrapper = "rid|{0}".format(request.rid)
        self.sendLine(wrapper)
        self.sendLine(line)
        self.sendLine(wrapper)
        return request.deferred

    def lineReceived(self, line):
        if line.startswith("<consoleN><"):
            return
        self.got_line(line.replace("\\n", '').replace("\\u0020", ' '))

    def got_line(self, line):
        """
        Process a line from server's output.
        """
        if line.startswith("Command not found: rid"):
            self._process_request_wrapper(line)
        elif self._request:
            self._request.results.append(line)
        else:
            self.parser.parse_line(line)

    def _process_request_wrapper(self, line):
        try:
            rid = int(line.split('|')[1])
        except IndexError:
            LOG.error("RID format is malformed in \"{0}\"".format(line))
        except ValueError:
            LOG.error("Could not get RID value from \"{0}\"".format(line))
        else:
            self._process_request_id(rid)

    def _process_request_id(self, rid):
        if self._request is None:
            if not self._requests:
                LOG.error("No pending requests, but got RID {0}".format(rid))
                return
            if rid == self._requests[0].rid:
                self._request = self._requests.popleft()
            else:
                LOG.error("Unexpected RID: {0}".format(rid))
        elif self._request.rid == rid:
            request, self._request = self._request, None
            if not request.deferred.called:
                request.deferred.callback(request.results)

    def server_info(self, timeout=None):
        """
        Request server info. Returns deferred.
        """
        return self._send_request(REQ_SERVER_INFO, timeout).addCallback(
            self.parser.server_info)

    def mission_status(self, timeout=None):
        """
        Request mission status. Returns deferred.
        """
        return self._send_request(REQ_MISSION_STATUS, timeout).addCallback(
            self.parser.mission_status)

    def mission_load(self, mission, timeout=None):
        """
        Request to load mission.

        Input:
        `mission`       # mission name to load. E.g. "test/test.mis"

        Output:
        Deferred object.
        """
        timeout = timeout or REQUEST_MISSION_LOAD_TIMEOUT
        return self._send_request(
            REQ_MISSION_LOAD.format(mission), timeout).addCallback(
            self.parser.mission_status)

    def mission_begin(self, timeout=None):
        """
        Request to begin mission. Returns deferred.
        """
        return self._send_request(REQ_MISSION_BEGIN, timeout).addCallback(
            lambda unused: self.mission_status(timeout))

    def mission_end(self, timeout=None):
        """
        Request to end mission. Returns deferred.
        """
        return self._send_request(REQ_MISSION_END, timeout).addCallback(
            lambda unused: self.mission_status(timeout))

    def mission_destroy(self, timeout=None):
        """
        Request to end mission. Returns deferred.
        """
        return self._send_request(REQ_MISSION_DESTROY, timeout).addCallback(
            lambda unused: self.mission_status(timeout))

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

    @defer.inlineCallbacks
    def users_count(self, timeout=None):
        """
        Get count users of connected users. Returns deferred.
        """
        strings = yield self._request_users_common_info(timeout)
        defer.returnValue(len(strings) - 1) # '1' is for user table's header

    @defer.inlineCallbacks
    def users_common_info(self, timeout=None):
        """
        Get common information about pilots shown by 'user' command.
        Returns deferred.
        """
        strings = yield self._request_users_common_info(timeout)
        defer.returnValue(self.parser.users_common_info(strings))

    @defer.inlineCallbacks
    def users_statistics(self, timeout=None):
        """
        Get full information about pilots' statistics shown by 'user STAT'
        command. Returns deferred.
        """
        strings = yield self._send_request(REQ_USERS_STATISTICS, timeout)
        defer.returnValue(self.parser.users_statistics(strings))

    def _request_users_common_info(self, timeout=None):
        """
        Request output lines from 'user' command. Returns deferred.
        """
        return self._send_request(REQ_USERS_COMMON_INFO, timeout)

    def kick_callsign(self, callsign, timeout=None):
        """
        Kick user by callsign.

        Input:
        `callsign` # callsign of the user to be kicked
        """
        self.sendLine(REQ_KICK_CALLSIGN.format(callsign))
        return self.users_count(timeout)

    def kick_number(self, number, timeout=None):
        """
        Kick user by number, assigned by server (execute 'user' on server or
        press 'S' in game to see user numbers).

        Input:
        `number`  # number of the user to be kicked
        """
        self.sendLine(REQ_KICK_NUMBER.format(number))
        return self.users_count(timeout)

    def kick_all(self, max_count, timeout=None):
        """
        Kick everyone from server.

        Input:
        `max_count`  # maximal possible number of users on server. See
                     # 'NET/serverChannels' in 'confs.ini' for this value
        """
        for i in xrange(max_count):
            # Kick 1st user in cycle. It's important to kick all of the users.
            # Do not rely on 'user_count' method in this situation: number
            # of users may change between getting current user list and kicking
            # the last user. It's OK if number of users will decrease, but if
            # it will increase, then someone may not be kicked. There is still
            # a little chance that someone will connect to server during
            # kicking process, but nothing can be done with this due to current
            # server functionality.
            self.sendLine(REQ_KICK_FIRST)
        return self.users_count(timeout)


class ConsoleClientFactory(ClientFactory):
    """
    Factory for building console's client protocols.
    """

    protocol = ConsoleClient

    def __init__(self, parser=None, timeout=REQUEST_TIMEOUT):
        """
        Input:
        `parser`   # an object implementing IConsoleParser interface
        `timeout`  # float value for server requests timeout in seconds
        """
        self._client = None
        self.parser = parser
        self.timeout = timeout
        self.on_connecting = defer.Deferred()
        self.on_connection_lost = defer.Deferred()

    def buildProtocol(self, addr):
        self._client = ClientFactory.buildProtocol(self, addr)
        parser, self.parser = self.parser or ConsolePassthroughParser(), None
        timeout, self.timeout = self.timeout, None
        self._client.parser = parser
        self._client.timeout = timeout
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


class ReconnectingConsoleClientFactory(ReconnectingClientFactory):
    """
    Factory for building console's client protocols with support of
    reconnection to server in case of loosing connection.
    """
    # Client's protocol class.
    protocol = ConsoleClient

    # Parser instance which will be passed to client's protocol. Instance of
    # 'ConsolePassthroughParser' will be used if this value is not specified.
    parser = None

    # Float value for server requests timeout in seconds which will be passed
    # to client's protocol. 'REQUEST_TIMEOUT' will be used if this value is not
    # specified.
    request_timeout = None

    # Client's protocol instance placeholder.
    client = None

    # Deferred, which will be invoked after the connection with server is
    # established.
    on_connected = None

    # Deferred, which will be invoked after the connection with server is lost.
    # 'on_connected' and 'on_disconnected' deferreds will be recreated before
    # invocation of this deferred, so you will need to update your callbacks
    # for connection and disconnection during processing this deferred's
    # callback.
    on_disconnected = None

    def __init__(self, parser=None, timeout_value=None):
        """
        Optional input:
        `parser`        : an object implementing IConsoleParser interface
        `timeout_value` : float value for server requests timeout in seconds
        """
        self.parser = parser
        self.timeout_value = timeout_value
        self._update_deferreds()

    def buildProtocol(self, addr):
        """
        Create a single protocol for communicating with game server's console.
        """
        client = ReconnectingClientFactory.buildProtocol(self, addr)
        client.parser = self.parser or ConsolePassthroughParser()
        client.timeout_value = self.timeout_value or REQUEST_TIMEOUT
        self.client = client
        return self.client

    def clientConnectionMade(self, client):
        """
        A callback which is called when connection is successfully established.
        Invokes public callback and tells about this event to the outer world.
        """
        self.resetDelay()
        LOG.debug("Connection successfully established")
        if self.on_connected is not None:
            d, self.on_connected = self.on_connected, None
            d.callback(client)

    def clientConnectionFailed(self, connector, reason):
        """
        A callback which is called when connection could not be established.
        Overrides base method and logs connection failure.
        """
        if self.continueTrying:
            LOG.error("Failed to connect to server: {0}".format(
                      unicode(reason.value)))
        ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        d, self.on_disconnected = self.on_disconnected, None
        if self.continueTrying == 0:
            LOG.debug("Connection with server was closed.")
            # Invoke callback and tell that connection was closed cleanly
            if d:
                d.callback(None)
        else:
            LOG.error("Connection with server is lost: {0}".format(
                      unicode(reason.value)))
            self._update_deferreds()
            # Invoke callback and tell that connection was lost
            if d:
                d.errback(reason)
            ReconnectingClientFactory.clientConnectionLost(
                self, connector, reason)

    def _update_deferreds(self):
        """
        Recreate public deferreds, so listeners can update their callbacks for
        connection and disconnection events.
        """
        self.on_connected = defer.Deferred()
        self.on_disconnected = defer.Deferred()


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
            LOG.info("Message from unknown peer: {0}:{1}.".format(*address))
            return
        if data.startswith(DEVICE_LINK_PREFIXES['answer']):
            processor = self.answers_received
        elif data.startswith(DEVICE_LINK_PREFIXES['request']):
            processor = self.requests_received
        else:
            LOG.error("Malformed data from {0}: \"{1}\"")
            return
        prepared_data = data[1:].strip(DL_CMD_SEP)
        payloads = self.decompose(prepared_data)
        processor(payloads, address)

    def decompose(self, data):
        results = []
        for chunk in data.split(DL_CMD_SEP):
            command = chunk.split(DL_ARGS_SEP)
            arg = command[1:]
            results.append((command[0], arg[0] if arg else None, ))
        return results

    def answers_received(self, answers, address):
        """
        Process received answers from server.
        """

    def requests_received(self, requests, address):
        """
        Process received requests from client.
        """

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
            [prefix, self.compose(payloads), ])
        self.transport.write(data, address or self.address)

    def compose(self, payloads):
        chunks = []
        for payload in payloads:
            cmd, arg = payload
            chunks.append(
                DL_ARGS_SEP.join([cmd, str(arg)]) if arg is not None else cmd)
        return DL_CMD_SEP.join(chunks)


class DeviceLinkClient(DeviceLinkProtocol):
    """
    Default DeviceLink client protocol.
    """

    # Max number of consequent commands. We need to split large groups of
    # commands into smaller ones due to the limit of server's buffer size.
    cmd_group_max_size = DEVICE_LINK_CMD_GROUP_MAX_SIZE

    def __init__(self, address, parser=None, timeout=REQUEST_TIMEOUT):
        """
        Input:
        `address`  # server's address for filtering messages
        `parser`   # an object implementing IDeviceLinkParser interface
        `timeout`  # float value for server requests timeout in seconds
        """
        DeviceLinkProtocol.__init__(self, address)
        self.timeout = timeout
        self.parser = parser or DeviceLinkPassthroughParser()
        self._requests = deque()

    def answers_received(self, answers, address):
        if address == self.address:
            for answer in answers:
                self._answer_received(answer)

    def _answer_received(self, answer):
        if not self._requests:
            LOG.error("No pending requests, but got answer {0}".format(answer))
            return
        opcode, arg = answer

        if self._requests[0].opcode == opcode:
            request = self._requests.popleft()
            if not request.deferred.called:
                request.deferred.callback(arg)
        else:
            LOG.error("Unexpected opcode: {0}".format(opcode))

    def _make_request(self, opcode, timeout):

        def on_timeout():
            LOG.error(
                "Device Link request \"{0}\" is timed out".format(opcode))
            self._requests.remove(request)
            defer.timeout(deferred)

        deferred = defer.Deferred()
        deferred.addCallback(lambda unused: watchdog.cancel())

        from twisted.internet import reactor
        watchdog = reactor.callLater(timeout,
                                     lambda: deferred.called or on_timeout())

        request = DeviceLinkRequest(opcode, deferred)
        self._requests.append(request)
        return request

    def _deferred_request(self, command, timeout=None):
        timeout = timeout or self.timeout
        request = self._make_request(command.opcode, timeout)
        self.send_request(command)
        return request.deferred

    @defer.inlineCallbacks
    def _deferred_requests(self, commands, timeout=None):
        timeout = timeout or self.timeout

        def on_results(results):
            all_results.extend(results)

        all_results = []
        step = self.cmd_group_max_size
        count = len(commands)

        for i in xrange((count / step) + 1):
            start = i * step
            group = commands[start:start + min((count - start), step)]
            dlist = [
                self._make_request(command.opcode, timeout).deferred
                for command in group
            ]
            self.send_requests(group)
            yield defer.gatherResults(dlist).addCallback(on_results)

        defer.returnValue(all_results)

    def refresh_radar(self):
        """
        Request DeviceLink radar refreshing.
        """
        self.send_request(DL_OPCODE.RADAR_REFRESH.make_command())
        return defer.succeed(None)

    def pilot_count(self, timeout=None):
        """
        Request active pilots count.

        Output:
        Deferred object.
        """
        return self._deferred_request(
            DL_OPCODE.PILOT_COUNT.make_command(), timeout).addCallback(
            self.parser.pilot_count)

    def pilot_pos(self, index, timeout=None):
        """
        Request active pilot position.

        Input:
        `index`         # pilot's integer DeviceLink ID value

        Output:
        Deferred object.
        """
        return self._deferred_request(
            DL_OPCODE.PILOT_POS.make_command(index), timeout).addCallback(
            self.parser.pilot_pos)

    def all_pilots_pos(self, timeout=None):
        """
        Request list of positions of all active pilots.

        Output:
        Deferred object.
        """
        return self._all_pos(
            self.pilot_count, DL_OPCODE.PILOT_POS, timeout).addCallback(
            self.parser.all_pilots_pos)

    def static_count(self, timeout=None):
        """
        Request active static objects count.

        Output:
        Deferred object.
        """
        return self._deferred_request(
            DL_OPCODE.STATIC_COUNT.make_command(), timeout).addCallback(
            self.parser.static_count)

    def static_pos(self, index, timeout=None):
        """
        Request active static object position.

        Input:
        `index`         # static object's integer DeviceLink ID value

        Output:
        Deferred object.
        """
        return self._deferred_request(
            DL_OPCODE.STATIC_POS.make_command(index), timeout).addCallback(
            self.parser.static_pos)

    def all_static_pos(self, timeout=None):
        """
        Request list of positions of all active static objects.

        Output:
        Deferred object.
        """
        return self._all_pos(
            self.static_count, DL_OPCODE.STATIC_POS, timeout).addCallback(
            self.parser.all_static_pos)

    def _all_pos(self, get_count, pos_opcode, timeout=None):

        def on_count(result):
            count = int(result)
            if not count:
                return []
            return self._deferred_requests([
                pos_opcode.make_command(i) for i in xrange(count)], timeout)

        return get_count().addCallback(on_count)
