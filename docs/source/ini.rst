===========
alfajor.ini
===========


.. code-block:: ini

  [default-targets]
  default+browser=wsgi

  [self-tests]
  wsgi=wsgi
  *=selenium
  zero=zero

  [self-tests+browser.wsgi]
  server-entry-point = tests.browser.webapp:webapp()
  base_url = http://localhost

  [self-tests+browser.selenium]
  cmd = alfajor-invoke tests.browser.webapp:run
  server_url = http://localhost:8008
  ping-address = localhost:8008
