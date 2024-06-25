import pytest
import jchannel

from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio(scope='module')


HOST = '127.0.0.1'
PORT = 8888
URL = 'http://localhost:8889'
HEARTBEAT = 3


async def test_starts(mocker):
    server = AsyncMock()

    def side_effect(host, port, url, heartbeat):
        assert host == HOST
        assert port == PORT
        assert url == URL
        assert heartbeat == HEARTBEAT
        return server

    Server = mocker.patch('jchannel.Server')
    Server.side_effect = side_effect

    assert await jchannel.start(HOST, PORT, URL, HEARTBEAT) is server
    server._start.assert_awaited_once()
