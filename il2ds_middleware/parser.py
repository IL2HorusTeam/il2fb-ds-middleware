# -*- coding: utf-8 -*-

from zope.interface import implementer

from il2ds_middleware.interfaces import IDeviceLinkParser


@implementer(IDeviceLinkParser)
class DeviceLinkParser:

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
