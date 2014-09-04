Using Eliot
===========

A Note On Naming
----------------

Eliot APIs provide both `PEP 8`_ style (e.g. ``write_traceback()``) and `Twisted`_ (e.g. ``writeTraceback()``) method and function names.
The only exceptions are pyunit-style assertions (e.g. ``assertContainsFields()``) and Twisted-specific APIs since both use camel-case by default.
Code examples below may use either style; both will work.

.. _PEP 8: http://legacy.python.org/dev/peps/pep-0008/
.. _Twisted: https://twistedmatrix.com/documents/current/core/development/policy/coding-standard.html



Unit Testing
------------

Now that you've got some code emitting log messages (or even better, before you've written the code) you can write unit tests to verify it.
Given good test coverage all code branches should already be covered by tests unrelated to logging.
Logging can be considered just another aspect of testing those code branches.
Rather than recreating all those tests as separate functions Eliot provides a decorator the allows adding logging assertions to existing tests.
``unittest.TestCase`` test methods decorated with ``eliot.testing.validate_logging`` will be called with a ``logger`` keyword argument, a ``eliot.MemoryLogger`` instance, which should replace any ``eliot.Logger`` in objects being tested.
The ``validate_logging`` decorator takes an argument: another function that takes the ``TestCase`` instance as its first argument (``self``), and the ``logger`` as its second argument.
This function can make assertions about logging after the main test function has run.
You can also pass additional arguments and keyword arguments to ``@validate_logging``, in which case the assertion function will get called with them as well.

Let's unit test some code that relies on the ``LOG_USER_REGISTRATION`` object we created earlier.


.. code-block:: python

      from eliot import Logger
      from myapp.logtypes import LOG_USER_REGISTRATION

      class UserRegistration(object):
          logger = Logger()

          def __init__(self):
              self.db = {}

          def register(self, username, password, age):
              self.db[username] = (password, age)
              LOG_USER_REGISTRATION(
                   username=username, password=password, age=age).write(self.logger)


Here's how we'd test it:

.. code-block:: python

    from unittest import TestCase
    from eliot import MemoryLogger
    from eliot.testing import assertContainsFields, validate_logging

    from myapp.registration import UserRegistration
    from myapp.logtypes import LOG_USER_REGISTRATION


    class LoggingTests(TestCase):
        def assertRegistrationLogging(self, logger):
            """
            Logging assertions for test_registration.
            """
            self.assertEqual(len(logger.messages), 1)
            msg = logger.messages[0]
            assertContainsFields(self, msg,
                                 {u"username": u"john",
                                  u"password": u"password",
                                  u"age": 12}))

        @validate_logging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.logger = logger
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Besides calling an the given validation function the ``@validate_logging`` decorator will also validate the logged messages after the test is done.
E.g. it will make sure they are JSON encodable.
Messages were created using ``ActionType`` and ``MessageType`` will be validated using the applicable ``Field`` definitions.
You can also call ``MemoryLogger.validate`` yourself to validate written messages.
If you don't want any additional logging assertions you can decorate your test function using ``@validate_logging(None)``.


Testing Tracebacks
^^^^^^^^^^^^^^^^^^

Tests decorated with ``@validate_logging`` will fail if there are any tracebacks logged to the given ``MemoryLogger`` (using ``write_traceback`` or ``writeFailure``) on the theory that these are unexpected errors indicating a bug.
If you expected a particular exception to be logged you can call ``MemoryLogger.flush_tracebacks``, after which it will no longer cause a test failure.
The result will be a list of traceback message dictionaries for the particular exception.

.. code-block:: python

    from unittest import TestCase
    from eliot.testing import validate_logging

    class MyTests(TestCase):
        def assertMythingBadPathLogging(self, logger):
            messages = logger.flush_tracebacks(OSError)
            self.assertEqual(len(messages), 1)

        @validate_logging(assertMythingBadPathLogging)
        def test_mythingBadPath(self, logger):
             mything = MyThing()
             mything.logger = logger
             # Trigger an error that will cause a OSError traceback to be logged:
             self.assertFalse(mything.load("/nonexistent/path"))



Testing Message and Action Structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Eliot provides utilities for making assertions about the structure of individual messages and actions.
The simplest method is using the ``assertHasMessage`` utility function which asserts that a message of a given ``MessageType`` has the given fields:

.. code-block:: python

    from eliot.testing import assertHasMessage, validate_logging

    class LoggingTests(TestCase):
        @validate_logging(assertHasMessage, LOG_USER_REGISTRATION,
                         {u"username": u"john",
                          u"password": u"password",
                          u"age": 12})
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.logger = logger
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


``assertHasMessage`` returns the found message and can therefore be used within more complex assertions. ``assertHasAction`` provides similar functionality for actions (see example below).

More generally, ``eliot.testing.LoggedAction`` and ``eliot.testing.LoggedMessage`` are utility classes to aid such testing.
``LoggedMessage.of_type`` lets you find all messages of a specific ``MessageType``.
A ``LoggedMessage`` has an attribute ``message`` which contains the logged message dictionary.
For example, we could rewrite the registration logging test above like so:

.. code-block:: python

    from eliot.testing import LoggedMessage, validate_logging

    class LoggingTests(TestCase):
        def assertRegistrationLogging(self, logger):
            """
            Logging assertions for test_registration.
            """
            logged = LoggedMessage.of_type(logger.messages, LOG_USER_REGISTRATION)[0]
            assertContainsFields(self, logged.message,
                                 {u"username": u"john",
                                  u"password": u"password",
                                  u"age": 12}))

        @validate_logging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.logger = logger
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Similarly, ``LoggedAction.of_type`` finds all logged actions of a specific ``ActionType``.
A ``LoggedAction`` instance has ``start_message`` and ``end_message`` containing the respective message dictionaries, and a ``children`` attribute containing a list of child ``LoggedAction`` and ``LoggedMessage``.
That is, a ``LoggedAction`` knows about the messages logged within its context.
``LoggedAction`` also has a utility method ``descendants()`` that returns an iterable of all its descendants.
We can thus assert that a particular message (or action) was logged within the context of another action.

For example, let's say we have some code like this:

.. code-block:: python

    LOG_SEARCH = ActionType(...)
    LOG_CHECK = MessageType(...)

    class Search:
        logger = Logger()

        def search(self, servers, database, key):
            with LOG_SEARCH(self.logger, database=database, key=key):
            for server in servers:
                LOG_CHECK(server=server).write(self.logger)
                if server.check(database, key):
                    return True
            return False

We want to assert that the LOG_CHECK message was written in the context of the LOG_SEARCH action.
The test would look like this:

.. code-block:: python

    from eliot.testing import LoggedAction, LoggedMessage, validate_logging
    import searcher

    class LoggingTests(TestCase):
        @validate_logging(None)
        def test_logging(self, logger):
            searcher = Search()
            searcher.logger = logger
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = LoggedAction.of_type(logger.messages, searcher.LOG_SEARCH)[0]
            messages = LoggedMessage.of_type(logger.messages, searcher.LOG_CHECK)
            # The action start message had the appropriate fields:
            assertContainsFields(self, action.start_message,
                                 {"database": "users", "key": "theuser"})
            # Messages were logged in the context of the action
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])


Or we can simplify further by using ``assertHasMessage`` and ``assertHasAction``:

.. code-block:: python

    from eliot.testing import LoggedAction, LoggedMessage, validate_logging
    import searcher

    class LoggingTests(TestCase):
        @validate_logging(None)
        def test_logging(self, logger):
            searcher = Search()
            searcher.logger = logger
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = assertHasAction(self, logger, searcher.LOG_SEARCH, succeeded=True,
                                     startFields={"database": "users",
                                                  "key": "theuser"})

            # Messages were logged in the context of the action
            messages = LoggedMessage.of_type(logger.messages, searcher.LOG_CHECK)
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])
