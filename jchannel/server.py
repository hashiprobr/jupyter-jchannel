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


class DebugScenario(Enum):
    READ_CONNECTION_REFERENCE_AFTER_REFERENCE_IS_NONE = auto()
    READ_CONNECTION_RESULT_BEFORE_REFERENCE_IS_NONE = auto()
    READ_DISCONNECTION_STATE_AFTER_RESULT_IS_SET = auto()
    READ_DISCONNECTION_RESULT_BEFORE_OBJECT_IS_REPLACED = auto()
    READ_SOCKET_STATE_BEFORE_SOCKET_IS_PREPARED = auto()
    RECEIVE_SOCKET_REQUEST_BEFORE_SERVER_IS_STOPPED = auto()
    RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED = auto()


class DebugEvent(asyncio.Event):
    def __init__(self, scenario):
        super().__init__()
        self.scenario = scenario
        self.count = 0


class DebugSentinel:
    def __init__(self):
        self.event = None

    def enable(self, scenario):
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
            self.event = None
            await asyncio.sleep(0)


class Server(AbstractServer):
    def __init__(self, host='localhost', port=8889, url=None, heartbeat=30):
        if not isinstance(host, str):
            raise TypeError('Host must be a string')

        if not isinstance(port, int):
            raise TypeError('Port must be an integer')

        if port < 0:
            raise ValueError('Port must be non-negative')

        if url is None:
            url = f'ws://{host}:{port}'
        else:
            if not isinstance(url, str):
                raise TypeError('URL must be a string')

            if not url.startswith('ws'):
                raise ValueError('URL must start with ws')

            if url[2] == 's':
                start = 6
            else:
                start = 5

            if url[(start - 3):start] != '://':
                raise ValueError('URL must start with ws:// or wss://')

            end = len(url) - 1
            while end >= start and url[end] == '/':
                end -= 1

            if end < start:
                raise ValueError('URL authority cannot be empty')

            url = url[:(end + 1)]

        if not isinstance(heartbeat, int):
            raise TypeError('Heartbeat must be an integer')

        if heartbeat <= 0:
            raise ValueError('Heartbeat must be positive')

        self._host = host
        self._port = port
        self._url = url
        self._heartbeat = heartbeat
        self._cleaned = None

        # None: user stoppage
        # web.WebSocketResponse: client connection
        self._connection = None

        # False: user stoppage
        # True: client disconnection
        self._disconnection = None

        if __debug__:  # pragma: no cover
            self._sentinel = DebugSentinel()

        self._registry = Registry()
        self._channels = {}

    def start(self):
        return asyncio.create_task(self._start())

    def stop(self):
        return asyncio.create_task(self._stop())

    def load(self):
        frontend.run(f"jchannel.start('{self._url}')")

    def open(self, code, timeout=3):
        channel = Channel(self, code)
        asyncio.create_task(self._open(channel, timeout))
        return channel

    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._stop()
        return False

    async def _start(self, scenario=None):
        if self._cleaned is None:
            self._cleaned = asyncio.Event()

            loop = asyncio.get_running_loop()
            self._connection = loop.create_future()
            self._disconnection = loop.create_future()

            if __debug__:  # pragma: no cover
                self._sentinel.enable(scenario)

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
            await site.start()

            asyncio.create_task(self._run(runner, site))

            self.load()

    async def _stop(self):
        if self._cleaned is not None:
            if __debug__:  # pragma: no cover
                await self._sentinel.wait_on_count(DebugScenario.READ_CONNECTION_REFERENCE_AFTER_REFERENCE_IS_NONE, 2)

            if self._connection is not None:
                if not self._connection.done():
                    self._connection.set_result(None)

            self._registry.clear()

            if self._disconnection is not None:
                if self._disconnection.done():
                    restarting = self._disconnection.result()

                    if __debug__:  # pragma: no cover
                        await self._sentinel.set_and_yield(DebugScenario.READ_DISCONNECTION_RESULT_BEFORE_OBJECT_IS_REPLACED)

                    if restarting:
                        raise StateError('Cannot stop server while restarting')
                else:
                    self._disconnection.set_result(False)

            await self._cleaned.wait()

    async def _run(self, runner, site):
        restarting = True

        while restarting:
            restarting = await self._disconnection

            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_DISCONNECTION_STATE_AFTER_RESULT_IS_SET)

            if restarting:
                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_DISCONNECTION_RESULT_BEFORE_OBJECT_IS_REPLACED, 1)

                loop = asyncio.get_running_loop()
                self._connection = loop.create_future()
                self._disconnection = loop.create_future()
            else:
                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_CONNECTION_RESULT_BEFORE_REFERENCE_IS_NONE, 1)

                self._connection = None
                self._disconnection = None

                if __debug__:  # pragma: no cover
                    await self._sentinel.set_and_yield(DebugScenario.READ_CONNECTION_REFERENCE_AFTER_REFERENCE_IS_NONE)

        if __debug__:  # pragma: no cover
            await self._sentinel.wait_on_count(DebugScenario.RECEIVE_SOCKET_REQUEST_BEFORE_SERVER_IS_STOPPED, 1)
            await self._sentinel.wait_on_count(DebugScenario.RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED, 1)

        await site.stop()
        await runner.cleanup()

        self._cleaned.set()
        self._cleaned = None

    async def _open(self, channel, timeout):
        try:
            await channel._open(timeout)
        except:
            logging.exception('Could not open channel')

    async def _reject(self, request):
        socket = web.WebSocketResponse()

        await socket.prepare(request)

        await socket.close()

        return socket

    async def _accept(self, socket, body_type, body):
        body['type'] = body_type

        data = json.dumps(body)

        await socket.send_str(data)

    async def _send(self, body_type, input, channel_key, timeout):
        if not isinstance(timeout, int):
            raise TypeError('Timeout must be an integer')

        if timeout < 0:
            raise ValueError('Timeout must be non-negative')

        if self._connection is None:
            socket = None
        else:
            self.load()

            try:
                socket = await asyncio.wait_for(asyncio.shield(self._connection), timeout)
            except asyncio.TimeoutError:
                raise StateError('Client timed out: check the browser console for details')

        if socket is None:
            raise StateError('Server not running')

        if not socket.prepared:
            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_SOCKET_STATE_BEFORE_SOCKET_IS_PREPARED)

            raise StateError('Server not prepared')

        if socket.closed:
            raise StateError('Server not connected')

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

    async def _on_shutdown(self, app):
        if app.socket is not None:
            await app.socket.close()

    async def _handle_socket(self, request):
        if __debug__:  # pragma: no cover
            await self._sentinel.set_and_yield(DebugScenario.RECEIVE_SOCKET_REQUEST_BEFORE_SERVER_IS_STOPPED)

        if self._connection is None:
            socket = await self._reject(request)
        else:
            if self._connection.done():
                socket = self._connection.result()

                if __debug__:  # pragma: no cover
                    await self._sentinel.set_and_yield(DebugScenario.READ_CONNECTION_RESULT_BEFORE_REFERENCE_IS_NONE)

                if socket is not None:
                    logging.warning('Received socket request while already connected')

                socket = await self._reject(request)
            else:
                socket = web.WebSocketResponse(heartbeat=self._heartbeat)

                self._connection.set_result(socket)

                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_SOCKET_STATE_BEFORE_SOCKET_IS_PREPARED, 1)

                await socket.prepare(request)

                request.app.socket = socket

                try:
                    async for message in socket:
                        if __debug__:  # pragma: no cover
                            await self._sentinel.set_and_yield(DebugScenario.RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED)

                        if message.type != WSMsgType.TEXT:
                            raise TypeError(f'Received unexpected message type {message.type}')

                        body = json.loads(message.data)

                        future_key = body['future']
                        channel_key = body['channel']
                        payload = body.pop('payload')
                        body_type = body.pop('type')

                        match body_type:
                            case 'closed':
                                logging.warning('Unexpected channel closure')

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
                                            payload = f'Received unexpected body type {body_type}'
                                            body_type = 'exception'
                                except:
                                    logging.exception('Caught handler exception')

                                    payload = 'Check the notebook log for details'
                                    body_type = 'exception'

                                body['payload'] = payload

                                await self._accept(socket, body_type, body)
                except:
                    logging.exception('Caught unexpected exception')

                request.app.socket = None

                self._registry.clear()

                if self._disconnection is not None:
                    if __debug__:  # pragma: no cover
                        await self._sentinel.wait_on_count(DebugScenario.READ_DISCONNECTION_STATE_AFTER_RESULT_IS_SET, 1)

                    if not self._disconnection.done():
                        logging.warning('Unexpected client disconnection')

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
