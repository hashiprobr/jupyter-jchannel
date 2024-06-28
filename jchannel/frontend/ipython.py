from IPython.display import HTML, display, clear_output
from ipywidgets import Output
from jchannel.frontend.abstract import AbstractFrontend


SHEET = '''
.cell-output-ipywidget-background {
    background-color: transparent !important;
}
'''


class IPythonFrontend(AbstractFrontend):
    def __init__(self):
        super().__init__()
        self.output = Output(_view_count=0)

    def _run(self, code):
        if self.output._view_count == 0:
            style = HTML(f'<style>{SHEET}</style>')
            display(style)
            display(self.output)

        with self.output:
            script = HTML(f'<script>{code}</script>')
            display(script)
            clear_output()
