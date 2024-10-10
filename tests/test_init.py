# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


import pytest
import jchannel

from unittest.mock import AsyncMock

pytestmark = pytest.mark.asyncio()


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
