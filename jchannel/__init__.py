from jchannel.server import Server


async def start(host='localhost', port=8889, url=None, heartbeat=30):
    server = Server(host, port, url, heartbeat)

    await server._start()

    return server
