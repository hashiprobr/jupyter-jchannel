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

        self._ended = asyncio.Event()

    def __aiter__(self):
        async def generate():
            try:
                async for chunk in self._reader.iter_any():
                    yield chunk
            finally:
                self._ended.set()

        return generate()

    async def join(self):
        '''
        Convenience method that joins all chunks into one.

        :return: The joined stream chunks as an array.
        :rtype: bytearray
        '''
        content = bytearray()

        async for chunk in self:
            content.extend(chunk)

        return content

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
            self._ended.set()

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
            self._ended.set()
