Typed Messages and Actions
==========================

Introduction
------------

As an additional layer on top of basic messages and actions Eliot also provides a way to defined types using the ``MessageType`` and ``ActionType`` classes.
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

