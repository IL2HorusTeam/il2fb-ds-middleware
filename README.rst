IL-2 FB Dedicated Server Middleware
===================================

|pypi_package| |pypi_downloads| |python_versions| |license|

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


.. |pypi_package| image:: http://img.shields.io/pypi/v/il2fb-ds-middleware.svg?style=flat
   :target: http://badge.fury.io/py/il2fb-ds-middleware/

.. |pypi_downloads| image:: http://img.shields.io/pypi/dm/il2fb-ds-middleware.svg?style=flat
   :target: https://crate.io/packages/il2fb-ds-middleware/
   :alt: Downloands of latest PyPI package

.. |python_versions| image:: https://img.shields.io/badge/Python-3.5,3.6-brightgreen.svg?style=flat
   :alt: Supported versions of Python

.. |docs| image:: https://readthedocs.org/projects/il-2-missions-parser/badge/?version=latest&style=flat
   :target: `read the docs`_
   :alt: Documentation

.. |license| image:: https://img.shields.io/badge/license-LGPLv3-brightgreen.svg?style=flat
   :target: https://github.com/IL2HorusTeam/il2fb-ds-middleware/blob/master/LICENSE
