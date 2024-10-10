# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


import asyncio
import pytest

from jchannel.registry import Registry

pytestmark = pytest.mark.asyncio(loop_scope='module')


@pytest.fixture
def r():
    return Registry()


async def test_stores_and_retrieves_twice(r):
    loop = asyncio.get_running_loop()
    future_0 = loop.create_future()
    key_0 = r.store(future_0)
    assert r.retrieve(key_0) is future_0
    with pytest.raises(KeyError):
        r.retrieve(key_0)
    future_1 = loop.create_future()
    key_1 = r.store(future_1)
    assert r.retrieve(key_1) is future_1
    with pytest.raises(KeyError):
        r.retrieve(key_1)


async def test_stores_and_retrieves_queue(r):
    loop = asyncio.get_running_loop()
    future_0 = loop.create_future()
    key_0 = r.store(future_0)
    future_1 = loop.create_future()
    key_1 = r.store(future_1)
    assert r.retrieve(key_0) is future_0
    with pytest.raises(KeyError):
        r.retrieve(key_0)
    assert r.retrieve(key_1) is future_1
    with pytest.raises(KeyError):
        r.retrieve(key_1)


async def test_stores_and_retrieves_stack(r):
    loop = asyncio.get_running_loop()
    future_0 = loop.create_future()
    key_0 = r.store(future_0)
    future_1 = loop.create_future()
    key_1 = r.store(future_1)
    assert r.retrieve(key_1) is future_1
    with pytest.raises(KeyError):
        r.retrieve(key_1)
    assert r.retrieve(key_0) is future_0
    with pytest.raises(KeyError):
        r.retrieve(key_0)


async def test_stores_and_clears(r):
    loop = asyncio.get_running_loop()
    future_0 = loop.create_future()
    key_0 = r.store(future_0)
    future_1 = loop.create_future()
    key_1 = r.store(future_1)
    r.clear()
    with pytest.raises(KeyError):
        r.retrieve(key_1)
    assert future_1.cancelled()
    with pytest.raises(KeyError):
        r.retrieve(key_0)
    assert future_0.cancelled()
