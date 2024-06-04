import json
import asyncio
import logging
import pytest

from unittest.mock import Mock, call
from aiohttp import ClientSession
from jchannel.types import JavascriptError, StateError
from jchannel.server import Server, DebugScenario

pytestmark = pytest.mark.asyncio(scope='module')


HOST = '127.0.0.1'
PORT = 8888
HEARTBEAT = 3

FUTURE_KEY = 123
CHANNEL_KEY = 456


async def test_instantiates():
    server = Server(HOST, PORT, None, HEARTBEAT)
    assert server._url == 'http://127.0.0.1:8888'


@pytest.mark.parametrize('input, output', [
    ('http://localhost:8889', 'http://localhost:8889'),
    ('http://localhost:8889/', 'http://localhost:8889'),
    ('http://localhost:8889//', 'http://localhost:8889'),
    ('http://localhost:8889///', 'http://localhost:8889'),
    ('http://localhost:8889/item', 'http://localhost:8889/item'),
    ('http://localhost:8889/item/', 'http://localhost:8889/item'),
    ('http://localhost:8889/item//', 'http://localhost:8889/item'),
    ('http://localhost:8889/item///', 'http://localhost:8889/item'),
    ('http://localhost:8889//item', 'http://localhost:8889//item'),
    ('http://localhost:8889//item/', 'http://localhost:8889//item'),
    ('http://localhost:8889//item//', 'http://localhost:8889//item'),
    ('http://localhost:8889//item///', 'http://localhost:8889//item'),
    ('http://localhost:8889///item', 'http://localhost:8889///item'),
    ('http://localhost:8889///item/', 'http://localhost:8889///item'),
    ('http://localhost:8889///item//', 'http://localhost:8889///item'),
    ('http://localhost:8889///item///', 'http://localhost:8889///item'),
    ('http://localhost:8889/item0/item1', 'http://localhost:8889/item0/item1'),
    ('http://localhost:8889/item0/item1/', 'http://localhost:8889/item0/item1'),
    ('http://localhost:8889/item0/item1//', 'http://localhost:8889/item0/item1'),
    ('http://localhost:8889/item0/item1///', 'http://localhost:8889/item0/item1'),
    ('http://localhost:8889//item0//item1', 'http://localhost:8889//item0//item1'),
    ('http://localhost:8889//item0//item1/', 'http://localhost:8889//item0//item1'),
    ('http://localhost:8889//item0//item1//', 'http://localhost:8889//item0//item1'),
    ('http://localhost:8889//item0//item1///', 'http://localhost:8889//item0//item1'),
    ('http://localhost:8889///item0///item1', 'http://localhost:8889///item0///item1'),
    ('http://localhost:8889///item0///item1/', 'http://localhost:8889///item0///item1'),
    ('http://localhost:8889///item0///item1//', 'http://localhost:8889///item0///item1'),
    ('http://localhost:8889///item0///item1///', 'http://localhost:8889///item0///item1'),
    ('https://localhost:8889', 'https://localhost:8889'),
    ('https://localhost:8889/', 'https://localhost:8889'),
    ('https://localhost:8889//', 'https://localhost:8889'),
    ('https://localhost:8889///', 'https://localhost:8889'),
    ('https://localhost:8889/item', 'https://localhost:8889/item'),
    ('https://localhost:8889/item/', 'https://localhost:8889/item'),
    ('https://localhost:8889/item//', 'https://localhost:8889/item'),
    ('https://localhost:8889/item///', 'https://localhost:8889/item'),
    ('https://localhost:8889//item', 'https://localhost:8889//item'),
    ('https://localhost:8889//item/', 'https://localhost:8889//item'),
    ('https://localhost:8889//item//', 'https://localhost:8889//item'),
    ('https://localhost:8889//item///', 'https://localhost:8889//item'),
    ('https://localhost:8889///item', 'https://localhost:8889///item'),
    ('https://localhost:8889///item/', 'https://localhost:8889///item'),
    ('https://localhost:8889///item//', 'https://localhost:8889///item'),
    ('https://localhost:8889///item///', 'https://localhost:8889///item'),
    ('https://localhost:8889/item0/item1', 'https://localhost:8889/item0/item1'),
    ('https://localhost:8889/item0/item1/', 'https://localhost:8889/item0/item1'),
    ('https://localhost:8889/item0/item1//', 'https://localhost:8889/item0/item1'),
    ('https://localhost:8889/item0/item1///', 'https://localhost:8889/item0/item1'),
    ('https://localhost:8889//item0//item1', 'https://localhost:8889//item0//item1'),
    ('https://localhost:8889//item0//item1/', 'https://localhost:8889//item0//item1'),
    ('https://localhost:8889//item0//item1//', 'https://localhost:8889//item0//item1'),
    ('https://localhost:8889//item0//item1///', 'https://localhost:8889//item0//item1'),
    ('https://localhost:8889///item0///item1', 'https://localhost:8889///item0///item1'),
    ('https://localhost:8889///item0///item1/', 'https://localhost:8889///item0///item1'),
    ('https://localhost:8889///item0///item1//', 'https://localhost:8889///item0///item1'),
    ('https://localhost:8889///item0///item1///', 'https://localhost:8889///item0///item1'),
])
async def test_instantiates_with_url(input, output):
    server = Server(HOST, PORT, input, HEARTBEAT)
    assert server._url == output


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


async def test_does_not_instantiate_with_non_http_url_start():
    with pytest.raises(ValueError):
        Server(HOST, PORT, 'ws://localhost:8889', HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http:/localhost:8889',
    'http:/localhost:8889/',
    'http:/localhost:8889//',
    'http:/localhost:8889///',
    'http:/localhost:8889/item',
    'http:/localhost:8889/item/',
    'http:/localhost:8889/item//',
    'http:/localhost:8889/item///',
    'http:/localhost:8889//item',
    'http:/localhost:8889//item/',
    'http:/localhost:8889//item//',
    'http:/localhost:8889//item///',
    'http:/localhost:8889///item',
    'http:/localhost:8889///item/',
    'http:/localhost:8889///item//',
    'http:/localhost:8889///item///',
    'http:/localhost:8889/item0/item1',
    'http:/localhost:8889/item0/item1/',
    'http:/localhost:8889/item0/item1//',
    'http:/localhost:8889/item0/item1///',
    'http:/localhost:8889//item0//item1',
    'http:/localhost:8889//item0//item1/',
    'http:/localhost:8889//item0//item1//',
    'http:/localhost:8889//item0//item1///',
    'http:/localhost:8889///item0///item1',
    'http:/localhost:8889///item0///item1/',
    'http:/localhost:8889///item0///item1//',
    'http:/localhost:8889///item0///item1///',
    'https:/localhost:8889',
    'https:/localhost:8889/',
    'https:/localhost:8889//',
    'https:/localhost:8889///',
    'https:/localhost:8889/item',
    'https:/localhost:8889/item/',
    'https:/localhost:8889/item//',
    'https:/localhost:8889/item///',
    'https:/localhost:8889//item',
    'https:/localhost:8889//item/',
    'https:/localhost:8889//item//',
    'https:/localhost:8889//item///',
    'https:/localhost:8889///item',
    'https:/localhost:8889///item/',
    'https:/localhost:8889///item//',
    'https:/localhost:8889///item///',
    'https:/localhost:8889/item0/item1',
    'https:/localhost:8889/item0/item1/',
    'https:/localhost:8889/item0/item1//',
    'https:/localhost:8889/item0/item1///',
    'https:/localhost:8889//item0//item1',
    'https:/localhost:8889//item0//item1/',
    'https:/localhost:8889//item0//item1//',
    'https:/localhost:8889//item0//item1///',
    'https:/localhost:8889///item0///item1',
    'https:/localhost:8889///item0///item1/',
    'https:/localhost:8889///item0///item1//',
    'https:/localhost:8889///item0///item1///',
])
async def test_does_not_instantiate_with_invalid_url_start(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http://',
    'http:///',
    'http:////',
    'http://///',
    'http:///item',
    'http:///item/',
    'http:///item//',
    'http:///item///',
    'http:////item',
    'http:////item/',
    'http:////item//',
    'http:////item///',
    'http://///item',
    'http://///item/',
    'http://///item//',
    'http://///item///',
    'http:///item0/item1',
    'http:///item0/item1/',
    'http:///item0/item1//',
    'http:///item0/item1///',
    'http:////item0//item1',
    'http:////item0//item1/',
    'http:////item0//item1//',
    'http:////item0//item1///',
    'http://///item0///item1',
    'http://///item0///item1/',
    'http://///item0///item1//',
    'http://///item0///item1///',
    'https://',
    'https:///',
    'https:////',
    'https://///',
    'https:///item',
    'https:///item/',
    'https:///item//',
    'https:///item///',
    'https:////item',
    'https:////item/',
    'https:////item//',
    'https:////item///',
    'https://///item',
    'https://///item/',
    'https://///item//',
    'https://///item///',
    'https:///item0/item1',
    'https:///item0/item1/',
    'https:///item0/item1//',
    'https:///item0/item1///',
    'https:////item0//item1',
    'https:////item0//item1/',
    'https:////item0//item1//',
    'https:////item0//item1///',
    'https://///item0///item1',
    'https://///item0///item1/',
    'https://///item0///item1//',
    'https://///item0///item1///',
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
    def side_effect(code):
        assert code == "jchannel.start('http://localhost:8889')" or code == "jchannel.stop('http://localhost:8889')"

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.run.side_effect = side_effect

    return Server()


async def send(s, body_type, input=None, timeout=3):
    await s._send(body_type, input, CHANNEL_KEY, timeout)


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


class Client:
    def __init__(self):
        self.stopped = True

    def start(self):
        if self.stopped:
            self.stopped = False
            self.connected = asyncio.Event()
            self.disconnected = asyncio.Event()
            asyncio.create_task(self._run())

    def _dumps(self, body_type, payload):
        body = {
            'future': FUTURE_KEY,
            'channel': CHANNEL_KEY,
            'payload': payload,
        }
        body['type'] = body_type
        return json.dumps(body)

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
                        case 'mock-closed':
                            await socket.send_str(self._dumps('closed', None))
                        case 'mock-exception':
                            await socket.send_str(self._dumps('exception', ''))
                        case 'mock-result':
                            await socket.send_str(self._dumps('result', '0'))
                        case _:
                            await socket.send_str(message.data)
        self.disconnected.set()


class MockChannel:
    def __init__(self, server, code):
        server._channels[CHANNEL_KEY] = self
        assert code == '() => { }'

    def _handle_call(self, name, args):
        if name == 'error':
            raise Exception
        if name == 'async':
            return self.resolve(args)
        return args

    async def resolve(self, args):
        return args

    async def _open(self, timeout):
        if not timeout:
            raise Exception


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
        c.start()

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.run.side_effect = side_effect

    return s, c


def open(s, timeout=3):
    channel = s.open('() => { }', timeout)
    assert isinstance(channel, MockChannel)


async def test_connects_disconnects_does_not_stop_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_DISCONNECTION_RESULT_BEFORE_OBJECT_IS_REPLACED)
    await c.connection()
    await send(s, 'socket-close')
    await c.disconnection()
    with pytest.raises(StateError):
        await s.stop()
    await s.stop()
    s._registry.clear.assert_has_calls(2 * [call()])


async def test_connects_and_stops_twice(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_CONNECTION_REFERENCE_AFTER_REFERENCE_IS_NONE)
    await c.connection()
    task = s.stop()
    await s.stop()
    await task
    await c.disconnection()


async def test_stops_and_does_not_connect(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_CONNECTION_RESULT_BEFORE_REFERENCE_IS_NONE)
    await s.stop()
    await c.connection()
    await c.disconnection()


async def test_connects_does_not_start_and_stops(server_and_client):
    s_0, c = server_and_client
    s_1 = Server()
    await s_0.start()
    await c.connection()
    with pytest.raises(OSError):
        await s_1.start()
    await s_0.stop()
    await c.disconnection()


async def test_connects_stops_and_does_not_start(server_and_client):
    s_0, c = server_and_client
    s_1 = Server()
    await s_0.start()
    await c.connection()
    with pytest.raises(OSError):
        task_start = s_1.start()
        task_stop = s_1.stop()
        await task_start
        await task_stop
    await s_0.stop()
    await c.disconnection()


async def test_connects_does_not_connect_and_stops(caplog, server_and_client):
    with caplog.at_level(logging.WARNING):
        s, c_0 = server_and_client
        c_1 = Client()
        await s.start()
        c_1.start()
        await c_0.connection()
        await c_1.connection()
        await s.stop()
        await c_0.disconnection()
        await c_1.disconnection()
    assert len(caplog.records) == 1


async def test_does_not_connect_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.RECEIVE_SOCKET_REQUEST_BEFORE_SERVER_IS_STOPPED)
    await s.stop()
    await c.connection()
    await c.disconnection()


async def test_connects_disconnects_does_not_send_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_DISCONNECTION_STATE_AFTER_RESULT_IS_SET)
    await c.connection()
    await send(s, 'socket-close')
    await c.disconnection()
    with pytest.raises(StateError):
        await send(s, '')
    await s.stop()


async def test_does_not_send_connects_and_stops(server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.READ_SOCKET_STATE_BEFORE_SOCKET_IS_PREPARED)
    with pytest.raises(StateError):
        await send(s, '')
    await c.connection()
    await s.stop()
    await c.disconnection()


async def test_receives_unexpected_message_type(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        await c.connection()
        await send(s, 'socket-bytes')
        await c.disconnection()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_empty_message(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        await c.connection()
        await send(s, 'empty-message')
        await c.disconnection()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_empty_body(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        await c.connection()
        await send(s, 'empty-body')
        await c.disconnection()
        await s.stop()
    assert len(caplog.records) == 1


async def test_receives_closed(future, server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED)
    await c.connection()
    await send(s, 'mock-closed')
    await s.stop()
    await c.disconnection()
    future.set_exception.assert_called_once_with(StateError)


async def test_receives_exception(future, server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED)
    await c.connection()
    await send(s, 'mock-exception')
    await s.stop()
    await c.disconnection()
    args, _ = future.set_exception.call_args
    error, = args
    assert isinstance(error, JavascriptError)
    message, = error.args
    assert isinstance(message, str)


async def test_receives_result(future, server_and_client):
    s, c = server_and_client
    await s._start(DebugScenario.RECEIVE_SOCKET_MESSAGE_BEFORE_SERVER_IS_STOPPED)
    await c.connection()
    await send(s, 'mock-result')
    await s.stop()
    await c.disconnection()
    args, _ = future.set_result.call_args
    output, = args
    assert output == 0


async def test_does_not_open(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        await c.connection()
        open(s, 0)
        await s.stop()
        await c.disconnection()
    assert len(caplog.records) == 1


async def test_echoes(server_and_client):
    s, c = server_and_client
    await s.start()
    await c.connection()
    open(s)
    await send(s, 'echo', 1)
    await c.disconnection()
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '1'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls(server_and_client):
    s, c = server_and_client
    await s.start()
    await c.connection()
    open(s)
    await send(s, 'call', {'name': 'name', 'args': [2, 3]})
    await c.disconnection()
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[2, 3]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls_async(server_and_client):
    s, c = server_and_client
    await s.start()
    await c.connection()
    open(s)
    await send(s, 'call', {'name': 'async', 'args': [2, 3]})
    await c.disconnection()
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'result'
    assert c.body['payload'] == '[2, 3]'
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY


async def test_calls_error(caplog, server_and_client):
    with caplog.at_level(logging.ERROR):
        s, c = server_and_client
        await s.start()
        await c.connection()
        open(s)
        await send(s, 'call', {'name': 'error', 'args': [2, 3]})
        await c.disconnection()
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
    await c.connection()
    open(s)
    await send(s, 'type')
    await c.disconnection()
    await s.stop()
    assert len(c.body) == 4
    assert c.body['type'] == 'exception'
    assert isinstance(c.body['payload'], str)
    assert c.body['channel'] == CHANNEL_KEY
    assert c.body['future'] == FUTURE_KEY
