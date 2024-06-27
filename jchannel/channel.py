import asyncio
import logging

from jchannel.types import AbstractServer, StateError


class Channel:
    def __init__(self, server, code):
        '''
        Represents a communication channel between a kernel server and a
        frontend client.

        :param server: The server.
        :type server: jchannel.server.Server

        :param code: JavaScript code representing an initialization function.
            This function should receive a `client Channel
            <https://hashiprobr.github.io/jupyter-jchannel-client/Channel.html>`_
            instance and initialize it.
        :type code: str
        '''

        if not isinstance(server, AbstractServer):
            raise TypeError('First parameter must be a jchannel server')

        server._channels[id(self)] = self

        self._server = server
        self._code = code
        self._handler = None
        self._use = False

    def destroy(self):
        '''
        Destroys this channel.

        An open channel cannot be destroyed. It must be closed first.

        A destroyed channel cannot be used for anything. There is no reason to
        keep references to it.

        :raise StateError: If this channel is already destroyed.
        :raise StateError: If this channel is in use.
        '''

        if self._server is None:
            raise StateError('Channel already destroyed')

        if self._use:
            raise StateError('Channel in use')

        del self._server._channels[id(self)]

        self._server = None

    def open(self, timeout=3):
        '''
        Opens this channel.

        :param timeout: The request timeout in seconds.
        :type timeout: int

        :return: A task that can be awaited to obtain the return value of the
            initialization function.
        :rtype: asyncio.Task
        '''
        return asyncio.create_task(self._open(timeout))

    def close(self, timeout=3):
        '''
        Closes this channel.

        :param timeout: The request timeout in seconds.
        :type timeout: int

        :return: A task that can be awaited to ensure the closure is complete.
        :rtype: asyncio.Task
        '''
        return asyncio.create_task(self._close(timeout))

    def echo(self, *args, timeout=3):
        '''
        Sends arguments to the server and receives them back.

        Under normal circumstances, this method should not be called. It should
        only be called for debugging or testing purposes.

        It is particularly useful to verify whether the arguments are robust to
        JSON serialization and deserialization.

        :param args: The arguments.

        :param timeout: The request timeout in seconds.
        :type timeout: int

        :return: A task that can be awaited to obtain the same arguments as a
            list.
        :rtype: asyncio.Task[list]
        '''
        return asyncio.create_task(self._echo(args, timeout))

    def call(self, name, *args, timeout=3):
        '''
        Makes a call to the server.

        :param name: The name of a client handler method.
        :type name: str

        :param args: The arguments of the call.

        :param timeout: The request timeout in seconds.
        :type timeout: int

        :return: A task that can be awaited to obtain the return value of the
            method.
        :rtype: asyncio.Task
        '''
        return asyncio.create_task(self._call(name, args, timeout))

    @property
    def handler(self):
        '''
        The object that handles calls from the client.
        '''
        return self._handler

    @handler.setter
    def handler(self, value):
        if value is None:
            raise ValueError('Handler cannot be None')
        self._handler = value

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
        result = await self._send('open', self._code, None, None, timeout)
        self._use = True
        return result

    async def _close(self, timeout):
        result = await self._send('close', None, None, None, timeout)
        self._use = False
        return result

    async def _echo(self, args, timeout):
        return await self._send('echo', args, None, None, timeout)

    async def _call(self, name, args, timeout):
        return await self._send('call', {'name': name, 'args': args}, None, None, timeout)

    async def _send(self, body_type, input, producer, consumer, timeout):
        if self._server is None:
            raise StateError('Channel is destroyed')

        future = await self._server._send(body_type, id(self), input, producer, consumer, timeout)

        try:
            return await future
        except StateError:
            logging.warning('Channel is closed: trying to open...')

            await self._open(timeout)

            future = await self._server._send(body_type, id(self), input, producer, consumer, timeout)

            return await future
