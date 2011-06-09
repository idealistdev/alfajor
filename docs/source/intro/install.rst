==================
Installing Alfajor
==================

The Alfajor repository is available for check out from our `github page`_.

.. _`github page`: https://github.com/idealist/Alfajor


Setup:
______

1) Create and activate a virtualenv_ (optional)
1) Next we need to install dependencies.  From the top of the distribution
run::

    $ python setup.py develop

1) Next install nose using either::

    $ easy_install nose

OR::

    $ pip install nose



.. _virtualenv: http://pypi.python.org/pypi/virtualenv

If you don't have Selenium installed, download `Selenium Server`_.  All you need
is the selenium-server.jar, and no configuration is required.

Run it with::

    $ java -jar selenium-server.jar

.. _`Selenium Server`: http://seleniumhq.org/download/

.. todo:: List which versions of Selenium are required


See it in action:
_________________

After following the steps above, the Alfajor plugin should be available
and listing command-line options for nose.  You can verify this by typing::

    $ nosetests --help

To run the standard tests that use an in-process web app through a WSGI
interface, simply type::

    $ nosetests

To run the same tests but using a real web browser, type::

    $ nosetests --browser=firefox

.. admonition:: You can use all sorts of browsers

    A list of valid browsers is:
      *firefox
      *mock
      *firefoxproxy
      *pifirefox
      *chrome
      *iexploreproxy
      *iexplore
      *firefox3
      *safariproxy
      *googlechrome
      *konqueror
      *firefox2
      *safari
      *piiexplore
      *firefoxchrome
      *opera
      *iehta
      *custom

.. admonition:: .ini Files

    The main action of Alfajor is directed through an :doc:`alfajor.ini </ini>` file.  At the
    simplest, this can be anywhere on the filesystem (see the --alfajor-config
    option in nose) or placed in the same directory as the .py file that
    configures the WebBrowser.  See `tests/webapp/{__init__.py,alfajor.ini}`.
