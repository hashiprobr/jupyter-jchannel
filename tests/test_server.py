import json
import asyncio
import logging
import pytest

from unittest.mock import Mock
from aiohttp import ClientSession
from jchannel.server import Server, StateError, JavascriptError, DebugScenario


HOST = 's'
PORT = 0
HEARTBEAT = 1

FUTURE_KEY = 0
CHANNEL_KEY = 1


pytestmark = pytest.mark.asyncio(scope='module')


async def test_instantiates():
    server = Server(HOST, PORT, None, HEARTBEAT)
    assert server.url == 'ws://s:0'


@pytest.mark.parametrize('input, output', [
    ('ws://a', 'ws://a'),
    ('ws://a/', 'ws://a'),
    ('ws://a//', 'ws://a'),
    ('ws:///a', 'ws:///a'),
    ('ws:///a/', 'ws:///a'),
    ('ws:///a//', 'ws:///a'),
    ('ws:////a', 'ws:////a'),
    ('ws:////a/', 'ws:////a'),
    ('ws:////a//', 'ws:////a'),
    ('ws://a/b', 'ws://a/b'),
    ('ws://a/b/', 'ws://a/b'),
    ('ws://a/b//', 'ws://a/b'),
    ('ws://a//b', 'ws://a//b'),
    ('ws://a//b/', 'ws://a//b'),
    ('ws://a//b//', 'ws://a//b'),
    ('wss://a', 'wss://a'),
    ('wss://a/', 'wss://a'),
    ('wss://a//', 'wss://a'),
    ('wss:///a', 'wss:///a'),
    ('wss:///a/', 'wss:///a'),
    ('wss:///a//', 'wss:///a'),
    ('wss:////a', 'wss:////a'),
    ('wss:////a/', 'wss:////a'),
    ('wss:////a//', 'wss:////a'),
    ('wss://a/b', 'wss://a/b'),
    ('wss://a/b/', 'wss://a/b'),
    ('wss://a/b//', 'wss://a/b'),
    ('wss://a//b', 'wss://a//b'),
    ('wss://a//b/', 'wss://a//b'),
    ('wss://a//b//', 'wss://a//b'),
])
async def test_instantiates_with_url(input, output):
    server = Server(HOST, PORT, input, HEARTBEAT)
    assert server.url == output


async def test_does_not_instantiate_with_non_string_host():
    with pytest.raises(TypeError):
        Server(0, PORT, None, HEARTBEAT)


async def test_does_not_instantiate_with_non_integer_port():
    with pytest.raises(TypeError):
        Server(HOST, 's', None, HEARTBEAT)


async def test_does_not_instantiate_with_negative_port():
    with pytest.raises(ValueError):
        Server(HOST, -1, None, HEARTBEAT)


async def test_does_not_instantiate_with_non_string_url():
    with pytest.raises(TypeError):
        Server(HOST, PORT, 0, HEARTBEAT)


async def test_does_not_instantiate_with_non_ws_url_start():
    with pytest.raises(ValueError):
        Server(HOST, PORT, 'http://a', HEARTBEAT)


@pytest.mark.parametrize('url', [
    'ws:/a',
    'wss:/a',
])
async def test_does_not_instantiate_with_invalid_url_start(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'ws://',
    'ws:///',
    'ws:////',
    'wss://',
    'wss:///',
    'wss:////',
])
async def test_does_not_instantiate_with_empty_url_authority(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


async def test_does_not_instantiate_with_non_integer_heartbeat():
    with pytest.raises(TypeError):
        Server(HOST, PORT, None, 's')


async def test_does_not_instantiate_with_non_positive_heartbeat():
    with pytest.raises(ValueError):
        Server(HOST, PORT, None, 0)


@pytest.fixture
def s(mocker):
    mocker.patch('jchannel.server.frontend')

    return Server()


async def test_stops(s):
    await s.stop()


async def test_starts_twice_and_stops(s):
    async with s:
        await s.start()


async def test_starts_and_stops_twice(s):
    await s.start()
    task = s.stop()
    await s.stop()
    await task


async def test_does_not_send(s):
    with pytest.raises(StateError):
        await send(s, '')


async def test_starts_does_not_send_and_stops(s):
    with pytest.raises(StateError):
        async with s as target:
            await send(target, '', timeout=0)


async def test_starts_stops_and_does_not_send(s):
    await s.start()
    task = s.stop()
    with pytest.raises(StateError):
        await send(s, '')
    await task


class Client:
    def __init__(self):
        self.stopped = True

    def _dumps(self, body_type, payload):
        body = {
            'future': FUTURE_KEY,
            'channel': CHANNEL_KEY,
            'payload': payload,
        }
        body['type'] = body_type
        return json.dumps(body)

    async def start(self):
        if self.stopped:
            self.stopped = False
            self.connected = asyncio.Event()
            self.disconnected = asyncio.Event()
            asyncio.create_task(self._run())

    async def connection(self):
        await self.connected.wait()

    async def disconnection(self):
        await self.disconnected.wait()

    async def _run(self):
        async with ClientSession() as session:
            self.body = None
            async with session.ws_connect(f'ws://localhost:8889/socket') as socket:
                self.connected.set()
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
                        case 'mock-exception':
                            await socket.send_str(self._dumps('exception', ''))
                        case 'mock-result':
                            await socket.send_str(self._dumps('result', '0'))
                        case _:
                            await socket.send_str(message.data)
        self.disconnected.set()


class MockChannel:
    def __init__(self, server):
        server.channels[CHANNEL_KEY] = self

    def handle_call(self, name, args):
        if name == 'error':
            raise Exception
        if name == 'async':
            return self.resolve(args)
        return args

    async def resolve(self, args):
        return args


@pytest.fixture
def mock_future():
    return Mock()


@pytest.fixture
def server_with_client(mocker, mock_future):
    Channel = mocker.patch('jchannel.server.Channel')
    Channel.side_effect = MockChannel

    s = Server()
    c = Client()

    def side_effect(code):
        assert code == "jchannel.start('ws://localhost:8889')"
        asyncio.create_task(c.start())

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.run.side_effect = side_effect

    registry = mocker.patch('jchannel.server.registry')
    registry.store.side_effect = lambda f: FUTURE_KEY
    registry.retrieve.side_effect = lambda k: mock_future

    return s, c


def start_with_sentinel(s, scenario):
    return asyncio.create_task(s._start(scenario))


async def send(c, body_type, input=None, timeout=3):
    await c._send(body_type, input, CHANNEL_KEY, timeout)


async def test_connects_disconnects_does_not_stop_and_stops(caplog, server_with_client):
    with caplog.at_level(logging.WARNING):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.STOP_BEFORE_RESTART)
        await c.connection()
        await send(s, 'socket-close')
        await c.disconnection()
        with pytest.raises(StateError):
            await s.stop()
        await s.stop()
    assert caplog.records


async def test_connects_and_stops_twice(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.STOP_AFTER_BREAK)
    await c.connection()
    task = s.stop()
    await s.stop()
    await task
    await c.disconnection()


async def test_stops_and_does_not_connect(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.CONNECT_BEFORE_BREAK)
    await s.stop()
    await c.connection()
    await c.disconnection()


async def test_connects_does_not_connect_and_stops(caplog, server_with_client):
    with caplog.at_level(logging.WARNING):
        s, c_0 = server_with_client
        c_1 = Client()
        await s.start()
        await c_1.start()
        await c_0.connection()
        await c_1.connection()
        await s.stop()
        await c_0.disconnection()
        await c_1.disconnection()
    assert caplog.records


async def test_breaks_does_not_connect_and_cleans(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.CONNECT_BEFORE_CLEAN)
    await s.stop()
    await c.connection()
    await c.disconnection()


async def test_receives_unexpected_message_type(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.CATCH_BEFORE_CLEAN)
        await c.connection()
        await send(s, 'socket-bytes')
        await s.stop()
        await c.disconnection()
    assert caplog.records


async def test_receives_empty_message(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.CATCH_BEFORE_CLEAN)
        await c.connection()
        await send(s, 'empty-message')
        await s.stop()
        await c.disconnection()
    assert caplog.records


async def test_receives_empty_body(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.CATCH_BEFORE_CLEAN)
        await c.connection()
        await send(s, 'empty-body')
        await s.stop()
        await c.disconnection()
    assert caplog.records


async def test_receives_closed(caplog, mock_future, server_with_client):
    with caplog.at_level(logging.WARNING):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
        await c.connection()
        await send(s, 'closed')
        await s.stop()
        await c.disconnection()
        mock_future.set_exception.assert_called_with(StateError)
    assert caplog.records


async def test_receives_exception(mock_future, server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    await send(s, 'mock-exception')
    await s.stop()
    await c.disconnection()
    args, _ = mock_future.set_exception.call_args
    error, = args
    assert isinstance(error, JavascriptError)
    message, = error.args
    assert isinstance(message, str)


async def test_receives_result(mock_future, server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    await send(s, 'mock-result')
    await s.stop()
    await c.disconnection()
    args, _ = mock_future.set_result.call_args
    output, = args
    assert output == 0


async def test_echoes(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    s.open()
    await send(s, 'echo', 1)
    await s.stop()
    await c.disconnection()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '1'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    s.open()
    await send(s, 'call', {'name': 'name', 'args': [0, 1]})
    await s.stop()
    await c.disconnection()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[0, 1]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls_async(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    s.open()
    await send(s, 'call', {'name': 'async', 'args': [0, 1]})
    await s.stop()
    await c.disconnection()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[0, 1]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls_error(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_with_client
        await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
        await c.connection()
        s.open()
        await send(s, 'call', {'name': 'error', 'args': [0, 1]})
        await s.stop()
        await c.disconnection()
        assert len(c.body) == 4
        assert c.body['type'] == 'exception'
        assert isinstance(c.body['payload'], str)
        assert c.body['channel'] == CHANNEL_KEY
        assert c.body['future'] == FUTURE_KEY
    assert caplog.records


async def test_receives_unexpected_body_type(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.RECEIVE_BEFORE_CLEAN)
    await c.connection()
    s.open()
    await send(s, 'type', None)
    await s.stop()
    await c.disconnection()
    assert len(c.body) == 4
    assert c.body['type'] == 'exception'
    assert isinstance(c.body['payload'], str)
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_connects_disconnects_and_stops(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.DISCONNECT_AFTER_STOP)
    await c.connection()
    await send(s, 'socket-close')
    await c.disconnection()
    await s.stop()


async def test_does_not_send_connects_and_stops(server_with_client):
    s, c = server_with_client
    await start_with_sentinel(s, DebugScenario.SEND_BEFORE_PREPARE)
    with pytest.raises(StateError):
        await send(s, '')
    await c.connection()
    await s.stop()
    await c.disconnection()
