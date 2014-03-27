# -*- coding: utf-8 -*-
from zope.interface.verify import verifyClass

from il2ds_middleware.interface.parser import ILineParser
from il2ds_middleware.ds_emulator.service import (RootService, PilotsService,
    MissionsService, )


verifyClass(ILineParser, RootService)
verifyClass(ILineParser, PilotsService)
verifyClass(ILineParser, MissionsService)
