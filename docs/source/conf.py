import sys
import os

sys.path.insert(0, os.path.abspath('../..'))


project = 'jupyter-jchannel'
copyright = ' 2024 Marcelo Hashimoto'

extensions = ['sphinx.ext.autodoc']
add_module_names = False

autoclass_content = 'both'
