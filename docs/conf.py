# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Amica'
copyright = '2025, Artem Savelov, Carrie Ching, André Frank Krause'
author = 'Artem Savelov, Carrie Ching, André Frank Krause'
release = 'proto2'

# add path to the python files in the parent directory
# still needed for the "sphinx.ext.viewcode" extension
import sys
from pathlib import Path
sys.path.insert(0, str(Path('../src').resolve()))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
   'autoapi.extension', # automagically generate API doc from a folder full of python files.
   'sphinx.ext.napoleon', # for numpy style docstrings
   'sphinx.ext.intersphinx', # link to official python docs
   'sphinx_copybutton', # copy button for code snippets
   'sphinx_autodoc_typehints', # automatic insertion of argument types into doc
   'myst_parser', # for markdown parsing to include the README.md
   'sphinx.ext.viewcode', # additional html-files with highlighted version of the source code
]

# folder containing the python files to be documented:
autoapi_dirs = ['../src']

# auto link to official python docs
intersphinx_mapping = { "py": ("https://docs.python.org/3", None), }

templates_path = ['_templates']
exclude_patterns = ['docs', 'assets', '_build', '_static', '_templates']

html_theme = 'furo'
html_static_path = ['_static']
