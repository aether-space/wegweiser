.. _gettingstarted:

===============
Getting started
===============

This guide explains how to use Wegweiser to autodocument your Pyramid
application.


The example app
===============

Let's assume we have a Pyramid app with the following views (taken
from the wiki app out of Pyramid's tutorial). The views' bodies are
intentionally left empty, as only the docstrings are needed for
Wegweiser to work.

.. code-block:: python
   
   from pyramid.view import view_config
   
   
   @view_config(route_name='view_wiki')
   def view_wiki(request):
       "Redirect to the FrontPage wiki page."
   
   @view_config(route_name='view_page', renderer='templates/view.pt')
   def view_page(request):
       "View a single wiki page."
   
   @view_config(route_name='add_page', renderer='templates/edit.pt')
   def add_page(request):
       "Add a new wiki page."
   
   @view_config(route_name='edit_page', renderer='templates/edit.pt')
   def edit_page(request):
       "Edit an existing wiki page."

The views are used in the following routes:

.. code-block:: python

   config.add_route('view_wiki', '/')
   config.add_route('view_page', '/{pagename}')
   config.add_route('add_page', '/add_page/{pagename}')
   config.add_route('edit_page', '/{pagename}/edit_page')

Documenting the routes is now as easy as completing the following steps:

#. :ref:`Install Wegweiser <installing>`
#. :ref:`Configure Sphinx and Wegweiser <configuring>`
#. :ref:`documenting`


.. _installing:

Installing wegweiser
====================

See the `Sphinx documentation about extensions
<http://sphinx-doc.org/extensions.html>`_. In short, you must add
``"wegweiser"`` to ``extensions`` in ``conf.py`` and Sphinx must be
able to import the ``wegweiser`` package.


.. _configuring:

Configuration
=============

Add the following lines to your documentation's ``conf.py`` file:

.. code-block:: python
		
   wegweiser = {
       "app_config": "/path/to/your/pyramid.ini"
   }


.. _documenting:

Adding routes to the documentation
==================================


To document all routes, use the ``pyramidroutes`` directive:

.. code-block:: rst

   .. pyramidroutes::

You can also limit which routes to show using the ``prefix`` option:

.. code-block:: rst

   .. pyramidroutes::
      :prefix: /spam/

If you have a big application, you probably want to group the routes
by module:

.. code-block:: rst

   .. pyramidroutes::
      :groupby: module

If you want to document a single route only (e.g. you want to group
routes by hand), you can use the ``pyramidroute`` directive:

.. code-block:: rst

   .. pyramidroute:: route_name


Full example
============

.. pyramidroutes::
