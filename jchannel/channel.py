class Channel:
    def __init__(self, server):
        server.channels[id(self)] = self

        self.server = server
        self.handler = None

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

    async def echo(self, *args, timeout=3):
        return await self._send('echo', args, timeout)

    async def call(self, name, *args, timeout=3):
        return await self._send('call', {'name': name, 'args': args}, timeout)

    async def _send(self, body_type, input, timeout):
        future = await self.server._send(body_type, input, id(self), timeout)

        return await future
