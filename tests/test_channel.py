import asyncio
import pytest

from unittest.mock import Mock
from jchannel.channel import Channel


pytestmark = pytest.mark.asyncio(scope='module')


@pytest.fixture
def server(mocker):
    mock = Mock()

    mocker.patch.object(mock, 'channels', {})

    async def side_effect(body_type, input, channel_key, timeout):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        future.set_result([body_type, input, channel_key, timeout])
        return future

    mock._send.side_effect = side_effect

    return mock


@pytest.fixture
def c(server):
    return Channel(server)


async def test_instantiates(server, c):
    assert server.channels[id(c)] == c
    assert c.server == server
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


async def test_echoes(c):
    output = ['echo', (2, 3), id(c), 3]
    assert await c.echo(2, 3) == output


async def test_calls(c):
    output = ['call', {'name': 'name', 'args': (2, 3)}, id(c), 3]
    assert await c.call('name', 2, 3) == output
