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
        return self._run(f'''
            const promise = new Promise((resolve, reject) => {{
                if (window.jchannel) {{
                    resolve();
                }} else {{
                    const script = document.createElement('script');

                    script.addEventListener('load', () => {{
                        resolve();
                    }});

                    script.addEventListener('error', () => {{
                        reject(new Error('Could not load client'));
                    }});

                    script.src = '{self.url}';

                    document.head.appendChild(script);
                }}
            }});

            promise.then(() => {{
                {code};
            }}).catch((error) => {{
                console.error(error.message);
            }});
        ''')

    @abstractmethod
    def _run(self, code):
        '''
        Runs JavaScript code.
        '''
