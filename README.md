IL-2 FB Dedicated Server Middleware
===================================

[![Build Status](https://travis-ci.org/IL2HorusTeam/il2ds-middleware.svg?branch=master)](https://travis-ci.org/IL2HorusTeam/il2ds-middleware)
[![Coverage Status](https://coveralls.io/repos/IL2HorusTeam/il2ds-middleware/badge.png?branch=master)](https://coveralls.io/r/IL2HorusTeam/il2ds-middleware?branch=master)
[![PyPi package](https://badge.fury.io/py/il2ds-middleware.png)](http://badge.fury.io/py/il2ds-middleware/)
[![Downloads](https://pypip.in/d/il2ds-middleware/badge.png)](https://crate.io/packages/il2ds-middleware/)

High-level access to IL-2 FB Dedicated Server

Synopsis
--------

A Python library for high-level communications with IL-2 Sturmovik FB Dedicated  Server. It provides interfaces of different services and parsers with their default implementation.

Primitive asynchronous interaction with server's console via TCP in telnet format was replaced by a service which provides an RPC-like style for managing missions flow, tracking user connections, chatting, gaining user's statistics, etc.

Interaction with server's DeviceLink interface via UDP was replaced by a corresponding service.

Manual reading of server's log was replaced by a service for continuous log reading and parsing of events.

The library provides opportunities for flexible and extremely rapid development of applications for interaction with IL-2 DS.


Installation
------------

    pip install il2ds-middleware

Usage
-----

Sorry, usage documentation will come in future, but you can take a look at [examples](./examples) right now.
