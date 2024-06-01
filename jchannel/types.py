from abc import ABC, abstractmethod


class StateError(Exception):
    pass


class JavascriptError(Exception):
    pass


class AbstractServer(ABC):
    def __init__(self):
        self._channels = {}

    @abstractmethod
    async def _send(self, body_type, input, channel_key, timeout):
        '''
        Sends WebSocket message.
        '''
