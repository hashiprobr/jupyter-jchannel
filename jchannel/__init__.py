# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


from jchannel.server import Server


async def start(host='localhost', port=8889, url=None, heartbeat=30):
    '''
    Convenience function that instantiates a kernel server, starts this server
    and returns it.

    :param host: As defined in `jchannel.server.Server
        <jchannel.server.html#jchannel.server.Server>`_.
    :param port: As defined in `jchannel.server.Server
        <jchannel.server.html#jchannel.server.Server>`_.
    :param url: As defined in `jchannel.server.Server
        <jchannel.server.html#jchannel.server.Server>`_.
    :param heartbeat: As defined in `jchannel.server.Server
        <jchannel.server.html#jchannel.server.Server>`_.

    :return: The server.
    :rtype: jchannel.server.Server
    '''
    server = Server(host, port, url, heartbeat)
    await server._start()
    return server
