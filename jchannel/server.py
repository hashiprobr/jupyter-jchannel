import json
import asyncio
import logging

from enum import Enum, auto
from inspect import isawaitable
from aiohttp import web, WSMsgType
from jchannel.types import AbstractServer, JavascriptError, StateError
from jchannel.registry import Registry
from jchannel.channel import Channel
from jchannel.frontend import frontend


if __debug__:  # pragma: no cover
    class DebugScenario(Enum):
        HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED = auto()
        READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED = auto()
        READ_SESSION_REFERENCES_AFTER_SESSION_REFERENCES_ARE_NONE = auto()
        READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE = auto()
        READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET = auto()

    class DebugEvent(asyncio.Event):
        def __init__(self, scenario):
            super().__init__()
            self.scenario = scenario
            self.count = 0

    class DebugSentinel:
        def __init__(self):
            self.event = None

        def watch(self, scenario):
            if scenario is not None:
                self.event = DebugEvent(scenario)

        async def wait_on_count(self, scenario, count):
            if self.event is not None and self.event.scenario == scenario:
                self.event.count += 1
                if self.event.count == count:
                    await self.event.wait()

        async def set_and_yield(self, scenario):
            if self.event is not None and self.event.scenario == scenario:
                self.event.set()
                await asyncio.sleep(0)


class Server(AbstractServer):
    def __init__(self, host='localhost', port=8889, url=None, heartbeat=30):
        '''
        Represents a kernel server.

        :param host: The host name.
        :type host: str

        :param port: The port number.
        :type port: int

        :param url: The URL accessed by the client. If ``None``, it is simply
            ``f'http://{host}:{port}'``. If not ``None``, it is particularly
            useful when the kernel is behind a proxy like `ngrok
            <https://ngrok.com/>`_.
        :type url: str or None

        :param heartbeat: The WebSocket heartbeat interval in seconds.
        :type heartbeat: int
        '''

        if not isinstance(host, str):
            raise TypeError('Host must be a string')

        host = host.strip()

        if not host:
            raise ValueError('Host cannot be blank')

        if '/' in host:
            raise ValueError('Host cannot have slashes')

        if not isinstance(port, int):
            raise TypeError('Port must be an integer')

        if port < 0:
            raise ValueError('Port must be non-negative')

        if url is None:
            url = f'http://{host}:{port}'
        else:
            if not isinstance(url, str):
                raise TypeError('URL must be a string')

            url = url.strip()

            if not url.startswith('http'):
                raise ValueError('URL must start with http')

            if url[4:5] == 's':
                start = 8
            else:
                start = 7

            if url[(start - 3):start] != '://':
                raise ValueError('URL must start with http:// or https://')

            if start == len(url) or url[start] == '/':
                raise ValueError('URL authority cannot be empty')

            end = len(url) - 1
            while url[end] == '/':
                end -= 1

            url = url[:(end + 1)]

        if not isinstance(heartbeat, int):
            raise TypeError('Heartbeat must be an integer')

        if heartbeat <= 0:
            raise ValueError('Heartbeat must be positive')

        self._host = host
        self._port = port
        self._url = url
        self._heartbeat = heartbeat

        self._cleaned = asyncio.Event()
        self._cleaned.set()

        # None: user stoppage
        # web.WebSocketResponse: client connection
        self._connection = None

        # False: user stoppage
        # True: client disconnection
        self._disconnection = None

        if __debug__:  # pragma: no cover
            self._sentinel = DebugSentinel()

        self._registry = Registry()
        super().__init__()

    def start_client(self):
        '''
        Starts the frontend client.

        Under normal circumstances, this method should not be called. It should
        only be called for debugging or testing purposes.
        '''
        frontend.run(f"jchannel.start('{self._url}')")

    def stop_client(self):
        '''
        Stops the frontend client.

        Under normal circumstances, this method should not be called. It should
        only be called for debugging or testing purposes.
        '''
        frontend.run(f"jchannel.stop('{self._url}')")

    def start(self):
        '''
        Starts this server.

        :return: A task that can be awaited to ensure the startup is complete.
        :rtype: asyncio.Task
        '''
        return asyncio.create_task(self._start())

    def stop(self):
        '''
        Stops this server.

        :return: A task that can be awaited to ensure the shutdown is complete.
        :rtype: asyncio.Task
        '''
        return asyncio.create_task(self._stop())

    async def open(self, code, timeout=3):
        '''
        Convenience method that instantiates a communication channel, opens this
        channel and returns it.

        :param code: As defined in `jchannel.channel.Channel
            <jchannel.channel.html#jchannel.channel.Channel>`_.
        :param timeout: As defined in `jchannel.channel.Channel.open
            <jchannel.channel.html#jchannel.channel.Channel.open>`_.

        :return: The channel.
        :rtype: jchannel.channel.Channel
        '''
        channel = Channel(self, code)
        try:
            await channel._open(timeout)
        except Exception as error:
            channel.destroy()
            raise error
        return channel

    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._stop()
        return False

    async def _start(self, scenario=None):
        if self._cleaned.is_set():
            self._cleaned.clear()

            loop = asyncio.get_running_loop()
            self._connection = loop.create_future()
            self._disconnection = loop.create_future()

            if __debug__:  # pragma: no cover
                self._sentinel.watch(scenario)

            app = web.Application()

            app.socket = None

            app.on_shutdown.append(self._on_shutdown)

            app.add_routes([
                web.get('/socket', self._handle_socket),
                web.get('/', self._handle_get),
                web.post('/', self._handle_post),
            ])

            runner = web.AppRunner(app)

            await runner.setup()

            site = web.TCPSite(runner, self._host, self._port)

            try:
                await site.start()
            except OSError as error:
                if not self._connection.done():
                    self._connection.set_result(None)

                if not self._disconnection.done():
                    self._disconnection.set_result(False)

                self._connection = None
                self._disconnection = None

                await runner.cleanup()

                self._cleaned.set()

                raise error

            self.start_client()

            asyncio.create_task(self._run(runner))

    async def _stop(self):
        if not self._cleaned.is_set():
            if __debug__:  # pragma: no cover
                await self._sentinel.wait_on_count(DebugScenario.READ_SESSION_REFERENCES_AFTER_SESSION_REFERENCES_ARE_NONE, 2)

            if self._connection is not None:
                if not self._connection.done():
                    self._connection.set_result(None)

            if self._disconnection is not None:
                if self._disconnection.done():
                    if self._disconnection.result():
                        raise StateError('Server is restarting')
                else:
                    self._disconnection.set_result(False)

            await self._cleaned.wait()

    async def _run(self, runner):
        while True:
            restart = await self._disconnection

            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET)

            self._registry.clear()

            if restart:
                loop = asyncio.get_running_loop()
                self._connection = loop.create_future()
                self._disconnection = loop.create_future()
            else:
                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE, 1)

                self._connection = None
                self._disconnection = None

                if __debug__:  # pragma: no cover
                    await self._sentinel.set_and_yield(DebugScenario.READ_SESSION_REFERENCES_AFTER_SESSION_REFERENCES_ARE_NONE)

                break

        frontend.run(f"jchannel._unload('{self._url}')")

        if __debug__:  # pragma: no cover
            await self._sentinel.wait_on_count(DebugScenario.HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED, 1)

        await runner.cleanup()

        self._cleaned.set()

    async def _send(self, body_type, channel_key, input, producer, consumer, timeout):
        if not isinstance(timeout, int):
            raise TypeError('Timeout must be an integer')

        if timeout < 0:
            raise ValueError('Timeout must be non-negative')

        if self._connection is None:
            socket = None
        else:
            self.start_client()

            try:
                socket = await asyncio.wait_for(asyncio.shield(self._connection), timeout)
            except asyncio.TimeoutError:
                raise StateError('Server not connected') from None

        if socket is None:
            raise StateError('Server not running')

        if not socket.prepared:
            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED)

            raise StateError('Server not prepared')

        if socket.closed:
            raise StateError('Server has disconnected')

        payload = json.dumps(input)

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        body = {
            'future': self._registry.store(future),
            'channel': channel_key,
            'payload': payload,
        }

        await self._accept(socket, body_type, body)

        return future

    async def _accept(self, socket, body_type, body):
        body['type'] = body_type

        data = json.dumps(body)

        await socket.send_str(data)

    async def _on_shutdown(self, app):
        if app.socket is not None:
            await app.socket.close()

    async def _handle_socket(self, request):
        if __debug__:  # pragma: no cover
            await self._sentinel.set_and_yield(DebugScenario.HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED)

        if self._connection is None:
            return web.Response(status=404)

        if self._connection.done():
            socket = self._connection.result()

            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE)

            if socket is None:
                status = 404
            else:
                status = 409

            return web.Response(status=status)

        socket = web.WebSocketResponse(heartbeat=self._heartbeat)

        self._connection.set_result(socket)

        if __debug__:  # pragma: no cover
            await self._sentinel.wait_on_count(DebugScenario.READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED, 1)

        await socket.prepare(request)

        request.app.socket = socket

        try:
            async for message in socket:
                if message.type != WSMsgType.TEXT:
                    raise TypeError(f'Unexpected message type {message.type}')

                body = json.loads(message.data)

                future_key = body['future']
                channel_key = body['channel']
                payload = body.pop('payload')
                body_type = body.pop('type')

                match body_type:
                    case 'closed':
                        future = self._registry.retrieve(future_key)
                        future.set_exception(StateError)
                    case 'exception':
                        future = self._registry.retrieve(future_key)
                        future.set_exception(JavascriptError(payload))
                    case 'result':
                        output = json.loads(payload)

                        future = self._registry.retrieve(future_key)
                        future.set_result(output)
                    case _:
                        input = json.loads(payload)

                        channel = self._channels[channel_key]

                        try:
                            match body_type:
                                case 'echo':
                                    body_type = 'result'
                                case 'call':
                                    output = channel._handle_call(input['name'], input['args'])
                                    if isawaitable(output):
                                        output = await output

                                    payload = json.dumps(output)
                                    body_type = 'result'
                                case _:
                                    payload = f'Unexpected body type {body_type}'
                                    body_type = 'exception'
                        except Exception as error:
                            logging.exception('Channel request exception')

                            payload = f'{error.__class__.__name__}: {str(error)}'
                            body_type = 'exception'

                        body['payload'] = payload

                        await self._accept(socket, body_type, body)
        except:
            logging.exception('Socket message exception')

            await socket.close()

        request.app.socket = None

        if self._disconnection is not None:
            if __debug__:  # pragma: no cover
                await self._sentinel.wait_on_count(DebugScenario.READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET, 1)

            if not self._disconnection.done():
                self._disconnection.set_result(True)

        return socket

    async def _handle_get(self, request):
        '''
        TODO
        '''

    async def _handle_post(self, request):
        '''
        TODO
        '''
