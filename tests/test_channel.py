import asyncio
import pytest

from jchannel.error import StateError
from jchannel.channel import Channel


pytestmark = pytest.mark.asyncio(scope='module')


class Server:
    def __init__(self):
        self.closed = False
        self.channels = {}

    async def _send(self, body_type, input, channel_key, timeout):
        if body_type == 'error':
            raise Exception
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        if self.closed:
            self.closed = False
            future.set_exception(StateError)
        else:
            future.set_result([body_type, input, channel_key, timeout])
        return future


@pytest.fixture
def server():
    return Server()


@pytest.fixture
def c(server):
    return Channel(server, 'code')


async def test_instantiates(server, c):
    assert server.channels[id(c)] == c
    assert c.server == server
    assert c.code == 'code'
    assert c.handler is None


async def test_sets_handler(c):
    handler = object()
    c.set_handler(handler)
    assert c.handler is handler


async def test_does_not_set_none_handler(c):
    with pytest.raises(ValueError):
        c.set_handler(None)


async def test_handles_call_with_result(c):
    class Handler:
        def name(self, a, b):
            return a + b
    c.set_handler(Handler())
    assert c._handle_call('name', [2, 3]) == 5


async def test_handles_call_with_exception(c):
    class Handler:
        def name(self, a, b):
            raise Exception
    c.set_handler(Handler())
    with pytest.raises(Exception):
        c._handle_call('name', [2, 3])


async def test_does_not_handle_call_without_handler(c):
    with pytest.raises(ValueError):
        c._handle_call('name', [2, 3])


async def test_does_not_handle_call_without_handler_attribute(c):
    c.set_handler(object())
    with pytest.raises(AttributeError):
        c._handle_call('name', [2, 3])


async def test_does_not_handle_call_without_callable_handler_attribute(c):
    class Handler:
        def __init__(self):
            self.name = 0
    c.set_handler(Handler())
    with pytest.raises(TypeError):
        c._handle_call('name', [2, 3])


async def test_opens(c):
    output = ['open', 'code', id(c), 3]
    assert await c.open() == output


async def test_closes(c):
    output = ['close', None, id(c), 3]
    assert await c.close() == output


async def test_opens_does_not_send_and_closes(c):
    with pytest.raises(Exception):
        async with c as channel:
            await channel._send('error', None, 3)


async def test_echoes(c):
    output = ['echo', (2, 3), id(c), 3]
    assert await c.echo(2, 3) == output


async def test_echoes_twice(server, c):
    server.closed = True
    output = ['echo', (2, 3), id(c), 3]
    assert await c.echo(2, 3) == output


async def test_calls(c):
    output = ['call', {'name': 'name', 'args': (2, 3)}, id(c), 3]
    assert await c.call('name', 2, 3) == output


async def test_calls_twice(server, c):
    server.closed = True
    output = ['call', {'name': 'name', 'args': (2, 3)}, id(c), 3]
    assert await c.call('name', 2, 3) == output
