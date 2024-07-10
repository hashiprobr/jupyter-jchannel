import asyncio
import pytest

from jchannel.types import PseudoMetaGenerator

pytestmark = pytest.mark.asyncio(scope='module')


def create_chunks(input):
    queue = asyncio.Queue()

    for data in input:
        value = data.encode()

        queue.put_nowait(value)

    queue.put_nowait(None)

    return PseudoMetaGenerator(queue)


async def test_iterates():
    chunks = create_chunks([
        'a',
        '',
        'bc',
        '',
        'def',
    ])

    output = []

    async for chunk in chunks:
        data = chunk.decode()

        output.append(data)

    assert output == [
        'a',
        '',
        'bc',
        '',
        'def',
    ]


async def test_iterates_by_limit_of_four_1_3_7():
    chunks = create_chunks([
        'a',
        '',
        'bcd',
        '',
        'efghijk',
    ])

    output = []

    async for chunk in chunks.by_limit(4):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcd',
        'efgh',
        'ijk',
    ]


async def test_iterates_by_limit_of_four_2_4_8():
    chunks = create_chunks([
        'ab',
        '',
        'cdef',
        '',
        'ghijklmn',
    ])

    output = []

    async for chunk in chunks.by_limit(4):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcd',
        'efgh',
        'ijkl',
        'mn',
    ]


async def test_iterates_by_limit_of_four_3_5_9():
    chunks = create_chunks([
        'abc',
        '',
        'defgh',
        '',
        'ijklmnopq',
    ])

    output = []

    async for chunk in chunks.by_limit(4):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcd',
        'efgh',
        'ijkl',
        'mnop',
        'q',
    ]


async def test_iterates_by_limit_of_four_4_6_10():
    chunks = create_chunks([
        'abcd',
        '',
        'efghij',
        '',
        'klmnopqrst',
    ])

    output = []

    async for chunk in chunks.by_limit(4):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcd',
        'efgh',
        'ijkl',
        'mnop',
        'qrst',
    ]


async def test_does_not_iterate_by_non_integer_limit():
    chunks = create_chunks([])
    aiter = chunks.by_limit('8192')
    with pytest.raises(TypeError):
        await anext(aiter)


async def test_does_not_iterate_by_non_positive_limit():
    chunks = create_chunks([])
    aiter = chunks.by_limit(0)
    with pytest.raises(ValueError):
        await anext(aiter)


async def test_iterates_by_two_space_separator_flex_start():
    chunks = create_chunks([
        'abcdef  ',
        '',
        'ghijk  lmno  ',
        '',
        'pqr  st  u  ',
    ])

    output = []

    async for chunk in chunks.by_separator('  '):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcdef  ',
        'ghijk  ',
        'lmno  ',
        'pqr  ',
        'st  ',
        'u  ',
    ]


async def test_iterates_by_two_space_separator_flex_end():
    chunks = create_chunks([
        '  abcdef',
        '',
        '  ghijk  lmno',
        '',
        '  pqr  st  u',
    ])

    output = []

    async for chunk in chunks.by_separator('  '):
        data = chunk.decode()

        output.append(data)

    assert output == [
        '  ',
        'abcdef  ',
        'ghijk  ',
        'lmno  ',
        'pqr  ',
        'st  ',
        'u',
    ]


async def test_iterates_by_two_space_separator_space_around():
    chunks = create_chunks([
        ' abcdef ',
        '',
        ' ghijk  lmno ',
        '',
        ' pqr  st  u ',
    ])

    output = []

    async for chunk in chunks.by_separator('  '):
        data = chunk.decode()

        output.append(data)

    assert output == [
        ' abcdef  ',
        'ghijk  ',
        'lmno  ',
        'pqr  ',
        'st  ',
        'u ',
    ]


async def test_iterates_by_two_space_separator_space_between():
    chunks = create_chunks([
        'abcdef',
        '',
        'ghijk  lmno',
        '',
        'pqr  st  u',
    ])

    output = []

    async for chunk in chunks.by_separator('  '):
        data = chunk.decode()

        output.append(data)

    assert output == [
        'abcdefghijk  ',
        'lmnopqr  ',
        'st  ',
        'u',
    ]


async def test_does_not_iterate_by_invalid_separator():
    chunks = create_chunks([])
    aiter = chunks.by_separator(True)
    with pytest.raises(TypeError):
        await anext(aiter)


async def test_does_not_iterate_by_empty_separator():
    chunks = create_chunks([])
    aiter = chunks.by_separator(b'')
    with pytest.raises(ValueError):
        await anext(aiter)
