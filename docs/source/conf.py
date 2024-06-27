import sys
import os

sys.path.append(os.path.abspath('../..'))


project = 'jupyter-jchannel'
copyright = ' 2024 Marcelo Hashimoto'

extensions = ['sphinx.ext.autodoc']
add_module_names = False

autoclass_content = 'both'
