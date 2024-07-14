import re
import shlex

from time import sleep
from signal import SIGINT
from subprocess import Popen, PIPE, STDOUT


PATTERN = re.compile(r'(https://.+\.trycloudflare\.com)')

TIMEOUT = 5


class Tunnel:
    def __init__(self, path):
        self.path = path
        self.process = None

    def ingress(self, host, port):
        self.egress()

        args = shlex.split(f'{self.path} --url http://{host}:{port}')
        self.process = Popen(args, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

        for line in self.process.stdout:
            match = PATTERN.search(line.decode())

            if match:
                url = match.group(0)

                # The Cloudflare documentation
                # recommends waiting some time.
                sleep(TIMEOUT)

                return url

        raise ConnectionError('Could not set up tunnel')

    def egress(self):
        if self.process is not None:
            self.process.send_signal(SIGINT)
            self.process = None
