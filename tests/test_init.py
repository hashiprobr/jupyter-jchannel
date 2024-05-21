import asyncio
import logging
import pytest
import jchannel

from unittest.mock import Mock

pytestmark = pytest.mark.asyncio(scope='module')


HOST = '127.0.0.1'
PORT = 8888
URL = 'ws://localhost:8889'
HEARTBEAT = 3


def mock_server(mocker, error):
    async def instance_side_effect():
        if error:
            raise Exception

    server = Mock()
    server._start.side_effect = instance_side_effect

    def constructor_side_effect(host, port, url, heartbeat):
        assert host == HOST
        assert port == PORT
        assert url == URL
        assert heartbeat == HEARTBEAT
        return server

    Server = mocker.patch('jchannel.Server')
    Server.side_effect = constructor_side_effect

    return server


def start():
    return jchannel.start(HOST, PORT, URL, HEARTBEAT)


async def test_starts(mocker):
    server = mock_server(mocker, False)
    assert start() is server
    await asyncio.sleep(0)


async def test_does_not_start(caplog, mocker):
    with caplog.at_level(logging.ERROR):
        server = mock_server(mocker, True)
        assert start() is server
        await asyncio.sleep(0)
    assert len(caplog.records) == 1
