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
            new Promise((resolve, reject) => {{
                if (self.jchannel) {{
                    resolve();
                }} else {{
                    const script = document.createElement('script');

                    script.addEventListener('load', () => {{
                        resolve();
                    }});

                    script.addEventListener('error', (event) => {{
                        reject(event);
                    }});

                    script.src = '{self.url}';

                    document.head.appendChild(script);
                }}
            }}).then(() => {{
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
