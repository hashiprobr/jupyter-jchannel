import asyncio
import pytest

from jchannel.registry import Registry


pytestmark = pytest.mark.asyncio(scope='module')


@pytest.fixture
def registry():
    return Registry()


async def test_stores_and_retrieves_two_serial(registry):
    loop = asyncio.get_running_loop()
    future0 = loop.create_future()
    key0 = registry.store(future0)
    assert registry.retrieve(key0) is future0
    with pytest.raises(KeyError):
        registry.retrieve(key0)
    future1 = loop.create_future()
    key1 = registry.store(future1)
    assert registry.retrieve(key1) is future1
    with pytest.raises(KeyError):
        registry.retrieve(key1)


async def test_stores_and_retrieves_two_parallel(registry):
    loop = asyncio.get_running_loop()
    future0 = loop.create_future()
    key0 = registry.store(future0)
    future1 = loop.create_future()
    key1 = registry.store(future1)
    assert registry.retrieve(key0) is future0
    with pytest.raises(KeyError):
        registry.retrieve(key0)
    assert registry.retrieve(key1) is future1
    with pytest.raises(KeyError):
        registry.retrieve(key1)


async def test_stores_and_retrieves_two_reversed(registry):
    loop = asyncio.get_running_loop()
    future0 = loop.create_future()
    key0 = registry.store(future0)
    future1 = loop.create_future()
    key1 = registry.store(future1)
    assert registry.retrieve(key1) is future1
    with pytest.raises(KeyError):
        registry.retrieve(key1)
    assert registry.retrieve(key0) is future0
    with pytest.raises(KeyError):
        registry.retrieve(key0)
