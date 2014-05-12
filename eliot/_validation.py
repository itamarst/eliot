"""
A log message serialization and validation system for Eliot.

Validation is intended to be done by unit tests, not the production code path,
although in theory it could be done then as well.
"""

from __future__ import unicode_literals

from collections import namedtuple

import six
unicode = six.text_type

from ._message import Message
from ._action import startAction, startTask


class ValidationError(Exception):
    """
    A field value failed validation.
    """


# Types that can be encoded to JSON:
_JSON_TYPES = {type(None), int, float, unicode, list, dict, bytes, bool}
_JSON_TYPES |= set(six.integer_types)

class Field(object):
    """
    A named field that can accept rich types and serialize them to the logging
    system's basic types (currently, JSON types).

    An optional extra validation function can be used to validate inputs when
    unit testing.

    @ivar key: The name of the field, the key which refers to it,
        e.g. C{"path"}.

    @ivar description: A description of what this field contains.
    @type description: C{unicode}
    """
    def __init__(self, key, serializer, description="", extraValidator=None):
        """
        @param serializer: A function that takes a single rich input and
            returns a serialized value that can be written out as JSON. May
            raise L{ValidationError} to indicate bad inputs.

        @param extraValidator: Allow additional validation of the field
            value. A callable that takes a field value, and raises
            L{ValidationError} if the value is a incorrect one for this
            field. Alternatively can be set to C{None}, in which case no
            additional validation is done.
        """
        self.key = key
        self.description = description
        self._serializer = serializer
        self._extraValidator = extraValidator


    def validate(self, input):
        """
        Validate the given input value against this L{Field} definition.

        @param input: An input value supposedly serializable by this L{Field}.

        @raises ValidationError: If the value is not serializable or fails to
            be validated by the additional validator.
        """
        # Make sure the input serializes:
        self._serializer(input)
        # Use extra validator, if given:
        if self._extraValidator is not None:
            self._extraValidator(input)


    def serialize(self, input):
        """
        Convert the given input to a value that can actually be logged.

        @param input: An input value supposedly serializable by this L{Field}.

        @return: A serialized value.
        """
        return self._serializer(input)


    @classmethod
    def forValue(klass, key, value, description):
        """
        Create a L{Field} that can only have a single value.

        @param key: The name of the field, the key which refers to it,
            e.g. C{"path"}.

        @param value: The allowed value for the field.

        @param description: A description of what this field contains.
        @type description: C{unicode}

        @return: A L{Field}.
        """
        def validate(checked):
            if checked != value:
                raise ValidationError(checked,
                                      "Field %r must be %r" % (key, value))
        return klass(key, lambda _: value, description, validate)


    @classmethod
    def forTypes(klass, key, classes, description, extraValidator=None):
        """
        Create a L{Field} that must be an instance of a given set of types.

        @param key: The name of the field, the key which refers to it,
            e.g. C{"path"}.

        @ivar classes: A C{list} of allowed Python classes for this field's
            values. Supported classes are C{unicode}, C{int}, C{float},
            C{bool}, C{long}, C{list} and C{dict} and C{None} (the latter
            isn't strictly a class, but will be converted appropriately).

        @param description: A description of what this field contains.
        @type description: C{unicode}

        @param extraValidator: See description in L{Field.__init__}.

        @return: A L{Field}.
        """
        fixedClasses = []
        for k in classes:
            if k is None:
                k = type(None)
            if k not in _JSON_TYPES:
                raise TypeError("%s is not JSON-encodeable" % (k,))
            fixedClasses.append(k)
        fixedClasses = tuple(fixedClasses)

        def validate(value):
            if not isinstance(value, fixedClasses):
                raise ValidationError(
                    value, "Field %r requires type to be one of %s" %
                    (key, classes))
            if extraValidator is not None:
                extraValidator(value)

        return klass(key, lambda v: v, description, extraValidator=validate)



def fields(**keys):
    """
    Factory for for L{MessageType} and L{ActionType} field definitions.

    @param **keys: A L{dict} mapping key names to the expected type of the
        field's values.

    @return: A L{list} of L{Field} instances.
    """
    return [Field.forTypes(key, [value], "") for key, value in keys.items()]



REASON = Field.forTypes("reason", [unicode], "The reason for an event.")
TRACEBACK = Field.forTypes("traceback", [unicode],
                           "The traceback for an exception.")
EXCEPTION = Field.forTypes("exception", [unicode],
                           "The FQPN of an exception class.")



class _MessageSerializer(object):
    """
    A serializer and validator for messages.

    @ivar fields: A C{dict} mapping a C{unicode} field name to the respective
        L{Field}.
    """
    def __init__(self, fields):
        keys = [field.key for field in fields]
        if len(set(keys)) != len(keys):
            raise ValueError(keys, "Duplicate field name")
        if "action_type" in keys:
            if "message_type" in keys:
                raise ValueError(keys, "Messages must have either "
                                 "'action_type' or 'message_type', not both")
        elif "message_type" not in keys:
            raise ValueError(keys, "Messages must have either 'action_type' ",
                             "or 'message_type'")
        if any(key.startswith("_") for key in keys):
            raise ValueError(keys, "Field names must not start with '_'")
        for reserved in ("task_uuid", "task_level", "timestamp",
                         "action_counter"):
            if reserved in keys:
                raise ValueError(keys, "The field name %r is reserved for use "
                                 "by the logging framework" % (reserved,))
        self.fields = dict((field.key, field) for field in fields)


    def serialize(self, message):
        """
        Serialize the given message in-place, converting inputs to outputs.

        We do this in-place for performance reasons. There are more fields in
        a message than there are L{Field} objects because of the timestamp,
        task_level and task_uuid fields. By only iterating over our L{Fields}
        we therefore reduce the number of function calls in a critical code
        path.

        @param message: A C{dict}.
        """
        for key, field in self.fields.items():
            message[key] = field.serialize(message[key])


    def validate(self, message):
        """
        Validate the given message.

        @param message: A C{dict}.

        @raises ValidationError: If the message has the wrong fields or one of
            its field values fail validation.
        """
        for key, field in self.fields.items():
            if key not in message:
                raise ValidationError(message, "Field %r is missing" % (key,))
            field.validate(message[key])
        fieldSet = set(self.fields) | set(
            ["task_level", "task_uuid", "timestamp", "action_counter"])
        for key in message:
            if key not in fieldSet:
                raise ValidationError(message, "Unexpected field %r" % (key,))


class MessageType(object):
    """
    A specific type of non-action message.

    Example usage:

        # Schema definition:
        KEY = Field("key", [int], u"The lookup key for things.")
        STATUS = Field("status", [int], u"The status of a thing.")
        LOG_STATUS = MessageType(
            "yourapp:subsystem:status", [KEY, STATUS],
            u"We just set the status of something.")

        # Actual code, with logging added:
        def setstatus(key, status):
            doactualset(key, status)
            LOG_STATUS(key=key, status=status).write()

    You do not need to use the L{MessageType} to create the L{eliot.Message},
    however; you could build it up using a series of L{eliot.Message.bind}
    calls. Having a L{MessageType} is nonetheless still useful for validation
    and documentation.

    @ivar message_type: The name of the type,
        e.g. C{"yourapp:subsystem:yourtype"}.

    @ivar description: A description of what this message means.
    @type description: C{unicode}
    """
    def __init__(self, message_type, fields, description=""):
        """
        @ivar type: The name of the type,
            e.g. C{"yourapp:subsystem:yourtype"}.

        @ivar fields: A C{list} of L{Field} instances which can appear in this
            type.

        @param description: A description of what this message means.
        @type description: C{unicode}
        """
        self.message_type = message_type
        self.description = description
        self._serializer = _MessageSerializer(
            fields + [Field.forValue("message_type", message_type,
                                     "The message type.")])


    def __call__(self, **fields):
        """
        Create a new L{eliot.Message} of this type with the given fields.

        @param fields: Extra fields to add to the message.

        @rtype: L{eliot.Message}
        """
        fields["message_type"] = self.message_type
        return Message(fields, self._serializer)




class _ActionSerializers(namedtuple("_ActionSerializers",
                                    ["start", "success", "failure"])):
    """
    Serializers for the three action messages: start, success and failure.
    """



class ActionType(object):
    """
    A specific type of action.

    Example usage:

        # Schema definition:
        KEY = Field("key", [int], u"The lookup key for things.")
        RESULT = Field("result", [str], u"The result of lookups.")
        LOG_DOSOMETHING = ActionType(
            "yourapp:subsystem:youraction",
            [KEY], [RESULT],
            u"Do something with a key, resulting in a value.")

        # Actual code, with logging added:
        def dosomething(key):
            with LOG_DOSOMETHING(logger, key=key) as action:
                _dostuff(key)
                _morestuff(key)
                result = _theresult()
                action.addSuccessFields(result=result)
            return result

    @ivar action_type: The name of the action,
        e.g. C{"yourapp:subsystem:youraction"}.

    @ivar startFields: A C{list} of L{Field} instances which can appear in
        this action's start message.

    @ivar successFields: A C{list} of L{Field} instances which can appear in
        this action's succesful finish message.

    @ivar failureFields: A C{list} of L{Field} instances which can appear in
        this action's failed finish message (in addition to the built-in
        C{"exception"} and C{"reason"} fields).

    @ivar description: A description of what this action's messages mean.
    @type description: C{unicode}
    """
    # Overrideable hook for testing; need staticmethod() so functions don't
    # get turned into methods.
    _startAction = staticmethod(startAction)
    _startTask = staticmethod(startTask)


    def __init__(self, action_type, startFields, successFields, description=""):
        self.action_type = action_type
        self.description = description

        actionTypeField = Field.forValue("action_type", action_type,
                                         "The action type")
        def makeActionStatusField(value):
            return Field.forValue("action_status", value, "The action status")
        startFields = startFields + [
            actionTypeField, makeActionStatusField("started")]
        successFields = successFields + [
            actionTypeField, makeActionStatusField("succeeded")]
        failureFields = [
            actionTypeField, makeActionStatusField("failed"), REASON,
            EXCEPTION]

        self._serializers = _ActionSerializers(_MessageSerializer(startFields),
                                               _MessageSerializer(successFields),
                                               _MessageSerializer(failureFields))


    def __call__(self, logger, **fields):
        """
        Start a new L{eliot.Action} of this type with the given start fields.

        You can use the result as a Python context manager, or use the
        L{eliot.Action.finish} API.

             LOG_DOSOMETHING = ActionType("yourapp:subsystem:dosomething",
                                      [Field.forTypes("entry", [int], "")],
                                      [Field.forTypes("result", [int], "")],
                                      [],
                                      "Do something with an entry.")
             with LOG_DOSOMETHING(logger, entry=x) as action:
                  do(x)
                  result = something(x * 2)
                  action.addSuccessFields(result=result)

        Or perhaps:

             action = LOG_DOSOMETHING(logger, entry=x)
             action.run(doSomething)
             action.finish()

        @param logger: A L{eliot.ILogger} provider to which the action's
            messages will be written.

        @param fields: Extra fields to add to the message.

        @rtype: L{eliot.Action}
        """
        return self._startAction(logger, self.action_type, self._serializers,
                                 **fields)


    def asTask(self, logger, **fields):
        """
        Start a new L{eliot.Action} of this type as a task (i.e. top-level
        action) with the given start fields.

        See L{ActionType.__call__} for example of usage.

        @param logger: A L{eliot.ILogger} provider to which the action's
            messages will be written.

        @param fields: Extra fields to add to the message.

        @rtype: L{eliot.Action}
        """
        return self._startTask(logger, self.action_type, self._serializers,
                               **fields)



__all__ = []
