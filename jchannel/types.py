import asyncio
import logging

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
        except:
            self._done.set()

            raise

        return chunk

    async def _drain(self):
        if not self._done.is_set():
            try:
                async for _ in self:
                    pass
            except:
                logging.exception('Post reading exception')

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


# class MetaGenerator:
#     def __init__(self, queue):
#         self._queue = queue
#
#         self._done = asyncio.Event()
#
#     def __aiter__(self):
#         return self
#
#     async def __anext__(self):
#         try:
#             chunk = await self._queue.get()
#
#             if chunk is None:
#                 raise StopAsyncIteration
#         except:
#             self._done.set()
#
#             raise
#
#         return chunk
#
#     async def join(self):
#         buffer = bytearray()
#
#         async for chunk in self:
#             buffer.extend(chunk)
#
#         return bytes(buffer)
#
#     async def by_limit(self, limit=8192):
#         if not isinstance(limit, int):
#             raise TypeError('Limit must be an integer')
#
#         if limit <= 0:
#             raise ValueError('Limit must be positive')
#
#         buffer = bytearray(limit)
#
#         size = 0
#
#         async for data in self:
#             chunk = memoryview(data)
#             length = len(chunk)
#
#             begin = 0
#             end = limit - size
#
#             if length > end:
#                 buffer[size:] = chunk[begin:end]
#                 yield bytes(buffer)
#                 size = 0
#
#                 begin = end
#                 end += limit
#
#                 while end <= length:
#                     yield bytes(chunk[begin:end])
#
#                     begin = end
#                     end += limit
#
#                 chunk = chunk[begin:]
#                 length = len(chunk)
#
#             new_size = size + length
#
#             buffer[size:new_size] = chunk
#             size = new_size
#
#         if size > 0:
#             yield bytes(buffer[:size])
#
#     async def by_separator(self, separator=b'\n'):
#         separator = self._clean(separator)
#
#         if not separator:
#             raise ValueError('Separator cannot be empty')
#
#         buffer = bytearray()
#         size = 0
#         offset = 0
#
#         async for data in self:
#             chunk = memoryview(data)
#
#             buffer.extend(chunk)
#             size = len(buffer)
#
#             shift = 0
#
#             while offset <= size - len(separator):
#                 if self._match(buffer, offset, separator):
#                     offset += len(separator)
#                     view = memoryview(buffer)
#                     yield bytes(view[shift:offset])
#                     shift = offset
#                 else:
#                     offset += 1
#
#             if shift > 0:
#                 new_size = size - shift
#                 buffer[:new_size] = buffer[shift:size]
#                 size = new_size
#                 offset -= shift
#
#         if size > 0:
#             yield bytes(buffer[:size])
#
#     def _clean(self, separator):
#         if isinstance(separator, str):
#             return separator.encode()
#
#         if isinstance(separator, bytes):
#             return separator
#
#         raise TypeError('Separator must be a string or a bytes object')
#
#     def _match(self, buffer, offset, separator):
#         i = offset
#         j = 0
#
#         while j < len(separator):
#             if buffer[i] != separator[j]:
#                 return False
#
#             i += 1
#             j += 1
#
#         return True
