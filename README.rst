IL-2 FB Dedicated Server Middleware
===================================

|PyPi package| |Downloads|

High-level access to IL-2 FB Dedicated Server


Synopsis
--------

A Python library for high-level communications with IL-2 Sturmovik FB
Dedicated Server. It provides interfaces of different services and
parsers with their default implementation.

Primitive asynchronous interaction with server's console via TCP in
telnet format was replaced by a service which provides an RPC-like style
for managing missions flow, tracking user connections, chatting, gaining
user's statistics, etc.

Interaction with server's DeviceLink interface via UDP was replaced by a
corresponding service.

Manual reading of server's log was replaced by a service for continuous
log reading and parsing of events.

The library provides opportunities for flexible and extremely rapid
development of applications for interaction with IL-2 DS.


Installation
------------

::

    pip install il2fb-ds-middleware


.. |PyPi package| image:: https://badge.fury.io/py/il2fb-ds-middleware.png
   :target: http://badge.fury.io/py/il2fb-ds-middleware/
.. |Downloads| image:: https://pypip.in/d/il2fb-ds-middleware/badge.png
   :target: https://crate.io/packages/il2fb-ds-middleware/
