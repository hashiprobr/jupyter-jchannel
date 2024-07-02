import asyncio

from abc import ABC, abstractmethod


class StateError(Exception):
    pass


class JavascriptError(Exception):
    pass


class AbstractServer(ABC):
    def __init__(self):
        self._channels = {}

    @abstractmethod
    async def _send(self, body_type, channel_key, input, stream, timeout):
        '''
        Sends WebSocket message.
        '''


class MetaGenerator:
    def __init__(self, reader):
        self._reader = reader

        self._dryup = asyncio.Event()

    async def _drain(self):
        try:
            async for _ in self._reader.iter_any():
                pass
        finally:
            self._dryup.set()

    async def by_limit(self, limit=8192):
        try:
            async for chunk in self._reader.iter_chunked(limit):
                yield chunk
        finally:
            self._dryup.set()

    async def by_separator(self, separator=b'\n'):
        try:
            while True:
                chunk = await self._reader.readuntil(separator)

                if chunk:
                    yield chunk
                else:
                    break
        finally:
            self._dryup.set()
