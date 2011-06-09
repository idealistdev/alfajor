=============================
Getting started using Alfajor
=============================


In this tutorial we will be showing you how to use Alfajor to greatly enhance
the tastiness of your functional testing.

We are assuming you have properly :doc:`installed Alfajor and ran the browser
based test suite to ensure everything is working </intro/install>`.


-----------------------
The Example Application
-----------------------

To start with, you are going to need a web application to test.  Since we are
nice, we've included an example application in the project for you.  You can
find it in ./tests/examples.  The application is a simple recommendation
system that under the covers is just an extremely simple `WSGI application`_.

.. _`WSGI application`: http://wsgi.org

Let's start by getting to know our example application.  You should be able
to start it up using the following command: ::

    $ alfajor-invoke tests.examples.webapp:run

Now if you point your web browser at http://127.0.0.1:8009, you should see
the silly example application.  Try filling in the form a few different ways
and get familiar with the output.

Alright, now let's press CTRL-c to stop your server, we've got some testing to
do.

-------------------------------
Testing the Example Application
-------------------------------

So now we've seen the application in all it's glory, we'd better write a few
tests to make sure it is functioning as expected.

Again, cuz we are such good guys over here, we've started a little test suite
that you can kick off pretty easily.  To run the tests simply type: ::

    $ nosetests tests.examples.test_simple

So let's go on a line-by-line tour through the nosetest test_name_entry in
tests/examples/test_simple

.. code-block:: python

    browser.open('/')

It is time to introduce you to the browser object.  It is going to be
available to you somewhat magically throughout each of your tests, all you
need to do is import it from your base testing module.

The :meth:`~alfajor.browsers.wsgi.WSGI.open` method will attempt to load
the **url** that is passed in.  Absolute urls, as shown in the example code,
will work by appending to your *base_url* or *server_url* setting.

.. admonition:: This magical setup is actually performed using your
    alfajor.ini file and some iems that you will place in your test modules
    __init__.py file.  For more information checkout
    `Configuring your test suite </intro/config>`_

Alright now the browser object has loaded the url, it is ready to be poked at.

.. code-block::python

    assert 'Alfajor' in browser.document['#mainTitle'].text_content

The :attr:`~alfajor.browsers.wsgi.WSGI.document` represents the HTMLDocument
element.  If you are familiar with `CSS selectors`_ this type of traversal,
should be fairly straightforward.  Basically what this is saying is, get the
:class:`~alfajor.browsers._lxml.DOMElement` element on the page with the *id*
attribute of *mainTitle*.  Once that is found use the
:attr:`~alfajor.browsers._lxml.DOMElement.text_content` which
returns text in all of the text nodes in between the found tags, to see if our
value is inside.

.. _`CSS selectors`: http://www.w3.org/TR/2001/CR-css3-selectors-20011113/

.. note:: Since the specification of the attribute id states that there can
    be only one element with this id, in an HTML document, this lookup will
    only return the first occurrence of the id.  If you are testing invalid
    HTML, consider yourself warned.

This could very easily be rewritten as such:

.. code-block::python

    assert 'Alfajor' in browser.document['h1'][0].text_content

.. admonition:: If you are curious about what more you can do with this
    document traversal system, you shoud read the chapter
    :doc:`Alfajor flavored lxml <lxml>`_

Okay so the next line we want to enter some data into a form

.. code-block::python

    browser.document['form input[name="name"]'].value = 'Juan'

So we get a handle to the input element that we want to add and simply set the
:attr:`value` attribute.





