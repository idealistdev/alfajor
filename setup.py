# Copyright Action Without Borders, Inc., the Alfajor authors and contributors.
# All rights reserved.  See AUTHORS.
#
# This file is part of 'alfajor' and is distributed under the BSD license.
# See LICENSE for more details.
"""\
Alfajor
-------

Tasty functional testing.

Alfajor provides a modern, object-oriented and browser-neutral interface to
HTTP resources.  With Alfajor, your Python scripts and test code have a live,
synchronized mirror of the browser's X/HTML DOM, even with DOM changes made on
the client by JavaScript.

Alfajor provides:

 - A straightforward 'browser' object, with an implementation that
   communicates in real-time with live web browsers via Selenium and a fast,
   no-javascript implementation via an integrated WSGI gateway

 - Use a specific browser, or, via integration with the 'nose' test runner,
   switch out the browser backend via a command line option to your tests.
   Firefox, Safari, WSGI- choose which you want on a run-by-run basis.

 - Synchronized access to the page DOM via a rich dialect of lxml, with great
   time-saving shortcuts that make tests compact, readable and fun to write.

 - Optional management of server processes under test, allowing them to
   transparently start and stop on demand as your tests run.

 - An 'apiclient' with native JSON response support, useful for testing REST
   and web api implementations at a fine-grained level.

 - A friendly BSD license.
"""

from setuptools import setup, find_packages


setup(name="alfajor",
      version="0.1",
      packages=find_packages(),

      author='Action Without Borders, Inc.',
      author_email='jason@idealist.org',  # FIXME

      description='Tasty functional testing.',
      keywords='testing test functional integration browser ajax selenium',
      long_description=__doc__,
      license='BSD',
      url='http://github.com/idealistdev/alfajor/',  # FIXME

      classifiers=[
          'Development Status :: 1 - Planning',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.5',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Browsers',
          'Topic :: Software Development :: Testing',
          'Topic :: Software Development :: Quality Assurance',
          ],

      entry_points={
          'console_scripts': [
            'alfajor-invoke=alfajor.utilities:invoke',
            ],
          'nose.plugins.0.10': [
              'alfajor = alfajor.runners.nose:Alfajor',
              ],
          },

      install_requires=[
        'Werkzeug >= 0.6',
        'lxml',
        'blinker',
        ],
      tests_require=[
        'nose == 0.11.3',
        ],
      )
