# -*- coding: utf-8 -*-
"""
$Id: setup.py 335 2018-03-23 10:39:06Z aokada $
"""

from setuptools import setup
from scripts.ecsub import __version__

import sys
sys.path.append('./tests')

setup(name='ecsub',
      version=__version__,
      description="ecsub is a command-line tool that submit batch scripts to AWS ECS.",
      long_description="""""",

      classifiers=[
          #   3 - Alpha
          #   4 - Beta
          #   5 - Production/Stable
          'Development Status :: 3 - Alpha',
          # Indicate who your project is intended for
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering :: Bio-Informatics',
          'Topic :: Scientific/Engineering :: Information Analysis',

          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      
      keywords=' cloud bioinformatics',
      author='Ai Okada',
      author_email='genomon.devel@gmail.com',
      url='https://github.com/aokad/ecsub.git',
      license='GPLv3',
      
      package_dir = {'': 'scripts'},
      packages=['ecsub'],
      scripts=['ecsub'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
          'awscli',
          'boto3',
          'pytz',
          'six'
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      package_data = {
      },
      test_suite = 'unit_tests.suite'
)
