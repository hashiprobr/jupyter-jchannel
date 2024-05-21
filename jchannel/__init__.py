import asyncio
import logging

from jchannel.server import Server


def start(host='localhost', port=8889, url=None, heartbeat=30):
    server = Server(host, port, url, heartbeat)
    asyncio.create_task(_start(server))
    return server


async def _start(server):
    try:
        await server._start()
    except:
        logging.exception('Could not start server')
