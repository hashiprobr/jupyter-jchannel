# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


import asyncio
import logging
import pytest

from jchannel.types import AbstractServer, StateError
from jchannel.channel import Channel

pytestmark = pytest.mark.asyncio(loop_scope='module')


CODE = '() => true'


async def test_does_not_instantiate():
    with pytest.raises(TypeError):
        Channel(True, CODE)


class Server(AbstractServer):
    def __init__(self):
        self._closed = False
        super().__init__()

    async def _send(self, body_type, channel_key, input, stream, timeout):
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        if body_type == 'open':
            self._closed = False

        if self._closed:
            future.set_exception(StateError)
        else:
            future.set_result([body_type, channel_key, input, stream, timeout])

        return future


@pytest.fixture
def server():
    return Server()


@pytest.fixture
def c(server):
    return Channel(server, CODE)


async def test_instantiates(server, c):
    assert server._channels[id(c)] is c
    assert c.context_timeout == 3
    assert c.handler is None


async def test_sets_context_timeout(c):
    c.context_timeout = 0
    assert c.context_timeout == 0


async def test_handles_with_result(c):
    class Handler:
        def name(self, a, b):
            return a + b
    c.handler = Handler()
    assert c._handle('name', [1, 2]) == 3


async def test_handles_with_exception(c):
    class Handler:
        def name(self, a, b):
            raise Exception
    c.handler = Handler()
    with pytest.raises(Exception):
        c._handle('name', [1, 2])


async def test_does_not_handle_without_handler_attribute(c):
    c.handler = object()
    with pytest.raises(AttributeError):
        c._handle('name', [1, 2])


async def test_does_not_handle_without_callable_handler_attribute(c):
    class Handler:
        def __init__(self):
            self.name = True
    c.handler = Handler()
    with pytest.raises(TypeError):
        c._handle('name', [1, 2])


async def test_opens(c):
    output = ['open', id(c), CODE, None, 3]
    assert await c.open() == output


async def test_closes(c):
    output = ['close', id(c), None, None, 3]
    assert await c.close() == output


async def test_opens_does_not_handle_and_closes(c):
    with pytest.raises(ValueError):
        async with c as channel:
            channel._handle('name', [1, 2])


async def test_echoes(c):
    output = ['echo', id(c), (1, 2), None, 3]
    assert await c.echo(1, 2) == output


async def test_echoes_twice(caplog, server, c):
    with caplog.at_level(logging.WARNING):
        server._closed = True
        output = ['echo', id(c), (1, 2), None, 3]
        assert await c.echo(1, 2) == output
    assert len(caplog.records) == 1


async def test_pipes(c):
    stream = object()
    output = ['pipe', id(c), None, stream, 3]
    assert await c.pipe(stream) == output


async def test_does_not_pipe_twice(server, c):
    server._closed = True
    stream = object()
    with pytest.raises(StateError):
        await c.pipe(stream)


async def test_calls(c):
    output = ['call', id(c), {'name': 'name', 'args': (1, 2)}, None, 3]
    assert await c.call('name', 1, 2) == output


async def test_calls_twice(caplog, server, c):
    with caplog.at_level(logging.WARNING):
        server._closed = True
        output = ['call', id(c), {'name': 'name', 'args': (1, 2)}, None, 3]
        assert await c.call('name', 1, 2) == output
    assert len(caplog.records) == 1


async def test_calls_with_stream(c):
    stream = object()
    output = ['call', id(c), {'name': 'name', 'args': (1, 2)}, stream, 3]
    assert await c.call_with_stream('name', stream, 1, 2) == output


async def test_does_not_call_with_stream_twice(server, c):
    server._closed = True
    stream = object()
    with pytest.raises(StateError):
        await c.call_with_stream('name', stream, 1, 2)
