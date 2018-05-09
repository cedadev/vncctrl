from setuptools import setup, find_packages
import sys, os

from vncctrl import __version__

setup(name='vncctrl',
      version=__version__,
      description="Initiate a VNC connection within Python",
      long_description="",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Alan Iwi',
      author_email='alan.iwi@stfc.ac.uk',
      url='https://github.com/cedadev/vncctrl',
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      vncctrl = vncctrl._vncctrl:main
      """,
      )
