from abc import ABC, abstractmethod


class StateError(Exception):
    pass


class JavascriptError(Exception):
    pass


class AbstractServer(ABC):
    def __init__(self):
        self._channels = {}

    @abstractmethod
    async def _send(self, body_type, channel_key, input, producer, consumer, timeout):
        '''
        Sends WebSocket message.
        '''
