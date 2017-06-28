# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='5GEM_image_robot',
    version='0.1.0',
    description='',
    long_description=readme,
    author='Magnus Åkerman',
    author_email='magnus.akerman@chalmers.se',
    url='https://github.com/MagnusAk78/5GEM-image-robot',
    license=license,
    packages=find_packages(exclude=('tests'))
)