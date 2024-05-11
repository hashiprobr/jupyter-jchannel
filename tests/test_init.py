import jchannel

from unittest.mock import Mock


HOST = 'a'
PORT = 0
URL = 'b'
HEARTBEAT = 1


def test_starts(mocker):
    mock = Mock()

    Server = mocker.patch('jchannel.Server')
    Server.return_value = mock

    server = jchannel.start(HOST, PORT, URL, HEARTBEAT)
    assert server is mock

    Server.assert_called_once_with(HOST, PORT, URL, HEARTBEAT)
    mock.start.assert_called_once()
