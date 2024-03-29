import json
import asyncio
import logging

from enum import Enum, auto
from aiohttp import web, WSMsgType
from jchannel.frontend import frontend


class StateError(Exception):
    pass


class DebugScenario(Enum):
    STOP_BEFORE_RESTART = auto()
    STOP_AFTER_BREAK = auto()
    CONNECT_BEFORE_BREAK = auto()
    CONNECT_BEFORE_CLEAN = auto()
    RECEIVE_BEFORE_CLEAN = auto()
    CATCH_BEFORE_CLEAN = auto()
    DISCONNECT_AFTER_STOP = auto()
    SEND_BEFORE_PREPARE = auto()


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


class Server:
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

        self.host = host
        self.port = port
        self.url = url
        self.heartbeat = heartbeat
        self.cleaned = None
        self.sentinel = DebugSentinel()

        # None: user stoppage
        # web.WebSocketResponse: client connection
        self.connection = None

        # False: user stoppage
        # True: client disconnection
        self.disconnection = None

    def start(self):
        return asyncio.create_task(self._start())

    def stop(self):
        return asyncio.create_task(self._stop())

    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._stop()
        return False

    async def _start(self, scenario=None):
        if self.cleaned is None:
            self.cleaned = asyncio.Event()

            self.sentinel.enable(scenario)

            loop = asyncio.get_running_loop()
            self.connection = loop.create_future()
            self.disconnection = loop.create_future()

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

            site = web.TCPSite(runner, self.host, self.port)
            await site.start()

            frontend.run(f"jchannel.start('{self.url}')")

            asyncio.create_task(self._run(runner, site))

    async def _stop(self):
        await self.sentinel.wait_on_count(DebugScenario.STOP_AFTER_BREAK, 2)

        try:
            if self.cleaned is not None:
                if self.connection is not None:
                    if not self.connection.done():
                        self.connection.set_result(None)

                if self.disconnection is not None:
                    if self.disconnection.done():
                        restarting = self.disconnection.result()

                        if restarting:
                            raise StateError('Cannot stop server while restarting')
                    else:
                        self.disconnection.set_result(False)

                await self.cleaned.wait()
        finally:
            await self.sentinel.set_and_yield(DebugScenario.STOP_BEFORE_RESTART)

    async def _run(self, runner, site):
        restarting = True

        while restarting:
            try:
                await self.connection
            except asyncio.CancelledError:
                pass

            restarting = await self.disconnection

            if restarting:
                await self.sentinel.wait_on_count(DebugScenario.STOP_BEFORE_RESTART, 1)

                loop = asyncio.get_running_loop()
                self.connection = loop.create_future()
                self.disconnection = loop.create_future()
            else:
                await self.sentinel.set_and_yield(DebugScenario.DISCONNECT_AFTER_STOP)
                await self.sentinel.wait_on_count(DebugScenario.CONNECT_BEFORE_BREAK, 1)

                self.connection = None
                self.disconnection = None

        await self.sentinel.set_and_yield(DebugScenario.STOP_AFTER_BREAK)
        await self.sentinel.wait_on_count(DebugScenario.CONNECT_BEFORE_CLEAN, 1)
        await self.sentinel.wait_on_count(DebugScenario.RECEIVE_BEFORE_CLEAN, 1)
        await self.sentinel.wait_on_count(DebugScenario.CATCH_BEFORE_CLEAN, 1)

        await site.stop()
        await runner.cleanup()

        self.cleaned.set()
        self.cleaned = None

    async def _reject(self, request):
        socket = web.WebSocketResponse()

        await socket.prepare(request)

        await socket.close()

        return socket

    async def _send(self, body_type, body={}, timeout=3):
        try:
            if self.connection is None:
                socket = None
            else:
                try:
                    socket = await asyncio.wait_for(self.connection, timeout)
                except asyncio.TimeoutError:
                    raise StateError('Client not connected: check the browser console for details')

            if socket is None:
                raise StateError('Server not running')

            if not socket.prepared:
                raise StateError('Server not prepared')

            body['type'] = body_type
            data = json.dumps(body)

            await socket.send_str(data)
        finally:
            await self.sentinel.set_and_yield(DebugScenario.SEND_BEFORE_PREPARE)

    async def _on_shutdown(self, app):
        if app.socket is not None:
            await app.socket.close()

    async def _handle_socket(self, request):
        if self.connection is None:
            socket = await self._reject(request)
        else:
            if self.connection.done():
                socket = self.connection.result()

                if socket is not None:
                    logging.warning('Received socket request while already connected')

                socket = await self._reject(request)
            else:
                socket = web.WebSocketResponse(heartbeat=self.heartbeat)

                self.connection.set_result(socket)

                await self.sentinel.wait_on_count(DebugScenario.SEND_BEFORE_PREPARE, 1)

                await socket.prepare(request)

                request.app.socket = socket

                try:
                    async for message in socket:
                        if message.type == WSMsgType.TEXT:
                            body = json.loads(message.data)
                            body_type = body.pop('type')

                            match body_type:
                                case _:
                                    logging.error(f'Received unexpected body type {body_type}')
                        else:
                            logging.error(f'Received unexpected message type {message.type}')

                        await self.sentinel.set_and_yield(DebugScenario.RECEIVE_BEFORE_CLEAN)
                except Exception:
                    logging.exception('Caught unexpected exception')

                    await self.sentinel.set_and_yield(DebugScenario.CATCH_BEFORE_CLEAN)
                finally:
                    request.app.socket = None

                await self.sentinel.wait_on_count(DebugScenario.DISCONNECT_AFTER_STOP, 1)

                if self.disconnection is not None:
                    if not self.disconnection.done():
                        logging.warning('Unexpected client disconnection')

                        self.disconnection.set_result(True)

        await self.sentinel.set_and_yield(DebugScenario.CONNECT_BEFORE_BREAK)
        await self.sentinel.set_and_yield(DebugScenario.CONNECT_BEFORE_CLEAN)

        return socket

    async def _handle_get(self, request):
        '''
        TODO
        '''

    async def _handle_post(self, request):
        '''
        TODO
        '''
