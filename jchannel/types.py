from abc import ABC, abstractmethod


class StateError(Exception):
    pass


class JavascriptError(Exception):
    pass


class AbstractServer(ABC):
    _channels: dict

    @abstractmethod
    async def _send(self, body_type, input, channel_key, timeout):
        '''
        Sends socket message.
        '''
