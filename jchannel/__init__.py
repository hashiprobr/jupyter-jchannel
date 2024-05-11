from jchannel.server import Server


def start(host='localhost', port=8889, url=None, heartbeat=30):
    server = Server(host, port, url, heartbeat)
    server.start()
    return server
