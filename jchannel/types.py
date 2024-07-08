import asyncio

from abc import ABC, abstractmethod


class StateError(Exception):
    '''
    Indicates that an operation could not be performed because the performer is
    in an invalid state.

    For example, a message could not be sent because the server is not
    connected.
    '''


class FrontendError(Exception):
    '''
    Indicates that an operation could not be performed in the frontend.

    Contains a simple message or the string representation of a frontend
    exception.
    '''


class AbstractServer(ABC):
    def __init__(self):
        self._channels = {}

    @abstractmethod
    async def _send(self, body_type, channel_key, input, stream, timeout):
        '''
        Sends WebSocket message.
        '''


class MetaGenerator:
    '''
    Provides generators to read a frontend stream.
    '''

    def __init__(self, reader):
        self._reader = reader

        self._done = asyncio.Event()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            chunk = await self._reader.readany()

            if not chunk:
                raise StopAsyncIteration
        finally:
            self._done.set()

        return chunk

    async def join(self):
        '''
        Convenience method that joins all chunks into one.

        :return: The joined stream chunks.
        :rtype: bytes
        '''
        buffer = bytearray()

        async for chunk in self:
            buffer.extend(chunk)

        return bytes(buffer)

    async def by_limit(self, limit=8192):
        '''
        Provides chunks with maximum size limit.

        :param limit: The size limit.
        :type limit: int

        :return: An async generator of stream chunks.
        :rtype: async_generator[bytes]
        '''
        try:
            async for chunk in self._reader.iter_chunked(limit):
                yield chunk
        finally:
            self._done.set()

    async def by_separator(self, separator=b'\n'):
        '''
        Provides chunks according to a separator.

        :param separator: The split separator.
        :type separator: bytes

        :return: An async generator of stream chunks.
        :rtype: async_generator[bytes]
        '''
        try:
            while True:
                chunk = await self._reader.readuntil(separator)

                if chunk:
                    yield chunk
                else:
                    break
        finally:
            self._done.set()
