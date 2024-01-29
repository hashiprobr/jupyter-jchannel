import json
import asyncio
import logging
import pytest

from aiohttp import ClientSession, WSMsgType
from jchannel.server import Server, DebugScenario


HOST = 's'
PORT = 0
HEARTBEAT = 1


pytestmark = pytest.mark.asyncio(scope='module')


@pytest.mark.parametrize('tag, url', [
    (False, 'http://s:0'),
    (True, 'https://s:0'),
])
async def test_instantiates(mocker, tag, url):
    if tag:
        environ = {'COLAB_RELEASE_TAG': ''}
    else:
        environ = {}
    mocker.patch.dict('jchannel.server.os.environ', environ)
    server = Server(HOST, PORT, None, HEARTBEAT)
    assert server.url == url


@pytest.mark.parametrize('input, output', [
    ('http://a', 'http://a'),
    ('http://a/', 'http://a'),
    ('http://a//', 'http://a'),
    ('http:///a', 'http:///a'),
    ('http:///a/', 'http:///a'),
    ('http:///a//', 'http:///a'),
    ('http:////a', 'http:////a'),
    ('http:////a/', 'http:////a'),
    ('http:////a//', 'http:////a'),
    ('http://a/b', 'http://a/b'),
    ('http://a/b/', 'http://a/b'),
    ('http://a/b//', 'http://a/b'),
    ('http://a//b', 'http://a//b'),
    ('http://a//b/', 'http://a//b'),
    ('http://a//b//', 'http://a//b'),
    ('https://a', 'https://a'),
    ('https://a/', 'https://a'),
    ('https://a//', 'https://a'),
    ('https:///a', 'https:///a'),
    ('https:///a/', 'https:///a'),
    ('https:///a//', 'https:///a'),
    ('https:////a', 'https:////a'),
    ('https:////a/', 'https:////a'),
    ('https:////a//', 'https:////a'),
    ('https://a/b', 'https://a/b'),
    ('https://a/b/', 'https://a/b'),
    ('https://a/b//', 'https://a/b'),
    ('https://a//b', 'https://a//b'),
    ('https://a//b/', 'https://a//b'),
    ('https://a//b//', 'https://a//b'),
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


async def test_does_not_instantiate_with_non_http_url_start():
    with pytest.raises(ValueError):
        Server(HOST, PORT, 'file://a', HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http:/a',
    'https:/a',
])
async def test_does_not_instantiate_with_invalid_url_start(url):
    with pytest.raises(ValueError):
        Server(HOST, PORT, url, HEARTBEAT)


@pytest.mark.parametrize('url', [
    'http://',
    'http:///',
    'http:////',
    'https://',
    'https:///',
    'https:////',
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
def server(mocker):
    mocker.patch('jchannel.server.frontend')

    return Server()


async def test_stops(server):
    await server.stop()


async def test_starts_and_stops_without_client(server):
    await server.start()
    await server.stop()


async def test_starts_twice_and_stops_without_client(server):
    await server.start()
    await server.start()
    await server.stop()


async def test_starts_and_stops_twice_without_client(server):
    await server.start()
    task_0 = server.stop()
    task_1 = server.stop()
    await task_0
    await task_1


async def test_does_not_send_without_client(server):
    with pytest.raises(RuntimeError):
        await server._send('close')


async def test_does_not_send(server):
    await server.start()
    task = server.stop()
    with pytest.raises(RuntimeError):
        await server._send('close')
    await task


class Client:
    def __init__(self, url):
        self.url = url

    async def start(self):
        self.connected = asyncio.Event()
        self.disconnected = asyncio.Event()
        asyncio.create_task(self._run())

    async def connection(self):
        await self.connected.wait()

    async def disconnection(self):
        await self.disconnected.wait()

    async def _run(self):
        async with ClientSession() as session:
            async with session.ws_connect(f'{self.url}/socket', autoping=False) as socket:
                self.connected.set()
                async for message in socket:
                    if message.type == WSMsgType.PING:
                        await socket.pong()
                    else:
                        kwargs = json.loads(message.data)
                        match kwargs['type']:
                            case 'close':
                                await socket.close()
                                break
                            case 'bytes':
                                await socket.send_bytes(b'')
                            case 'empty':
                                await socket.send_str('')
                            case _:
                                await socket.send_str(message.data)
        self.disconnected.set()


def client():
    return Client('http://localhost:8889')


@pytest.fixture
def server_with_client(mocker):
    s = Server()
    c = client()

    def side_effect(source):
        assert source == 'jchannel.start("http://localhost:8889");'
        asyncio.create_task(c.start())

    frontend = mocker.patch('jchannel.server.frontend')
    frontend.inject_code.side_effect = side_effect

    return s, c


def start_with_sentinel(s, scenario):
    return asyncio.create_task(s._start(scenario))


async def test_connects_breaks_and_stops(server_with_client):
    server, client = server_with_client
    await start_with_sentinel(server, DebugScenario.STOP_AFTER_BREAK)
    await client.connection()
    task_0 = server.stop()
    task_1 = server.stop()
    await task_0
    await task_1
    await client.disconnection()


async def test_connects_disconnects_breaks_and_stops(server_with_client):
    server, client = server_with_client
    await start_with_sentinel(server, DebugScenario.DISCONNECT_BEFORE_BREAK)
    await client.connection()
    await server._send('close')
    await server.stop()
    await client.disconnection()


async def test_connects_disconnects_and_does_not_stop(server_with_client):
    server, client = server_with_client
    await start_with_sentinel(server, DebugScenario.STOP_AFTER_DISCONNECT)
    await client.connection()
    await server._send('close')
    with pytest.raises(RuntimeError):
        await server.stop()
    await server.stop()
    await client.disconnection()


async def test_does_not_connect_breaks_and_stops(server_with_client):
    server, client = server_with_client
    await start_with_sentinel(server, DebugScenario.CONNECT_BEFORE_BREAK)
    await server.stop()
    await client.connection()
    await client.disconnection()


async def test_breaks_does_not_connect_and_stops(server_with_client):
    server, client = server_with_client
    await start_with_sentinel(server, DebugScenario.CONNECT_BEFORE_CLEAN)
    await server.stop()
    await client.connection()
    await client.disconnection()


async def test_connects_does_not_connect_breaks_and_stops(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        server, client_0 = server_with_client
        client_1 = client()
        await server.start()
        await client_1.start()
        await client_0.connection()
        await client_1.connection()
        await server.stop()
        await client_0.disconnection()
        await client_1.disconnection()
    assert caplog.records


async def test_receives_unexpected_message_type(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        server, client = server_with_client
        await start_with_sentinel(server, DebugScenario.RECEIVE_BEFORE_CLEAN)
        await server.start()
        await client.connection()
        await server._send('bytes')
        await server.stop()
        await client.disconnection()
    assert caplog.records


async def test_receives_unexpected_data_type(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        server, client = server_with_client
        await start_with_sentinel(server, DebugScenario.RECEIVE_BEFORE_CLEAN)
        await client.connection()
        await server._send('error')
        await server.stop()
        await client.disconnection()
    assert caplog.records


async def test_raises_exception(caplog, server_with_client):
    with caplog.at_level(logging.ERROR):
        server, client = server_with_client
        await start_with_sentinel(server, DebugScenario.EXCEPT_BEFORE_CLEAN)
        await client.connection()
        await server._send('empty')
        await server.stop()
        await client.disconnection()
    assert caplog.records
