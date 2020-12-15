Unit Testing Your Logging
=========================

Now that you've got some code emitting log messages (or even better, before you've written the code) you can write unit tests to verify it.
Given good test coverage all code branches should already be covered by tests unrelated to logging.
Logging can be considered just another aspect of testing those code branches.

Rather than recreating all those tests as separate functions Eliot provides a decorator the allows adding logging assertions to existing tests.


Linting your logs
-----------------

Decorating a test function with ``eliot.testing.capture_logging`` validation will ensure that:

1. You haven't logged anything that isn't JSON serializable.
2. There are no unexpected tracebacks, indicating a bug somewhere in your code.

.. code-block:: python

   from eliot.testing import capture_logging

   class MyTest(unittest.TestCase):
      @capture_logging(None)
      def test_mytest(self, logger):
          call_my_function()


Making assertions about the logs
--------------------------------

You can also ensure the correct messages were logged.

.. code-block:: python

      from eliot import log_message

      class UserRegistration(object):

          def __init__(self):
              self.db = {}

          def register(self, username, password, age):
              self.db[username] = (password, age)
              log_message(message_type="user_registration",
                          username=username, password=password,
                          age=age)


Here's how we'd test it:

.. code-block:: python

    from unittest import TestCase
    from eliot import MemoryLogger
    from eliot.testing import assertContainsFields, capture_logging

    from myapp.registration import UserRegistration


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

        @capture_logging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Testing Tracebacks
------------------

Tests decorated with ``@capture_logging`` will fail if there are any tracebacks logged (using ``write_traceback`` or ``writeFailure``) on the theory that these are unexpected errors indicating a bug.
If you expected a particular traceback to be logged you can call ``MemoryLogger.flush_tracebacks``, after which it will no longer cause a test failure.
The result will be a list of traceback message dictionaries for the particular exception.

.. code-block:: python

    from unittest import TestCase
    from eliot.testing import capture_logging

    class MyTests(TestCase):
        def assertMythingBadPathLogging(self, logger):
            messages = logger.flush_tracebacks(OSError)
            self.assertEqual(len(messages), 1)

        @capture_logging(assertMythingBadPathLogging)
        def test_mythingBadPath(self, logger):
             mything = MyThing()
             # Trigger an error that will cause a OSError traceback to be logged:
             self.assertFalse(mything.load("/nonexistent/path"))



Testing Message and Action Structure
------------------------------------

Eliot provides utilities for making assertions about the structure of individual messages and actions.
The simplest method is using the ``assertHasMessage`` utility function which asserts that a message of a given message type has the given fields:

.. code-block:: python

    from eliot.testing import assertHasMessage, capture_logging

    class LoggingTests(TestCase):
        @capture_logging(assertHasMessage, "user_registration",
                         {u"username": u"john",
                          u"password": u"password",
                          u"age": 12})
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


``assertHasMessage`` returns the found message and can therefore be used within more complex assertions. ``assertHasAction`` provides similar functionality for actions (see example below).

More generally, ``eliot.testing.LoggedAction`` and ``eliot.testing.LoggedMessage`` are utility classes to aid such testing.
``LoggedMessage.of_type`` lets you find all messages of a specific message type.
A ``LoggedMessage`` has an attribute ``message`` which contains the logged message dictionary.
For example, we could rewrite the registration logging test above like so:

.. code-block:: python

    from eliot.testing import LoggedMessage, capture_logging

    class LoggingTests(TestCase):
        def assertRegistrationLogging(self, logger):
            """
            Logging assertions for test_registration.
            """
            logged = LoggedMessage.of_type(logger.messages, "user_registration")[0]
            assertContainsFields(self, logged.message,
                                 {u"username": u"john",
                                  u"password": u"password",
                                  u"age": 12}))

        @capture_logging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Similarly, ``LoggedAction.of_type`` finds all logged actions of a specific action type.
A ``LoggedAction`` instance has ``start_message`` and ``end_message`` containing the respective message dictionaries, and a ``children`` attribute containing a list of child ``LoggedAction`` and ``LoggedMessage``.
That is, a ``LoggedAction`` knows about the messages logged within its context.
``LoggedAction`` also has a utility method ``descendants()`` that returns an iterable of all its descendants.
We can thus assert that a particular message (or action) was logged within the context of another action.

For example, let's say we have some code like this:

.. code-block:: python

    from eliot import start_action, Message

    class Search:
        def search(self, servers, database, key):
            with start_action(action_type="log_search", database=database, key=key):
            for server in servers:
                Message.log(message_type="log_check", server=server)
                if server.check(database, key):
                    return True
            return False

We want to assert that the "log_check" message was written in the context of the "log_search" action.
The test would look like this:

.. code-block:: python

    from eliot.testing import LoggedAction, LoggedMessage, capture_logging
    import searcher

    class LoggingTests(TestCase):
        @capture_logging(None)
        def test_logging(self, logger):
            searcher = Search()
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = LoggedAction.of_type(logger.messages, "log_search")[0]
            messages = LoggedMessage.of_type(logger.messages, "log_check")
            # The action start message had the appropriate fields:
            assertContainsFields(self, action.start_message,
                                 {"database": "users", "key": "theuser"})
            # Messages were logged in the context of the action
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])


Or we can simplify further by using ``assertHasMessage`` and ``assertHasAction``:

.. code-block:: python

    from eliot.testing import LoggedAction, LoggedMessage, capture_logging
    import searcher

    class LoggingTests(TestCase):
        @capture_logging(None)
        def test_logging(self, logger):
            searcher = Search()
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = assertHasAction(self, logger, "log_search", succeeded=True,
                                     startFields={"database": "users",
                                                  "key": "theuser"})

            # Messages were logged in the context of the action
            messages = LoggedMessage.of_type(logger.messages, "log_check")
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])


Custom JSON encoding
--------------------

Just like a ``FileDestination`` can have a custom JSON encoder, so can your tests, so you can validate your messages with that JSON encoder:

.. code-block:: python

   from unittest import TestCase
   from eliot.json import EliotJSONEncoder
   from eliot.testing import capture_logging

   class MyClass:
       def __init__(self, x):
           self.x = x

   class MyEncoder(EliotJSONEncoder):
       def default(self, obj):
           if isinstance(obj, MyClass):
               return {"x": obj.x}
           return EliotJSONEncoder.default(self, obj)

   class LoggingTests(TestCase):
       @capture_logging(None, encoder_=MyEncoder)
       def test_logging(self, logger):
           # Logged messages will be validated using MyEncoder....
           ...

Notice that the hyphen after `encoder_` is deliberate: by default keyword arguments are passed to the assertion function (the first argument to ``@capture_logging``) so it's marked this way to indicate it's part of Eliot's API.

Custom testing setup
--------------------

In some cases ``@capture_logging`` may not do what you want.
You can achieve the same effect, but with more control, with some lower-level APIs:

.. code-block:: python

   from eliot import MemoryLogger
   from eliot.testing import swap_logger, check_for_errors

   def custom_capture_logging():
       # Replace default logging setup with a testing logger:
       test_logger = MemoryLogger()
       original_logger = swap_logger(test_logger)

       try:
           run_some_code()
       finally:
           # Restore original logging setup:
           swap_logger(original_logger)
           # Validate log messages, check for tracebacks:
           check_for_errors(test_logger)
           
