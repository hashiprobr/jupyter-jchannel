import json
import asyncio
import logging
import pytest

from unittest.mock import Mock
from aiohttp import ClientSession, WSServerHandshakeError
from jchannel.types import JavascriptError, StateError
from jchannel.server import Server, DebugScenario

pytestmark = pytest.mark.asyncio(scope='module')


HOST = ' \t\n127.0.0.1 \t\n'
PORT = 8888
HEARTBEAT = 3

FUTURE_KEY = 123
CHANNEL_KEY = 456


async def test_instantiates():
    server = Server(HOST, PORT, None, HEARTBEAT)
    assert server._url == 'http://127.0.0.1:8888'


@pytest.mark.parametrize('input, output', [
    (' \t\nhttp://localhost:8889 \t\n', 'http://localhost:8889'),
    (' \t\nhttp://localhost:8889/ \t\n', 'http://localhost:8889'),
    (' \t\nhttp://localhost:8889// \t\n', 'http://localhost:8889'),
    (' \t\nhttp://localhost:8889/// \t\n', 'http://localhost:8889'),
    (' \t\nhttp://localhost:8889/item \t\n', 'http://localhost:8889/item'),
    (' \t\nhttp://localhost:8889/item/ \t\n', 'http://localhost:8889/item'),
    (' \t\nhttp://localhost:8889/item// \t\n', 'http://localhost:8889/item'),
    (' \t\nhttp://localhost:8889/item/// \t\n', 'http://localhost:8889/item'),
    (' \t\nhttp://localhost:8889//item \t\n', 'http://localhost:8889//item'),
    (' \t\nhttp://localhost:8889//item/ \t\n', 'http://localhost:8889//item'),
    (' \t\nhttp://localhost:8889//item// \t\n', 'http://localhost:8889//item'),
    (' \t\nhttp://localhost:8889//item/// \t\n', 'http://localhost:8889//item'),
    (' \t\nhttp://localhost:8889///item \t\n', 'http://localhost:8889///item'),
    (' \t\nhttp://localhost:8889///item/ \t\n', 'http://localhost:8889///item'),
    (' \t\nhttp://localhost:8889///item// \t\n', 'http://localhost:8889///item'),
    (' \t\nhttp://localhost:8889///item/// \t\n', 'http://localhost:8889///item'),
    (' \t\nhttp://localhost:8889/item0/item1 \t\n', 'http://localhost:8889/item0/item1'),
    (' \t\nhttp://localhost:8889/item0/item1/ \t\n', 'http://localhost:8889/item0/item1'),
    (' \t\nhttp://localhost:8889/item0/item1// \t\n', 'http://localhost:8889/item0/item1'),
    (' \t\nhttp://localhost:8889/item0/item1/// \t\n', 'http://localhost:8889/item0/item1'),
    (' \t\nhttp://localhost:8889//item0//item1 \t\n', 'http://localhost:8889//item0//item1'),
    (' \t\nhttp://localhost:8889//item0//item1/ \t\n', 'http://localhost:8889//item0//item1'),
    (' \t\nhttp://localhost:8889//item0//item1// \t\n', 'http://localhost:8889//item0//item1'),
    (' \t\nhttp://localhost:8889//item0//item1/// \t\n', 'http://localhost:8889//item0//item1'),
    (' \t\nhttp://localhost:8889///item0///item1 \t\n', 'http://localhost:8889///item0///item1'),
    (' \t\nhttp://localhost:8889///item0///item1/ \t\n', 'http://localhost:8889///item0///item1'),
    (' \t\nhttp://localhost:8889///item0///item1// \t\n', 'http://localhost:8889///item0///item1'),
    (' \t\nhttp://localhost:8889///item0///item1/// \t\n', 'http://localhost:8889///item0///item1'),
    (' \t\nhttps://localhost:8889 \t\n', 'https://localhost:8889'),
    (' \t\nhttps://localhost:8889/ \t\n', 'https://localhost:8889'),
    (' \t\nhttps://localhost:8889// \t\n', 'https://localhost:8889'),
    (' \t\nhttps://localhost:8889/// \t\n', 'https://localhost:8889'),
    (' \t\nhttps://localhost:8889/item \t\n', 'https://localhost:8889/item'),
    (' \t\nhttps://localhost:8889/item/ \t\n', 'https://localhost:8889/item'),
    (' \t\nhttps://localhost:8889/item// \t\n', 'https://localhost:8889/item'),
    (' \t\nhttps://localhost:8889/item/// \t\n', 'https://localhost:8889/item'),
    (' \t\nhttps://localhost:8889//item \t\n', 'https://localhost:8889//item'),
    (' \t\nhttps://localhost:8889//item/ \t\n', 'https://localhost:8889//item'),
    (' \t\nhttps://localhost:8889//item// \t\n', 'https://localhost:8889//item'),
    (' \t\nhttps://localhost:8889//item/// \t\n', 'https://localhost:8889//item'),
    (' \t\nhttps://localhost:8889///item \t\n', 'https://localhost:8889///item'),
    (' \t\nhttps://localhost:8889///item/ \t\n', 'https://localhost:8889///item'),
    (' \t\nhttps://localhost:8889///item// \t\n', 'https://localhost:8889///item'),
    (' \t\nhttps://localhost:8889///item/// \t\n', 'https://localhost:8889///item'),
    (' \t\nhttps://localhost:8889/item0/item1 \t\n', 'https://localhost:8889/item0/item1'),
    (' \t\nhttps://localhost:8889/item0/item1/ \t\n', 'https://localhost:8889/item0/item1'),
    (' \t\nhttps://localhost:8889/item0/item1// \t\n', 'https://localhost:8889/item0/item1'),
    (' \t\nhttps://localhost:8889/item0/item1/// \t\n', 'https://localhost:8889/item0/item1'),
    (' \t\nhttps://localhost:8889//item0//item1 \t\n', 'https://localhost:8889//item0//item1'),
    (' \t\nhttps://localhost:8889//item0//item1/ \t\n', 'https://localhost:8889//item0//item1'),
    (' \t\nhttps://localhost:8889//item0//item1// \t\n', 'https://localhost:8889//item0//item1'),
    (' \t\nhttps://localhost:8889//item0//item1/// \t\n', 'https://localhost:8889//item0//item1'),
    (' \t\nhttps://localhost:8889///item0///item1 \t\n', 'https://localhost:8889///item0///item1'),
    (' \t\nhttps://localhost:8889///item0///item1/ \t\n', 'https://localhost:8889///item0///item1'),
    (' \t\nhttps://localhost:8889///item0///item1// \t\n', 'https://localhost:8889///item0///item1'),
    (' \t\nhttps://localhost:8889///item0///item1/// \t\n', 'https://localhost:8889///item0///item1'),
])
async def test_instantiates_with_url(input, output):
    server = Server(HOST, PORT, input, HEARTBEAT)
    assert server._url == output


async def test_does_not_instantiate_with_non_string_host():
    with pytest.raises(TypeError):
        Server(True, PORT, None, HEARTBEAT)


async def test_does_not_instantiate_with_blank_host():
    with pytest.raises(ValueError):
        Server(' \t\n', PORT, None, HEARTBEAT)


async def test_does_not_instantiate_with_slash_host():
    with pytest.raises(ValueError):
        Server('127.0/0.1', PORT, None, HEARTBEAT)


async def test_does_not_instantiate_with_non_integer_port():
    with pytest.raises(TypeError):
        Server(HOST, '8888', None, HEARTBEAT)


async def test_does_not_instantiate_with_negative_port():
    with pytest.raises(ValueError):
        Server(HOST, -1, None, HEARTBEAT)


async def test_does_not_instantiate_with_non_string_url():
    with pytest.raises(TypeError):
        Server(HOST, PORT, True, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'ws://localhost:8889',
    'wss://localhost:8889',
])
async def test_does_not_instantiate_with_non_http_url(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http',
    'http:',
    'http:/',
    'http:/localhost:8889',
    'https',
    'https:',
    'https:/',
    'https:/localhost:8889',
])
async def test_does_not_instantiate_with_invalid_url_start(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http://',
    'http:///',
    'http:///localhost:8889',
    'https://',
    'https:///',
    'https:///localhost:8889',
])
async def test_does_not_instantiate_with_empty_url_authority(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


async def test_does_not_instantiate_with_non_integer_heartbeat():
    with pytest.raises(TypeError):
        Server(HOST, PORT, None, '3')


async def test_does_not_instantiate_with_non_positive_heartbeat():
    with pytest.raises(ValueError):
        Server(HOST, PORT, None, 0)


@pytest.fixture
def s(mocker):
    def side_effect(code):
        assert code in [
            "jchannel.start('http://localhost:8889')",
            "jchannel.stop('http://localhost:8889')",
            "jchannel._unload('http://localhost:8889')",
        ]

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.run.side_effect = side_effect

    return Server()


async def send(s, body_type, input=None, chunks=None, timeout=3):
    await s._send(body_type, CHANNEL_KEY, input, chunks, timeout)


async def test_stops_client_and_stops(s):
    s.stop_client()
    await s.stop()


async def test_starts_twice_and_stops_twice(s):
    await s.start()
    await s.start()
    task = s.stop()
    await s.stop()
    await task


async def test_does_not_send_with_non_integer_timeout(s):
    with pytest.raises(TypeError):
        await send(s, 'close', timeout='3')


async def test_does_not_send_with_negative_timeout(s):
    with pytest.raises(ValueError):
        await send(s, 'close', timeout=-1)


async def test_does_not_send(s):
    with pytest.raises(StateError):
        await send(s, 'close')


async def test_starts_stops_and_does_not_send(s):
    await s.start()
    task = s.stop()
    with pytest.raises(StateError):
        await send(s, 'close')
    await task


async def test_starts_does_not_send_and_stops(s):
    with pytest.raises(StateError):
        async with s as server:
            await send(server, 'close', timeout=0)


class MockChannel:
    def __init__(self, server, code):
        server._channels[CHANNEL_KEY] = self
        assert code == '() => true'

        def destroy():
            del server._channels[CHANNEL_KEY]

        self.destroy = destroy

    def _handle_call(self, name, args):
        if name == 'error':
            raise Exception
        if name == 'async':
            return self._resolve(args)
        return args

    async def _resolve(self, args):
        return args

    async def _open(self, timeout):
        if not timeout:
            raise Exception


class Client:
    def __init__(self):
        self.stopped = True
        self.body = None

    def start(self):
        if self.stopped:
            self.stopped = False

            loop = asyncio.get_running_loop()
            self.connection = loop.create_future()
            self.disconnection = loop.create_future()

            asyncio.create_task(self._run())

    def _dumps(self, body_type, payload):
        body = {
            'future': FUTURE_KEY,
            'channel': CHANNEL_KEY,
            'payload': payload,
        }

        body['type'] = body_type

        return json.dumps(body)

    async def _run(self):
        async with ClientSession() as session:
            try:
                async with session.ws_connect(f'ws://localhost:8889/socket') as socket:
                    self.connection.set_result(200)

                    async for message in socket:
                        body = json.loads(message.data)

                        match body['type']:
                            case 'exception' | 'result':
                                self.body = body
                                await socket.close()
                                break
                            case 'socket-close':
                                await socket.close()
                                break
                            case 'socket-bytes':
                                await socket.send_bytes(b'')
                            case 'empty-message':
                                await socket.send_str('')
                            case 'empty-body':
                                await socket.send_str('{}')
                            case 'mock-closed':
                                await socket.send_str(self._dumps('closed', None))
                            case 'mock-exception':
                                await socket.send_str(self._dumps('exception', 'message'))
                            case 'mock-result':
                                await socket.send_str(self._dumps('result', 'true'))
                            case _:
                                await socket.send_str(message.data)
            except WSServerHandshakeError as error:
                self.connection.set_result(error.status)

        self.disconnection.set_result(None)


@pytest.fixture
def future():
    return Mock()


@pytest.fixture
def server_and_client(mocker, future):
    registry = Mock()

    Registry = mocker.patch('jchannel.server.Registry')
    Registry.return_value = registry

    registry.store.return_value = FUTURE_KEY
    registry.retrieve.return_value = future

    Channel = mocker.patch('jchannel.server.Channel')
    Channel.side_effect = MockChannel

    s = Server()
    c = Client()

    def side_effect(code):
        if code == "jchannel.start('http://localhost:8889')":
            c.start()
        else:
            assert code == "jchannel._unload('http://localhost:8889')"

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.run.side_effect = side_effect

    return s, c


async def open(s, timeout=3):
    channel = await s.open('() => true', timeout)
    assert isinstance(channel, MockChannel)


async def test_connects_and_stops_twice(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_SESSION_REFERENCES_AFTER_SESSION_REFERENCES_ARE_NONE)
    assert await c.connection == 200
    task = s.stop()
    await s.stop()
    await task
    await c.disconnection
    assert s._registry.clear.call_count == 1


async def test_connects_disconnects_does_not_send_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_DISCONNECTION_STATE_AFTER_DISCONNECTION_RESULT_IS_SET)
    assert await c.connection == 200
    await send(s, 'socket-close')
    await c.disconnection
    with pytest.raises(StateError):
        await send(s, 'close')
    await s.stop()
    assert s._registry.clear.call_count == 1


async def test_does_not_send_connects_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_SOCKET_PREPARATION_BEFORE_SOCKET_IS_PREPARED)
    with pytest.raises(StateError):
        await send(s, 'close')
    assert await c.connection == 200
    await s.stop()
    await c.disconnection
    assert s._registry.clear.call_count == 1


async def test_stops_and_does_not_connect(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.HANDLE_SOCKET_REQUEST_BEFORE_APP_RUNNER_IS_CLEANED)
    await s.stop()
    assert await c.connection == 404
    await c.disconnection


async def test_does_not_connect_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_CONNECTION_RESULT_BEFORE_SESSION_REFERENCES_ARE_NONE)
    task = s.stop()
    assert await c.connection == 404
    await task
    await c.disconnection


async def test_connects_does_not_connect_and_stops(server_and_client):
    s, c_0 = server_and_client
    c_1 = Client()
    await s.start()
    assert await c_0.connection == 200
    c_1.start()
    assert await c_1.connection == 409
    await s.stop()
    await c_0.disconnection
    await c_1.disconnection


async def test_connects_does_not_start_and_stops(server_and_client):
    s_0, c = server_and_client
    s_1 = Server()
    await s_0.start()
    assert await c.connection == 200
    with pytest.raises(OSError):
        await s_1.start()
    await s_0.stop()
    await c.disconnection


async def test_connects_does_not_start_and_stops_twice(server_and_client):
    s_0, c = server_and_client
    s_1 = Server()
    await s_0.start()
    assert await c.connection == 200
    with pytest.raises(OSError):
        task_start = s_1.start()
        task_stop = s_1.stop()
        await task_start
        await task_stop
    await s_0.stop()
    await c.disconnection


async def test_receives_unexpected_message_type(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        assert await c.connection == 200
        await send(s, 'socket-bytes')
        await c.disconnection
        with pytest.raises(StateError):
            await s.stop()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_empty_message(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        assert await c.connection == 200
        await send(s, 'empty-message')
        await c.disconnection
        with pytest.raises(StateError):
            await s.stop()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_empty_body(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        assert await c.connection == 200
        await send(s, 'empty-body')
        await c.disconnection
        with pytest.raises(StateError):
            await s.stop()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_closed(future, server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await send(s, 'mock-closed')
    await send(s, 'socket-close')
    await c.disconnection
    await s.stop()
    future.set_exception.assert_called_once_with(StateError)


async def test_receives_exception(future, server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await send(s, 'mock-exception')
    await send(s, 'socket-close')
    await c.disconnection
    await s.stop()
    (args, _), = future.set_exception.call_args_list
    error, = args
    assert isinstance(error, JavascriptError)
    assert error.args == ('message',)


async def test_receives_result(future, server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await send(s, 'mock-result')
    await send(s, 'socket-close')
    await c.disconnection
    await s.stop()
    (args, _), = future.set_result.call_args_list
    output, = args
    assert output is True


async def test_does_not_open(server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    with pytest.raises(Exception):
        await open(s, 0)
    await s.stop()
    await c.disconnection
    assert CHANNEL_KEY not in s._channels


async def test_echoes(server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await open(s)
    await send(s, 'echo', 3)
    await c.disconnection
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '3'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls(server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await open(s)
    await send(s, 'call', {'name': 'name', 'args': [1, 2]})
    await c.disconnection
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[1, 2]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls_async(server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await open(s)
    await send(s, 'call', {'name': 'async', 'args': [1, 2]})
    await c.disconnection
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[1, 2]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_does_not_call_error(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        assert await c.connection == 200
        await open(s)
        await send(s, 'call', {'name': 'error', 'args': [1, 2]})
        await c.disconnection
        await s.stop()
        assert len(c.body) == 4
        assert c.body['type'] == 'exception'
        assert isinstance(c.body['payload'], str)
        assert c.body['channel'] == CHANNEL_KEY
        assert c.body['future'] == FUTURE_KEY
    assert len(caplog.records) == 1


async def test_receives_unexpected_body_type(server_and_client):
    s, c = server_and_client
    await s.start()
    assert await c.connection == 200
    await open(s)
    await send(s, 'type')
    await c.disconnection
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'exception'
    assert isinstance(c.body['payload'], str)
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY
