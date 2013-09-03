# -*- coding: utf-8 -*-

from zope.interface import implementer

from il2ds_middleware.constants import MISSION_STATUS, PILOT_LEAVE_REASON
from il2ds_middleware.interface.parser import (IDeviceLinkParser,
    IConsoleParser, )


@implementer(IConsoleParser)
class ConsoleParser(object):

    _buffer = None

    def __init__(self, pilot_service=None):
        self.pilot_service = pilot_service

    def parse_line(self, line):
        if self.user_joined(line):
            return
        elif self.user_left(line):
            return

    def server_info(self, lines):
        result = {}
        for line in lines:
            key, value = line.split(':')
            result[key.strip().lower()] = value.strip()
        return result

    def mission_status(self, lines):
        for line in lines:
            if line == "Mission NOT loaded":
                return (MISSION_STATUS.NOT_LOADED, None, )
            elif line.endswith("is Loaded"):
                return (MISSION_STATUS.LOADED, line.split()[1], )
            elif line.endswith("is Playing"):
                return (MISSION_STATUS.PLAYING, line.split()[1], )
        return lines

    mission_load = mission_destroy = mission_status
    mission_begin = mission_end = mission_status

    def user_joined(self, line):
        result = (line.startswith("socket channel")
            and line.endswith("is complete created."))
        if result:
            chunks = line.split(',')
            info = {
                'channel': int(chunks[0].split()[-1].strip('\'')),
                'ip': chunks[1].split()[-1].split(':')[0],
                'callsign': chunks[2].strip(),
            }
            if self.pilot_service is not None:
                self.pilot_service.user_join(info)
        return result

    def user_left(self, line):
        if line.startswith("socketConnection with") and "lost" in line:
            self._buffer = line
            return True
        elif line.endswith("has left the game.") and self._buffer:
            chunks = self._buffer.split()
            reason = (PILOT_LEAVE_REASON.KICKED if 'kicked' in self._buffer
                else PILOT_LEAVE_REASON.DISCONNECTED)
            self._buffer = None
            info = {
                'channel': int(chunks[5]),
                'ip': chunks[2].split(':')[0],
                'callsign': line.split()[2],
                'reason': reason,
            }
            if self.pilot_service is not None:
                self.pilot_service.user_left(info)
            return True
        else:
            return False

    def on_user_left(self, info):
        raise NotImplementedError

@implementer(IDeviceLinkParser)
class DeviceLinkParser(object):

    def pilot_count(self, data):
        return int(data)

    def pilot_pos(self, data):
        return self._parse_pos(data, 'callsign')

    def all_pilots_pos(self, datas):
        return map(self.pilot_pos, datas)

    static_count = pilot_count

    def static_pos(self, data):
        return self._parse_pos(data)

    def all_static_pos(self, datas):
        return map(self.static_pos, datas)

    def _parse_pos(self, data, name_attr='name'):
        idx, info = data.split(':')
        attr, x, y, z = info.split(';')
        return {
            'idx': int(idx),
            name_attr: attr,
            'pos': {
                'x': int(x),
                'y': int(y),
                'z': int(z),
            },
        }
