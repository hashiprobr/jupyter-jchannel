import json
import asyncio
import logging

from enum import Enum, auto
from inspect import isawaitable
from aiohttp import web, WSMsgType
from jchannel.types import AbstractServer, MetaGenerator, StreamQueue, AbortError, FrontendError, StateError
from jchannel.registry import Registry
from jchannel.channel import Channel
from jchannel.frontend import frontend


HEADERS = {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': '*',
    'access-control-allow-headers': '*',
}


if __debug__:  # pragma: no cover
    class DebugScenario(Enum):
        HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED = auto()
        READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED = auto()
        READ_SESSION_REFERENCES_AFTER_SESSION_REFERENCES_ARE_NONE = auto()
        READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE = auto()
        READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET = auto()
        READ_DISCONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NEW = auto()

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

        self._high_water_mark = 1
        self._send_timeout = 3
        self._receive_timeout = None
        self._max_msg_size = 4194304
        self._keepalive_timeout = 75
        self._shutdown_timeout = 60

        self._cleaned = asyncio.Event()
        self._cleaned.set()

        # None: user stoppage
        # Socket: client connection
        self._connection = None

        # False: user stoppage
        # True: client disconnection
        self._disconnection = None

        if __debug__:  # pragma: no cover
            self._sentinel = DebugSentinel()

        # self._events = set()

        self._queues = {}

        self._streams = {}

        self._registry = Registry()
        super().__init__()

    @property
    def high_water_mark(self):
        return self._high_water_mark

    @high_water_mark.setter
    def high_water_mark(self, value):
        self._high_water_mark = value

    @property
    def send_timeout(self):
        '''
        The post send timeout in seconds. Default is 3.

        When this server receives a post request, this timeout is used to send a
        WebSocket response message.
        '''
        return self._send_timeout

    @send_timeout.setter
    def send_timeout(self, value):
        self._send_timeout = value

    @property
    def receive_timeout(self):
        '''
        As defined in `aiohttp.web.WebSocketResponse
        <https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.WebSocketResponse>`_.
        '''
        return self._receive_timeout

    @receive_timeout.setter
    def receive_timeout(self, value):
        self._receive_timeout = value

    @property
    def max_msg_size(self):
        '''
        As defined in `aiohttp.web.WebSocketResponse
        <https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.WebSocketResponse>`_.
        '''
        return self._max_msg_size

    @max_msg_size.setter
    def max_msg_size(self, value):
        self._max_msg_size = value

    @property
    def keepalive_timeout(self):
        '''
        As defined in `aiohttp.web.AppRunner
        <https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.AppRunner>`_.
        '''
        return self._keepalive_timeout

    @keepalive_timeout.setter
    def keepalive_timeout(self, value):
        self._keepalive_timeout = value

    @property
    def shutdown_timeout(self):
        '''
        As defined in `aiohttp.web.TCPSite
        <https://docs.aiohttp.org/en/stable/web_reference.html#aiohttp.web.TCPSite>`_.
        '''
        return self._shutdown_timeout

    @shutdown_timeout.setter
    def shutdown_timeout(self, value):
        self._shutdown_timeout = value

    def start_client(self):
        '''
        Starts the frontend client.

        Under normal circumstances, this method should not be called. It should
        only be called for debugging or testing purposes.
        '''
        frontend.run(f"jchannel.start('{self._url}', {self._max_msg_size})")

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
        except:
            channel.destroy()
            raise
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
                web.get('/upload', self._handle_upload),
                web.get('/', self._handle_get),
                web.post('/', self._handle_post),
                web.options('/', self._allow),
            ])

            runner = web.AppRunner(app, keepalive_timeout=self._keepalive_timeout)

            await runner.setup()

            site = web.TCPSite(runner, self._host, self._port, shutdown_timeout=self._shutdown_timeout)

            try:
                await site.start()
            except OSError:
                if not self._connection.done():
                    self._connection.set_result(None)

                if not self._disconnection.done():
                    self._disconnection.set_result(False)

                self._connection = None
                self._disconnection = None

                await runner.cleanup()

                self._cleaned.set()

                raise

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
                    restart = self._disconnection.result()

                    if __debug__:  # pragma: no cover
                        await self._sentinel.set_and_yield(DebugScenario.READ_DISCONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NEW)

                    if restart:
                        raise StateError('Server was restarting')
                else:
                    self._disconnection.set_result(False)

            await self._cleaned.wait()

    async def _run(self, runner):
        while True:
            restart = await self._disconnection

            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET)

            if restart:
                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_DISCONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NEW, 1)

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

    async def _send(self, body_type, channel_key, input, stream, timeout):
        if stream is not None:
            try:
                stream = aiter(stream)
            except TypeError:
                raise TypeError('Stream must be an async iterable')

        if not isinstance(timeout, int):
            raise TypeError('Timeout must be an integer')

        if timeout < 0:
            raise ValueError('Timeout must be non-negative')

        socket = await self._propose(timeout)

        payload = json.dumps(input)

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        body = {
            'future': self._registry.store(future),
            'channel': channel_key,
            'payload': payload,
        }

        await self._accept(socket, body_type, body, stream)

        return future

    async def _propose(self, timeout):
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

        return socket

    async def _accept(self, socket, body_type, body, stream):
        if stream is None:
            stream_key = None
        else:
            stream_key = id(stream)
            self._streams[stream_key] = stream

        body['stream'] = stream_key
        body['type'] = body_type

        data = json.dumps(body)

        await socket.send_str(data)

    async def _call(self, channel, input, chunks):
        name = input.pop('name')
        args = input.pop('args')

        if not isinstance(name, str):
            raise TypeError('Name must be a string')

        if not isinstance(args, list):
            raise TypeError('Args must be a list')

        if chunks is not None:
            args.insert(0, chunks)

        output = channel._handle(name, args)
        if isawaitable(output):
            output = await output

        try:
            return aiter(output), 'null'
        except TypeError:
            return None, json.dumps(output)

    async def _on_message(self, socket, message):
        try:
            if message.type != WSMsgType.TEXT:
                raise TypeError(f'Unexpected socket message type {message.type}')

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
                    future.set_exception(FrontendError(payload))
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
                                stream = None
                                body_type = 'result'
                            case 'call':
                                stream, payload = await self._call(channel, input, None)
                                body_type = 'result'
                            case _:
                                stream = None
                                payload = f'Unexpected socket body type {body_type}'
                                body_type = 'exception'
                    except Exception as error:
                        logging.exception('Socket request exception')

                        stream = None
                        payload = f'{error.__class__.__name__}: {str(error)}'
                        body_type = 'exception'

                    body['payload'] = payload

                    await self._accept(socket, body_type, body, stream)
        except:
            logging.exception('Socket message exception')

            await socket.close()

    async def _on_shutdown(self, app):
        if app.socket is not None:
            await app.socket.close()

    async def _handle_socket(self, request):
        if __debug__:  # pragma: no cover
            await self._sentinel.set_and_yield(DebugScenario.HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED)

        if self._connection is None:
            return web.Response(status=503, headers=HEADERS)

        if self._connection.done():
            socket = self._connection.result()

            if __debug__:  # pragma: no cover
                await self._sentinel.set_and_yield(DebugScenario.READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE)

            if socket is None:
                status = 503
            else:
                status = 409

            return web.Response(status=status, headers=HEADERS)

        socket = web.WebSocketResponse(
            receive_timeout=self._receive_timeout,
            heartbeat=self._heartbeat,
            max_msg_size=self._max_msg_size,
        )

        self._connection.set_result(socket)

        if __debug__:  # pragma: no cover
            await self._sentinel.wait_on_count(DebugScenario.READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED, 1)

        await socket.prepare(request)

        tasks = set()

        def done_callback(task):
            tasks.remove(task)

        request.app.socket = socket
        try:
            async for message in socket:
                task = asyncio.create_task(self._on_message(socket, message))
                tasks.add(task)
                task.add_done_callback(done_callback)
        finally:
            request.app.socket = None

            while tasks:
                task = next(iter(tasks))
                await task
                task.remove_done_callback(done_callback)

            if self._disconnection is not None:
                if __debug__:  # pragma: no cover
                    await self._sentinel.wait_on_count(DebugScenario.READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET, 1)

                if not self._disconnection.done():
                    self._disconnection.set_result(True)

            # for event in self._events:
            #     event.set()

            for queue in self._queues.values():
                queue.abort()

            self._streams.clear()

            self._registry.clear()

        return socket

    async def _handle_upload(self, request):  # pseudo-stream
        socket = web.WebSocketResponse(
            receive_timeout=self._receive_timeout,
            heartbeat=self._heartbeat,
            max_msg_size=self._max_msg_size,
        )

        await socket.prepare(request)

        queue = StreamQueue(self._high_water_mark)

        queue_key = id(queue)
        self._queues[queue_key] = queue

        await socket.send_str(str(queue_key))

        try:
            async for message in socket:
                chunk = message.data

                if chunk:
                    await queue.put(chunk)
                else:
                    await socket.send_bytes(chunk)

            await queue.put(None)
        except AbortError:
            await socket.close()
        finally:
            del self._queues[queue_key]

        return socket

    async def _handle_get(self, request):
        try:
            stream_key = int(request.headers.getone('x-jchannel-stream'))

            stream = self._streams.pop(stream_key)
        except:
            logging.exception('Get headers exception')

            return web.Response(status=400, headers=HEADERS)

        response = web.StreamResponse(headers=HEADERS)

        await response.prepare(request)

        try:
            async for chunk in stream:
                await response.write(chunk)
        except:
            logging.exception('Get writing exception')

        await response.write_eof()

        return response

    async def _handle_post(self, request):
        try:
            data = request.headers.getone('x-jchannel-data')

            body = json.loads(data)

            future_key = body['future']
            channel_key = body['channel']
            payload = body.pop('payload')
            body_type = body.pop('type')

            if body_type == 'result':
                future = self._registry.retrieve(future_key)

                channel = None
            else:
                input = json.loads(payload)

                channel = self._channels[channel_key]
        except:
            logging.exception('Post headers exception')

            return web.Response(status=400, headers=HEADERS)

        # chunks = MetaGenerator(request.content)

        content = await request.content.read()
        queue = self._queues[int(content)]
        chunks = MetaGenerator(queue)

        response = web.StreamResponse(headers=HEADERS)
        await response.prepare(request)
        pseudo_status = b'200'

        if channel is None:
            future.set_result(chunks)
        else:
            try:
                match body_type:
                    case 'call':
                        stream, payload = await self._call(channel, input, chunks)
                        body_type = 'result'
                    case 'pipe':
                        stream = chunks
                        payload = 'null'
                        body_type = 'result'
                    case _:
                        stream = None
                        payload = f'Unexpected post body type {body_type}'
                        body_type = 'exception'
            except Exception as error:
                logging.exception('Post request exception')

                stream = None
                payload = f'{error.__class__.__name__}: {str(error)}'
                body_type = 'exception'

            if stream is None:
                async for _ in chunks:
                    pass

            try:
                socket = await self._propose(self._send_timeout)
            except:
                logging.exception('Post sending exception')

                # return web.Response(status=503, headers=HEADERS)

            # body['payload'] = payload

            # await self._accept(socket, body_type, body, stream)

                pseudo_status = b'503'

                chunks._queue.abort()
            else:
                body['payload'] = payload

                await self._accept(socket, body_type, body, stream)

        # await self._until(chunks._done)

        # return web.Response(headers=HEADERS)

        await response.write(pseudo_status)
        await response.write_eof()

        return response

    async def _allow(self, request):
        return web.Response(headers=HEADERS)

    # async def _until(self, event):
    #     self._events.add(event)
    #     await event.wait()
    #     self._events.remove(event)
