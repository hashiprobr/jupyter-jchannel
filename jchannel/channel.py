import asyncio

from jchannel.error import StateError


class Channel:
    def __init__(self, server, code):
        server.channels[id(self)] = self

        self.server = server
        self.code = code
        self.handler = None

    def __del__(self):
        del self.server.channels[id(self)]

    def open(self, timeout=3):
        return asyncio.create_task(self._open(timeout))

    def close(self, timeout=3):
        return asyncio.create_task(self._close(timeout))

    def echo(self, *args, timeout=3):
        return asyncio.create_task(self._echo(args, timeout))

    def call(self, name, *args, timeout=3):
        return asyncio.create_task(self._call(name, args, timeout))

    def set_handler(self, handler):
        if handler is None:
            raise ValueError('Handler cannot be None')
        self.handler = handler

    def _handle_call(self, name, args):
        method = self._method(name)

        return method(*args)

    def _method(self, name):
        if self.handler is None:
            raise ValueError('Channel does not have handler')

        method = getattr(self.handler, name)

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
        return await self._send('open', self.code, timeout)

    async def _close(self, timeout):
        return await self._send('close', None, timeout)

    async def _echo(self, args, timeout):
        return await self._send('echo', args, timeout)

    async def _call(self, name, args, timeout):
        return await self._send('call', {'name': name, 'args': args}, timeout)

    async def _send(self, body_type, input, timeout):
        future = await self.server._send(body_type, input, id(self), timeout)

        try:
            return await future
        except StateError:
            await self._open(timeout)

            future = await self.server._send(body_type, input, id(self), timeout)

            return await future
