import asyncio
import logging
import pytest

from jchannel.types import AbstractServer, StateError
from jchannel.channel import Channel

pytestmark = pytest.mark.asyncio(scope='module')


CODE = '() => true'


async def test_does_not_instantiate():
    with pytest.raises(TypeError):
        Channel(True, CODE)


class Server(AbstractServer):
    def __init__(self):
        self._closed = False
        super().__init__()

    async def _send(self, body_type, input, channel_key, timeout):
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        if body_type == 'open':
            self._closed = False

        if self._closed:
            future.set_exception(StateError)
        else:
            future.set_result([body_type, channel_key, input, timeout])

        return future


@pytest.fixture
def server():
    return Server()


@pytest.fixture
def c(server):
    return Channel(server, CODE)


async def test_instantiates(server, c):
    assert server._channels[id(c)] is c
    assert c.handler is None


async def test_does_not_set_none_handler(c):
    with pytest.raises(ValueError):
        c.handler = None


async def test_handles_call_with_result(c):
    class Handler:
        def name(self, a, b):
            return a + b
    c.handler = Handler()
    assert c._handle_call('name', [1, 2]) == 3


async def test_handles_call_with_exception(c):
    class Handler:
        def name(self, a, b):
            raise Exception
    c.handler = Handler()
    with pytest.raises(Exception):
        c._handle_call('name', [1, 2])


async def test_does_not_handle_call_without_handler(c):
    with pytest.raises(ValueError):
        c._handle_call('name', [1, 2])


async def test_does_not_handle_call_without_handler_attribute(c):
    c.handler = object()
    with pytest.raises(AttributeError):
        c._handle_call('name', [1, 2])


async def test_does_not_handle_call_without_callable_handler_attribute(c):
    class Handler:
        def __init__(self):
            self.name = True
    c.handler = Handler()
    with pytest.raises(TypeError):
        c._handle_call('name', [1, 2])


async def test_opens(c):
    output = ['open', CODE, id(c), 3]
    assert await c.open() == output


async def test_closes(c):
    output = ['close', None, id(c), 3]
    assert await c.close() == output


async def test_opens_does_not_destroy_and_closes(c):
    with pytest.raises(StateError):
        async with c as channel:
            await channel.destroy()


async def test_echoes(c):
    output = ['echo', (1, 2), id(c), 3]
    assert await c.echo(1, 2) == output


async def test_echoes_twice(caplog, server, c):
    with caplog.at_level(logging.WARNING):
        server._closed = True
        output = ['echo', (1, 2), id(c), 3]
        assert await c.echo(1, 2) == output
    assert len(caplog.records) == 1


async def test_calls(c):
    output = ['call', {'name': 'name', 'args': (1, 2)}, id(c), 3]
    assert await c.call('name', 1, 2) == output


async def test_calls_twice(caplog, server, c):
    with caplog.at_level(logging.WARNING):
        server._closed = True
        output = ['call', {'name': 'name', 'args': (1, 2)}, id(c), 3]
        assert await c.call('name', 1, 2) == output
    assert len(caplog.records) == 1


async def test_destroys_and_does_not_call_and_does_not_destroy(server, c):
    c.destroy()
    assert id(c) not in server._channels
    with pytest.raises(StateError):
        await c.call('name', 1, 2)
    with pytest.raises(StateError):
        c.destroy()
