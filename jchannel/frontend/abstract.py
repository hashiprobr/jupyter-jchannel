# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


import os

from abc import ABC, abstractmethod
from importlib import metadata


class AbstractFrontend(ABC):
    def __init__(self):
        try:
            url = os.environ['JCHANNEL_CLIENT_URL']
        except KeyError:
            version = metadata.version('jupyter-jchannel')

            url = f'https://unpkg.com/jupyter-jchannel-client@{version}/dist/main.js'

        self.url = url

    def run(self, code):
        self._run(f'''
            if (!self.jchannelLoaded) {{
                self.jchannelLoaded = new Promise((resolve, reject) => {{
                    const script = document.createElement('script');

                    script.addEventListener('load', () => {{
                        resolve();
                    }});

                    script.addEventListener('error', (event) => {{
                        reject(event);
                    }});

                    script.src = '{self.url}';

                    document.head.appendChild(script);
                }});
            }}

            self.jchannelLoaded.then(() => {{
                {code};
            }}).catch((event) => {{
                console.error('Script error event', event);
            }});
        ''')

    @abstractmethod
    def _run(self, code):
        '''
        Runs JavaScript code.
        '''
