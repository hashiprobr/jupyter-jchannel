from IPython.display import clear_output, display, Javascript
from ipywidgets import Output
from jchannel.frontend.abstract import AbstractFrontend


class IPythonFrontend(AbstractFrontend):
    def __init__(self):
        super().__init__()
        self.output = Output(_view_count=0)

    def _run(self, code):
        if self.output._view_count == 0:
            display(self.output)

        with self.output:
            element = Javascript(code)
            display(element)
            clear_output()
