import os
import json
import asyncio
import logging

from enum import Enum, auto
from aiohttp import web, WSMsgType
from jchannel.frontend import frontend


class DebugScenario(Enum):
    STOP_BETWEEN_STOP_AND_CLEAN = auto()
    STOP_BETWEEN_DISCONNECT_AND_RESTART = auto()
    RESTART_BETWEEN_DISCONNECT_AND_STOP = auto()


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
            if 'COLAB_RELEASE_TAG' in os.environ:
                scheme = 'https'
            else:
                scheme = 'http'

            url = f'{scheme}://{host}:{port}'
        else:
            if not isinstance(url, str):
                raise TypeError('URL must be a string')

            if not url.startswith('http'):
                raise ValueError('URL must start with http')

            if url[4] == 's':
                start = 8
            else:
                start = 7

            if url[(start - 3):start] != '://':
                raise ValueError('URL must start with http:// or https://')

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

    async def _start(self, scenario=None):
        if self.cleaned is None:
            self.cleaned = asyncio.Event()

            if scenario is not None:
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

            frontend.inject_code(f'jchannel.start("{self.url}");')

            asyncio.create_task(self._run(runner, site))

    async def _stop(self):
        await self.sentinel.wait_on_count(DebugScenario.STOP_BETWEEN_STOP_AND_CLEAN, 2)
        await self.sentinel.wait_on_count(DebugScenario.STOP_BETWEEN_DISCONNECT_AND_RESTART, 1)

        if self.cleaned is not None:
            if self.connection is not None:
                if not self.connection.done():
                    self.connection.set_result(None)

            if self.disconnection is not None:
                if self.disconnection.done():
                    restarting = self.disconnection.result()

                    if restarting:
                        raise RuntimeError('Cannot stop server while restarting')
                else:
                    self.disconnection.set_result(False)

            await self.cleaned.wait()

    async def _run(self, runner, site):
        restarting = True

        while restarting:
            await self.connection

            restarting = await self.disconnection

            await self.sentinel.set_and_yield(DebugScenario.STOP_BETWEEN_DISCONNECT_AND_RESTART)
            await self.sentinel.wait_on_count(DebugScenario.RESTART_BETWEEN_DISCONNECT_AND_STOP, 1)

            if restarting:
                loop = asyncio.get_running_loop()
                self.connection = loop.create_future()
                self.disconnection = loop.create_future()
            else:
                self.connection = None
                self.disconnection = None

        await self.sentinel.set_and_yield(DebugScenario.STOP_BETWEEN_STOP_AND_CLEAN)

        await site.stop()
        await runner.cleanup()

        self.cleaned.set()
        self.cleaned = None

    async def _reject(self, request):
        socket = web.WebSocketResponse()
        await socket.prepare(request)

        await socket.close()

        return socket

    async def _send(self, data_type, **kwargs):
        if self.connection is None:
            socket = None
        else:
            socket = await self.connection

        if socket is None:
            raise RuntimeError('Server not running')

        kwargs['type'] = data_type
        data = json.dumps(kwargs)

        await socket.send_str(data)

    async def _on_shutdown(self, app):
        if app.socket is not None:
            await app.socket.close()

    async def _handle_socket(self, request):
        if self.connection is None:
            return self._reject()

        if self.connection.done():
            socket = self.connection.result()

            if socket is not None:
                logging.error('Received socket request while already connected')

            return self._reject()

        socket = web.WebSocketResponse(heartbeat=self.heartbeat)
        await socket.prepare(request)

        self.connection.set_result(socket)

        request.app.socket = socket

        async for message in socket:
            if message.type == WSMsgType.TEXT:
                kwargs = json.loads(message.data)
                data_type = kwargs.pop('type')

                match data_type:
                    case _:
                        logging.error(f'Received unexpected data type {data_type}')
            else:
                logging.error(f'Received unexpected message type {message.type}')

        request.app.socket = None

        if self.disconnection is not None:
            if not self.disconnection.done():
                self.disconnection.set_result(True)

        await self.sentinel.set_and_yield(DebugScenario.RESTART_BETWEEN_DISCONNECT_AND_STOP)

        return socket

    async def _handle_get(self, request):
        response = web.Response()
        return response

    async def _handle_post(self, request):
        response = web.Response()
        return response


try:
    url = os.environ['JCHANNEL_CLIENT_URL']
except KeyError:
    url = 'TODO'

frontend.inject_file(url)
