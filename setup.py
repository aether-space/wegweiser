# encoding: utf-8

try:
    from setuptools import setup
    has_setuptools = True
except ImportError:
    from distutils.core import setup
    has_setuptools = False


if has_setuptools:
    extra_kwargs = {
        "requires": ["Pyramid", "Sphinx"],
        "zip_safe": False
    }
else:
    extra_kwargs = {}


setup(
    name="wegweiser",
    version="0.1",
    description="Sphinx extension for autodocumenting Pyramid applications.",
    packages=["wegweiser"],
    **extra_kwargs)
