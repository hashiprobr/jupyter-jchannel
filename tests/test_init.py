import asyncio
import logging
import pytest
import jchannel

from unittest.mock import Mock


HOST = 'a'
PORT = 0
URL = 'b'
HEARTBEAT = 1


pytestmark = pytest.mark.asyncio(scope='module')


async def test_starts(mocker, caplog):
    with caplog.at_level(logging.ERROR):
        async def side_effect():
            raise Exception

        server = Mock()
        server._start.side_effect = side_effect

        Server = mocker.patch('jchannel.Server')
        Server.return_value = server

        assert jchannel.start(HOST, PORT, URL, HEARTBEAT) is server
        Server.assert_called_once_with(HOST, PORT, URL, HEARTBEAT)

        await asyncio.sleep(0)
    assert len(caplog.records) == 1
