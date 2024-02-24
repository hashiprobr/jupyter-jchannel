import pytest
import jchannel

from unittest.mock import Mock


HOST = 'a'
PORT = 0
URL = 'b'
HEARTBEAT = 1


pytestmark = pytest.mark.asyncio(scope='module')


async def test_starts(mocker):
    async def _start():
        pass

    mock = Mock()
    mock._start.return_value = _start()

    Server = mocker.patch('jchannel.Server')
    Server.return_value = mock

    server = await jchannel.start(HOST, PORT, URL, HEARTBEAT)
    assert server is mock

    Server.assert_called_once_with(HOST, PORT, URL, HEARTBEAT)
    mock._start.assert_called_once()
