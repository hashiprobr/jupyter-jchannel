import json
import asyncio
import pytest

from aiohttp import ClientSession, WSMsgType
from jchannel import Server, DebugScenario


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
    mocker.patch.dict('jchannel.os.environ', environ)
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
def s():
    return Server()


async def test_stops(s):
    await s.stop()


async def test_starts_and_stops_without_client(s):
    await s.start()
    await s.stop()


async def test_starts_twice_and_stops_without_client(s):
    await s.start()
    await s.start()
    await s.stop()


async def test_starts_and_stops_twice_without_client(s):
    await s.start()
    task_0 = s.stop()
    task_1 = s.stop()
    await task_0
    await task_1


@pytest.fixture
def client(mocker):
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
                                case 'disconnect':
                                    await socket.close()
                                    break
                                case _:
                                    await socket.send_str(message.data)
            self.disconnected.set()

    client = Client('http://localhost:8889')

    def side_effect(source):
        assert source == 'jchannel.start("http://localhost:8889");'
        asyncio.create_task(client.start())

    default = mocker.patch('jchannel.default')
    default.inject_code.side_effect = side_effect

    return client


def start_with_sentinel(s, scenario):
    return asyncio.create_task(s._start(scenario))


async def test_starts_and_stops(s, client):
    await s.start()
    await client.connection()
    await s.stop()
    await client.disconnection()


async def test_starts_and_stops_twice(s, client):
    await start_with_sentinel(s, DebugScenario.STOP_BETWEEN_STOP_AND_CLEAN)
    await client.connection()
    task_0 = s.stop()
    task_1 = s.stop()
    await task_0
    await task_1
    await client.disconnection()


async def test_stops_and_does_not_restart(s, client):
    await s.start()
    await client.connection()
    await s._send('disconnect')
    await s.stop()
    await client.disconnection()


async def test_restarts_and_stops(s, client):
    await start_with_sentinel(s, DebugScenario.RESTART_BETWEEN_DISCONNECT_AND_STOP)
    await client.connection()
    await s._send('disconnect')
    await s.stop()
    await client.disconnection()


async def test_restarts_and_does_not_stop(s, client):
    await start_with_sentinel(s, DebugScenario.STOP_BETWEEN_DISCONNECT_AND_RESTART)
    await client.connection()
    await s._send('disconnect')
    with pytest.raises(RuntimeError):
        await s.stop()
    await s.stop()
    await client.disconnection()
