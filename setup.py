from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='vncctrl',
      version=version,
      description="Initiate a VNC connection within Python",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='Alan Iwi',
      author_email='alan.iwi@stfc.ac.uk',
      url='',
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
