from IPython.display import HTML
from jchannel.frontend.abstract import AbstractFrontend


class IPythonFrontend(AbstractFrontend):
    def inject_file(self, url):
        HTML(f'<script src="{url}"></script>')

    def inject_code(self, source):
        HTML(f'<script>{source}</script>')
