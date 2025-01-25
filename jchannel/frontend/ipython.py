# Copyright (c) 2024 Marcelo Hashimoto
#
# This program and the accompanying materials are made
# available under the terms of the Eclipse Public License 2.0
# which is available at https://www.eclipse.org/legal/epl-2.0/
#
# SPDX-License-Identifier: EPL-2.0


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
        self.hidden = True
        self.output = Output(_view_count=0)
        self.output.observe(self._handle, '_view_count')

    def _handle(self, change):
        if change['new'] == 0:
            self.hidden = True

    def _run(self, code):
        if self.hidden:
            self.hidden = False
            style = HTML(f'<style>{SHEET}</style>')
            display(style)
            display(self.output)

        with self.output:
            # NOTE: Using IPython.display.Javascript
            # would be more elegant, but does not seem
            # to be working in Visual Studio Code.
            script = HTML(f'<script>{code}</script>')
            display(script)
            clear_output()
