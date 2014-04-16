Using Eliot
===========

Introduction
------------

The APIs you typically want to use are ``MessageType`` and ``ActionType``.
Here's an example demonstrating how we create a message type, bind some values and then log the message:

.. code-block:: python

    from eliot import Field, MessageType, Logger

    class Coordinate(object):
        def __init__(self, x, y):
            self.x = self.x
            self.y = self.y


    # This field takes a complex type that will be stored in a single Field,
    # so we pass in a serializer function that converts it to a list with two
    # ints:
    _LOCATION = Field(u"location", lambda loc: [loc.x, loc.y], u"The location.")
    # These fields are just basic supported types, in this case int and unicode
    # respectively:
    _COUNT = Field.forTypes(u"count", [int], u"The number of items to deliver.")
    _NAME = Field.forTypes(u"name", [unicode], u"The name of the delivery person.")

    # This is a type definition for a message. It is used to hook up
    # serialization of field values, and for message validation in unit tests:
    LOG_DELIVERY_SCHEDULED = MessageType(
        u"pizzadelivery:schedule",
        [_LOCATION, _COUNT, _NAME],
        u"A pizza delivery has been scheduled.")


    logger = Logger()

    def deliverPizzas(deliveries):
        person = getFreeDeliveryPerson()
        # Create a base message with some, but not all, of the fields filled in:
        baseMessage = LOG_DELIVERY_SCHEDULED(name=person.name)
        for location, count in deliveries:
            deliveryDatabase.insert(person, location, count)
            # Bind additional message fields and then log the resulting message:
            message = baseMessage.bind(count=count, location=location)
            message.write(logger)


Before you can understand this in detail we need to go over lower-level APIs.


Messages and Loggers
--------------------

At its base, Eliot outputs structured messages composed of named fields.
Eliot messages are typically serialized to JSON objects.
Fields therefore can have Unicode names, so either ``unicode`` or ``bytes`` containing UTF-8 encoded Unicode.
Message values must be supported by JSON: ``int``, ``float``, ``None``, ``unicode``, UTF-8 encoded Unicode as ``bytes``, ``dict`` or ``list``.
The latter two can only be composed of other supported types.

A ``Message`` is written to a ``Logger``, whose purpose is to create scope for unit tests to validate only specific messages.
Typically you will create a ``Logger`` per top-level class you are testing.

.. code-block:: python

    from eliot import Message, Logger

    class YourClass(object):
        logger = Logger()

        def run(self):
            # Create a message with two fields, "key" and "value":
            msg = Message.new(key=123, value=u"hello")
            # Write the message:
            msg.write(self.logger)

You can also create a new ``Message`` from an existing one by binding new values.
New values will override ones on the base ``Message``, but ``bind()`` does not mutate the original ``Message``.

.. code-block:: python

      # This message has fields key=123, value=u"hello"
      msg = Message.new(key=123, value=u"hello")
      # And this one has fields key=123, value=u"other", extra=456
      msg2 = msg.bind(value=u"other", extra=456)

You can also log tracebacks when your code hits an unexpected exception:

.. code-block:: python

    from eliot import Logger, writeTraceback

    class YourClass(object):
        logger = Logger()

        def run(self):
            try:
                 dosomething()
            except:
                 writeTraceback(self.logger, u"yourapp:yourclass")

When using Twisted you would do:

.. code-block:: python

    from eliot import Logger, writeFailure

    class YourClass(object):
        logger = Logger()

        def run(self):
            d = dosomething()
            d.addErrback(writeFailure, self.logger, u"yourapp:yourclass")


The final argument in both cases is the "system".
This should be a Unicode string, a logical description of what subsystem in your application generated the message.
Colons are used as namespace separators by convention to discourage the use of Python modules and namespaces.
System strings should involve code structure rather than file structure.
This means they will not have to change if you decide to refactor your implementation.


Destinations
------------

Destinations are how messages get written out by the ``Logger`` class.
A destination is a callable that takes a message dictionary.
For example, if we want to write out a JSON message per line we can do:

.. code-block:: python

    import json
    from eliot import addDestination

    def stdout(message):
        sys.stdout.write(json.dumps(message) + b"\n")
    addDestination(stdout)

For Twisted users ``eliot.logwriter.ThreadedFileWriter`` is a logging destination that writes to a file-like object in a thread.


Actions and Tasks
-----------------

A higher-level construct than messages is the concept of an action.
An action can be started, and then finishes either successfully or with some sort of an exception.
Success in this case simply means no exception was thrown; the result of an action may be a successful response saying "this did not work".
Log messages are emitted for action start and finish.

Actions are also nested; one action can be the parent of another.
A top-level action with no parent is called a task.
An action's parent is deduced from the Python call stack.
Log messages will also note the action they are part of if they can deduce it from the call stack.
The result of all this is that you can trace the operation of your code as it logs various actions, and see a narrative of what happened and what caused it to happen.


Synchronous Code
^^^^^^^^^^^^^^^^

Here's a basic example of logging an action:

.. code-block:: python

     from eliot import startAction, Logger

     logger = Logger()

     with startAction(logger, u"yourapp:subsystem:frob"):
         x = _beep()
         frobinate(x)

This will log an action start message and if the block finishes successfully an action success message.
If an exception is thrown by the block then an action failure message will be logged along with the exception type and reason as additional fields.
Each action thus results in two messages being logged: at the start and finish of the action.
No traceback will be logged so if you want a traceback you will need to do so explicitly.
Notice that the action has a name, with a subsystem prefix.
Again, this should be a logical name.

Note that all code called within this block is within the context of this action.
While running the block of code within the ``with`` statement new actions created with ``startAction`` will get the top-level ``startAction`` as their parent.
If there is no parent the action will be considered a task.
If you want to ignore the context and create a top-level task you can use the ``eliot.startTask`` API.

You can add fields to both the start message and the success/failure messages.

.. code-block:: python

     from eliot import startAction, Logger

     logger = Logger()

     with startAction(logger, u"yourapp:subsystem:frob",
                      # Fields added to start message only:
                      key=123, foo=u"bar") as action:
         x = _beep(123)
         try:
              result = frobinate(x)
              # Fields added to success message only:
              action.addSuccessFields(result=result)
         except KeyError, e:
              # Fields added to failure message only:
              action.addFailureFields(x=x)


Twisted
^^^^^^^

If you are using Twisted an additional set of APIs is available.
First, since code running in an event loop may not all be in same call stack you can explicitly run a function within the action context.

.. code-block:: python

     from eliot import startAction, Logger

     logger = Logger()

     action = startAction(logger, u"yourapp:subsystem:frob")
     # Call doSomething(x=1) in context of action, return its result:
     result = action.run(doSomething, x=1)

A variant also exists for ``Deferred`` callbacks, which just has slightly different argument order:

.. code-block:: python

     from eliot import startAction, Logger

     logger = Logger()

     action = startAction(logger, u"yourapp:subsystem:frob")
     d = Deferred()
     # Call doSomething(deferredResult, x=1) in context of action, return its
     # result:
     d.addCallback(action.runCallback, gotResult, x=1)

Second, you can tell the action that it will finish when a ``Deferred`` fires:

     from eliot import startAction, Logger

     logger = Logger()

     action = startAction(logger, u"yourapp:subsystem:frob")
     d = action.run(doSomething, x=1)
     d.addCallback(action.runCallback, gotResult)
     # When Deferred has result at this point, the action is considered finished:
     action.finishAfter(d)

As you would expect, if the ``Deferred`` fires with a regular result that will result in success message.
If the ``Deferred`` fires with an errback that will result in failure message.


Type System
-----------

So far we've been creating messages and actions in an unstructured manner.
This means it's harder to support types that aren't built-in and to validate message structure.
There's no documentation of what fields messages and action messages expect.
To improve this we introduce the preferred API for creating actions and standalone messages: ``ActionType`` and ``MessageType``.

A ``Field`` instance is used to validate fields of messages, and to serialize rich types to the built-in supported types.
It is created with the name of the field, a a serialization function that converts the input to an output and a description.
The serialization function must return a result that is JSON-encodable.
You can also pass in an extra validation function.
If you pass this function in it will be called with values that are being validated; if it raises ``eliot.ValidationError`` that value will fail validation.

A couple of utility functions allow creating specific types of ``Field`` instances.
``Field.forValue`` returns a ``Field`` that only can have a single value.
More generally useful, ``Field.forTypes`` returns a ``Field`` that can only be one of certain specific types: some subset of ``unicode``, ``bytes``, ``int``, ``float``, ``bool``, ``list`` and ``dict`` as well as ``None`` which technically isn't a class.
As always, ``bytes`` must only contain UTF-8 encoded Unicode.

.. code-block:: python

    from eliot import Field

    def userToUsername(user):
        """
        Extract username from a User object.
        """
        return user.username

    USERNAME = Field(u"username", userToUsername, u"The name of the user.")

    # Validation is useful for unit tests and catching bugs; it's not used in
    # the actual logging code path. We therefore don't bother catching things
    # we'd do in e.g. web form validation.
    def _validateAge(value):
        if value is not None and value < 0:
             raise ValidationError("Field 'age' must be positive:", value)
    AGE = Field.forTypes(u"age", [int, None],
                         u"The age of the user, might be None if unknown",
                         _validateAge)


MessageType
^^^^^^^^^^^

Now that you have some fields you can create a custom ``MessageType``.
This takes a message name which will be put in the ``message_type`` field of resulting messages.
It also takes a list of ``Field`` instances and a description.

.. code-block:: python

    from eliot import MessageType

    LOG_USER_REGISTRATION = MessageType(u"yourapp:authentication:registration",
                                        [USERNAME, AGE],
                                        u"We've just registered a new user.")

Given a ``MessageType`` you can create a ``Message`` instance with the ``message_type`` field pre-populated.
You can then use it the way you would normally use ``Message``, e.g. ``bind()`` or ``write()``.

.. code-block:: python

    msg = LOG_USER_REGISTRATION(username=user, age=193)
    msg.write(logger)

A ``Message`` created from a ``MessageType`` will automatically use the ``MessageType`` ``Field`` instances to serialize its fields.

Keep in mind that no validation is done when messages are created.
Instead, validation is intended to be done in your unit tests.
If you're not unit testing all your log messages you're doing it wrong.
Luckily, Eliot makes it pretty easy to test logging as we'll see in a bit.


ActionType
^^^^^^^^^^

Similarly to ``MessageType`` you can also create types for actions.
Unlike a ``MessageType`` you need three sets of fields: one for actions start, one for success and one for failure.

.. code-block:: python

    from eliot import ActionType, Field, Logger

    LOG_USER_SIGNIN = ActionType(u"yourapp:authentication:signin",
                                 # Start message fields:
                                 [USERNAME],
                                 # Success message fields:
                                 [Field.forTypes(u"status", [int], u"Status code for the user")],
                                 # Failure message fields in addition to built-in ones:
                                 [],
                                 u"A user is attempting to sign in.")

Calling the resulting instance is equivalent to ``startAction``.
For ``startTask`` you can call ``LOG_USER_SIGNIN.asTask``.

.. code-block:: python

    logger = Logger()

    def signin(user, password):
         with LOG_USER_SIGNIN(logger, username=user) as action:
             status = user.authenticate(password)
             action.addSuccessFields(status=status)
         return status

Again, as with ``MessageType``, field values will be serialized using the ``Field`` definitions in the ``ActionType``.


Unit Testing
------------

Now that you've got some code emitting log messages (or even better, before you've written the code) you can write unit tests to verify it.
Given good test coverage all code branches should already be covered by tests unrelated to logging.
Logging can be considered just another aspect of testing those code branches.
Rather than recreating all those tests as separate functions Eliot provides a decorator the allows adding logging assertions to existing tests.
``unittest.TestCase`` test methods decorated with ``eliot.testing.validateLogging`` will be called with a ``logger`` keyword argument, a ``eliot.MemoryLogger`` instance, which should replace any ``eliot.Logger` in objects being tested.
The ``validateLogging`` decorator takes an argument: another function that takes the ``TestCase`` instance as its first argument (``self``), and the ``logger`` as its second argument.
This function can make assertions about logging after the main test function has run.
You can also pass additional arguments and keyword arguments to ``@validateLogging``, in which case the assertion function will get called with them as well.

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
    from eliot.testing import assertContainsFields, validateLogging

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

        @validateLogging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.logger = logger
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Besides calling an the given validation function the ``@validateLogging`` decorator will also validate the logged messages after the test is done.
E.g. it will make sure they are JSON encodable.
Messages were created using ``ActionType`` and ``MessageType`` will be validated using the applicable ``Field`` definitions.
You can also call ``MemoryLogger.validate`` yourself to validate written messages.
If you don't want any additional logging assertions you can decorate your test function using ``@validateLogging(None)``.


Testing Tracebacks
^^^^^^^^^^^^^^^^^^

Tests decorated with ``@validateLogging`` will fail if there are any tracebacks logged to the given ``MemoryLogger`` (using ``writeTraceback`` or ``writeFailure``) on the theory that these are unexpected errors indicating a bug.
If you expected a particular exception to be logged you can call ``MemoryLogger.flushTracebacks``, after which it will no longer cause a test failure.
The result will be a list of traceback message dictionaries for the particular exception.

.. code-block:: python

    from unittest import TestCase
    from eliot.testing import validateLogging

    class MyTests(TestCase):
        def assertMythingBadPathLogging(self, logger):
            messages = logger.flushTracebacks(OSError)
            self.assertEqual(len(messages), 1)

        @validateLogging(assertMythingLogging)
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

    from eliot.testing import assertHasMessage, validateLogging

    class LoggingTests(TestCase):
        @validateLogging(assertHasMessage, LOG_USER_REGISTRATION,
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
``LoggedMessage.ofType`` lets you find all messages of a specific ``MessageType``.
A ``LoggedMessage`` has an attribute ``message`` which contains the logged message dictionary.
For example, we could rewrite the registration logging test above like so:

.. code-block:: python

    from eliot.testing import LoggedMessage, validateLogging

    class LoggingTests(TestCase):
        def assertRegistrationLogging(self, logger):
            """
            Logging assertions for test_registration.
            """
            logged = LoggedMessage.ofType(logger.messages, LOG_USER_REGISTRATION)[0]
            assertContainsFields(self, logged.message,
                                 {u"username": u"john",
                                  u"password": u"password",
                                  u"age": 12}))

        @validateLogging(assertRegistrationLogging)
        def test_registration(self, logger):
            """
            Registration adds entries to the in-memory database.
            """
            registry = UserRegistration()
            registry.logger = logger
            registry.register(u"john", u"password", 12)
            self.assertEqual(registry.db[u"john"], (u"passsword", 12))


Similarly, ``LoggedAction.ofType`` finds all logged actions of a specific ``ActionType``.
A ``LoggedAction`` instance has ``startMessage`` and ``endMessage`` containing the respective message dictionaries, and a ``children`` attribute containing a list of child ``LoggedAction`` and ``LoggedMessage``.
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

    from eliot.testing import LoggedAction, LoggedMessage, validateLogging
    import searcher

    class LoggingTests(TestCase):
        @validateLogging(None)
        def test_logging(self, logger):
            searcher = Search()
            searcher.logger = logger
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = LoggedAction.ofType(logger.messages, searcher.LOG_SEARCH)[0]
            messages = LoggedMessage.ofType(logger.messages, searcher.LOG_CHECK)
            # The action start message had the appropriate fields:
            assertContainsFields(self, action.startMessage,
                                 {"database": "users", "key": "theuser"})
            # Messages were logged in the context of the action
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])


Or we can simplify further by using ``assertHasMessage`` and ``assertHasAction``:

.. code-block:: python

    from eliot.testing import LoggedAction, LoggedMessage, validateLogging
    import searcher

    class LoggingTests(TestCase):
        @validateLogging(None)
        def test_logging(self, logger):
            searcher = Search()
            searcher.logger = logger
            servers = [buildServer(), buildServer()]

            searcher.search(servers, "users", "theuser")
            action = assertHasAction(self, logger, searcher.LOG_SEARCH, succeeded=True,
                                     startFields={"database": "users",
                                                  "key": "theuser"})

            # Messages were logged in the context of the action
            messages = LoggedMessage.ofType(logger.messages, searcher.LOG_CHECK)
            self.assertEqual(action.children, messages)
            # Each message had the respective server set.
            self.assertEqual(servers, [msg.message["server"] for msg in messages])


Serialization Errors
--------------------

While validation only happens in ``MemoryLogger.validate`` (either manually or when run by ``@validateLogging``), serialization must run in the normal logging code path.
Eliot tries to very hard never to raise exceptions from the log writing code path so as not to prevent actual code from running.
If a message fails to serialize then a ``eliot:traceback`` message will be logged, along with a ``eliot:serialization_failure`` message with an attempt at showing the message that failed to serialize.

    {"exception": "exceptions.ValueError", "timestamp": "2013-11-22T14:16:51.386745Z", "traceback": "Traceback (most recent call last):\n  File \"/home/itamarst/Customers/HybridLogic/HybridCluster/src/eliot/_output.py\", line 114, in write\n  File \"/home/itamarst/Customers/HybridLogic/HybridCluster/src/eliot/_validation.py\", line 197, in serialize\n  File \"/home/itamarst/Customers/HybridLogic/HybridCluster/src/eliot/_validation.py\", line 83, in serialize\nValueError: invalid literal for int() with base 10: 'hello'\n", "system": "eliot:output", "reason": "invalid literal for int() with base 10: 'hello'", "message_type": "eliot:traceback"}
    {"timestamp": "2013-11-22T14:16:51.386827Z", "message": "{u\"u'message_type'\": u\"'test'\", u\"u'field'\": u\"'hello'\", u\"u'timestamp'\": u\"'2013-11-22T14:16:51.386634Z'\"}", "message_type": "eliot:serialization_failure"}
