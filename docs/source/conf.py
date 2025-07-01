# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "tierkreis"
copyright = "2025, Quantinuum"
author = "Quantinuum"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "autodoc2",
    "myst_parser",
    "quantinuum_sphinx",
]
autodoc2_packages = [
    "../../tierkreis/tierkreis",
    "../../tierkreis_workers/aer_worker",
    "../../tierkreis_workers/nexus_worker",
    "../../tierkreis_workers/pytket_worker",
]

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "quantinuum_sphinx"
html_static_path = ["_static"]
html_favicon = "_static/quantinuum_favicon.svg"
