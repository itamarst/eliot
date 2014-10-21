Using Types to Structure Messages and Actions
=============================================

Why Typing?
-----------

So far we've been creating messages and actions in an unstructured manner.
This means it's harder to support Python objects that aren't built-in and to validate message structure.
Moreover there's no documentation of what fields messages and action messages expect.
To improve this we introduce the preferred API for creating actions and standalone messages: ``ActionType`` and ``MessageType``.
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
    _COUNT = Field.for_types(u"count", [int], u"The number of items to deliver.")
    _NAME = Field.for_types(u"name", [unicode], u"The name of the delivery person.")

    # This is a type definition for a message. It is used to hook up
    # serialization of field values, and for message validation in unit tests:
    LOG_DELIVERY_SCHEDULED = MessageType(
        u"pizzadelivery:schedule",
        [_LOCATION, _COUNT, _NAME],
        u"A pizza delivery has been scheduled.")


    logger = Logger()

    def deliver_pizzas(deliveries):
        person = get_free_delivery_person()
        # Create a base message with some, but not all, of the fields filled in:
        base_message = LOG_DELIVERY_SCHEDULED(name=person.name)
        for location, count in deliveries:
            delivery_database.insert(person, location, count)
            # Bind additional message fields and then log the resulting message:
            message = base_message.bind(count=count, location=location)
            message.write(logger)

Fields
------

A ``Field`` instance is used to validate fields of messages, and to serialize rich types to the built-in supported types.
It is created with the name of the field, a a serialization function that converts the input to an output and a description.
The serialization function must return a result that is JSON-encodable.
You can also pass in an extra validation function.
If you pass this function in it will be called with values that are being validated; if it raises ``eliot.ValidationError`` that value will fail validation.

A couple of utility functions allow creating specific types of ``Field`` instances.
``Field.for_value`` returns a ``Field`` that only can have a single value.
More generally useful, ``Field.for_types`` returns a ``Field`` that can only be one of certain specific types: some subset of ``unicode``, ``bytes``, ``int``, ``float``, ``bool``, ``list`` and ``dict`` as well as ``None`` which technically isn't a class.
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
    AGE = Field.for_types(u"age", [int, None],
                         u"The age of the user, might be None if unknown",
                         _validateAge)


Message Types
-------------

Now that you have some fields you can create a custom ``MessageType``.
This takes a message name which will be put in the ``message_type`` field of resulting messages.
It also takes a list of ``Field`` instances and a description.

.. code-block:: python

    from eliot import MessageType, Field
    USERNAME = Field.for_types("username", [str])
    AGE = Field.for_types("age", [int])

    LOG_USER_REGISTRATION = MessageType(u"yourapp:authentication:registration",
                                        [USERNAME, AGE],
                                        u"We've just registered a new user.")

Since this syntax is rather verbose a utility function called ``fields`` is provided which creates a ``list`` of ``Field`` instances for you, with support to specifying the types of the fields.
The equivalent to the code above is:

.. code-block:: python

    from eliot import MessageType, fields

    LOG_USER_REGISTRATION = MessageType(u"yourapp:authentication:registration",
                                        fields(username=str, age=int))

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


Action Types
------------

Similarly to ``MessageType`` you can also create types for actions.
Unlike a ``MessageType`` you need two sets of fields: one for action start, one for success.

.. code-block:: python

    from eliot import ActionType, fields, Logger

    LOG_USER_SIGNIN = ActionType(u"yourapp:authentication:signin",
                                 # Start message fields:
                                 fields(username=str),
                                 # Success message fields:
                                 fields(status=int),
                                 # Description:
                                 u"A user is attempting to sign in.")

Calling the resulting instance is equivalent to ``start_action``.
For ``start_task`` you can call ``LOG_USER_SIGNIN.as_task``.

.. code-block:: python

    logger = Logger()

    def signin(user, password):
         with LOG_USER_SIGNIN(logger, username=user) as action:
             status = user.authenticate(password)
             action.add_success_fields(status=status)
         return status

Again, as with ``MessageType``, field values will be serialized using the ``Field`` definitions in the ``ActionType``.


Serialization Errors
--------------------

While validation of field values typically only happens when unit testing, serialization must run in the normal logging code path.
Eliot tries to very hard never to raise exceptions from the log writing code path so as not to prevent actual code from running.
If a message fails to serialize then a ``eliot:traceback`` message will be logged, along with a ``eliot:serialization_failure`` message with an attempt at showing the message that failed to serialize.

.. code-block:: json

    {"exception": "exceptions.ValueError",
     "timestamp": "2013-11-22T14:16:51.386745Z",
     "traceback": "Traceback (most recent call last):\n  ... ValueError: invalid literal for int() with base 10: 'hello'\n",
     "system": "eliot:output",
     "reason": "invalid literal for int() with base 10: 'hello'",
     "message_type": "eliot:traceback"}
    {"timestamp": "2013-11-22T14:16:51.386827Z",
     "message": "{u\"u'message_type'\": u\"'test'\", u\"u'field'\": u\"'hello'\", u\"u'timestamp'\": u\"'2013-11-22T14:16:51.386634Z'\"}",
     "message_type": "eliot:serialization_failure"}
