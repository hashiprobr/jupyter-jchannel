import asyncio
import logging

from jchannel.types import AbstractServer, StateError


class Channel:
    def __init__(self, server, code):
        if not isinstance(server, AbstractServer):
            raise TypeError('First parameter must be a jchannel server')

        server._channels[id(self)] = self

        self._server = server
        self._code = code
        self._handler = None
        self._use = False

    def destroy(self):
        if self._use:
            raise StateError('Channel is currently in use')

        del self._server._channels[id(self)]

        self._server = None

    def open(self, timeout=3):
        return asyncio.create_task(self._open(timeout))

    def close(self, timeout=3):
        return asyncio.create_task(self._close(timeout))

    def echo(self, *args, timeout=3):
        return asyncio.create_task(self._echo(args, timeout))

    def call(self, name, *args, timeout=3):
        return asyncio.create_task(self._call(name, args, timeout))

    def _set_handler(self, handler):
        if handler is None:
            raise ValueError('Handler cannot be None')
        self._handler = handler

    handler = property(fset=_set_handler)

    def _handle_call(self, name, args):
        method = self._method(name)

        return method(*args)

    def _method(self, name):
        if self._handler is None:
            raise ValueError('Channel does not have handler')

        method = getattr(self._handler, name)

        if not callable(method):
            raise TypeError(f'Handler attribute {name} is not callable')

        return method

    async def __aenter__(self):
        await self._open(3)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._close(3)
        return False

    async def _open(self, timeout):
        result = await self._send('open', self._code, timeout)
        self._use = True
        return result

    async def _close(self, timeout):
        result = await self._send('close', None, timeout)
        self._use = False
        return result

    async def _echo(self, args, timeout):
        return await self._send('echo', args, timeout)

    async def _call(self, name, args, timeout):
        return await self._send('call', {'name': name, 'args': args}, timeout)

    async def _send(self, body_type, input, timeout):
        if self._server is None:
            raise StateError('Channel is destroyed')

        future = await self._server._send(body_type, input, id(self), timeout)

        try:
            return await future
        except StateError:
            logging.warning('Channel is closed: trying to open...')

            await self._open(timeout)

            future = await self._server._send(body_type, input, id(self), timeout)

            return await future
