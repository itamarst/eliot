"""
Tests for L{eliot._validation}.
"""

from __future__ import unicode_literals

from unittest import TestCase

from .._validation import (
    Field, MessageType, ActionType, ValidationError,
    _MessageSerializer,
    )
from .._action import startAction, startTask
from .._output import MemoryLogger
from ..serializers import identity


class TypedFieldTests(TestCase):
    """
    Tests for L{Field.forTypes}.
    """
    def test_validateCorrectType(self):
        """
        L{Field.validate} will not raise an exception if the given value is in
        the list of supported classes.
        """
        field = Field.forTypes("path", [unicode, int], u"A path!")
        field.validate(123)
        field.validate("hello")


    def test_validateNone(self):
        """
        When given a "class" of C{None}, L{Field.validate} will support
        validating C{None}.
        """
        field = Field.forTypes("None", [None], u"Nothing!")
        field.validate(None)


    def test_validateWrongType(self):
        """
        L{Field.validate} will raise a L{ValidationError} exception if the
        given value's type is not in the list of supported classes.
        """
        field = Field.forTypes("key", [int], u"An integer key")
        self.assertRaises(ValidationError, field.validate, "lala")
        self.assertRaises(ValidationError, field.validate, None)
        self.assertRaises(ValidationError, field.validate, object())


    def test_extraValidatorPasses(self):
        """
        L{Field.validate} will not raise an exception if the extra validator
        does not raise an exception.
        """
        def validate(i):
            if i > 10:
                return
            else:
                raise ValidationError("too small")
        field = Field.forTypes("key", [int], u"An integer key", validate)
        field.validate(11)


    def test_extraValidatorFails(self):
        """
        L{Field.validate} will raise a L{ValidationError} exception if the
        extra validator raises one.
        """
        def validate(i):
            if i > 10:
                return
            else:
                raise ValidationError("too small")
        field = Field.forTypes("key", [int], u"An int", validate)
        self.assertRaises(ValidationError, field.validate, 10)


    def test_onlyValidTypes(self):
        """
        Only JSON supported types can be passed to L{Field.forTypes}.
        """
        self.assertRaises(TypeError, Field.forTypes, "key", [complex], "Oops")


    def test_listIsValidType(self):
        """
        A C{list} is a valid type for L{Field.forTypes}.
        """
        Field.forTypes("key", [list], "Oops")


    def test_dictIsValidType(self):
        """
        A C{dict} is a valid type for L{Field.forTypes}.
        """
        Field.forTypes("key", [dict], "Oops")



class FieldTests(TestCase):
    """
    Tests for L{Field}.
    """
    def test_description(self):
        """
        L{Field.description} stores the passed in description.
        """
        field = Field("path", identity, u"A path!")
        self.assertEqual(field.description, u"A path!")


    def test_key(self):
        """
        L{Field.key} stores the passed in field key.
        """
        field = Field("path", identity, u"A path!")
        self.assertEqual(field.key, u"path")


    def test_serialize(self):
        """
        L{Field.serialize} calls the given serializer function.
        """
        result = []
        Field("key", result.append, u"field").serialize(123)
        self.assertEqual(result, [123])


    def test_serializeResult(self):
        """
        L{Field.serialize} returns the result of the given serializer function.
        """
        result = Field("key", lambda obj: 456, u"field").serialize(None)
        self.assertEqual(result, 456)


    def test_serializeCallsValidate(self):
        """
        L{Field.validate} calls the serializer, in case that raises an
        exception for the given input.
        """
        class MyException(Exception):
            pass
        def serialize(obj):
            raise MyException()

        field = Field("key", serialize, u"")
        self.assertRaises(MyException, field.validate, 123)


    def test_noExtraValidator(self):
        """
        L{Field.validate} doesn't break if there is no extra validator.
        """
        field = Field("key", identity, u"")
        field.validate(123)


    def test_extraValidatorPasses(self):
        """
        L{Field.validate} will not raise an exception if the extra validator
        does not raise an exception.
        """
        def validate(i):
            if i > 10:
                return
            else:
                raise ValidationError("too small")
        field = Field("path", identity, u"A path!", validate)
        field.validate(11)


    def test_extraValidatorFails(self):
        """
        L{Field.validate} will raise a L{ValidationError} exception if the
        extra validator raises one.
        """
        def validate(i):
            if i > 10:
                return
            else:
                raise ValidationError("too small")
        field = Field("path", identity, u"A path!", validate)
        self.assertRaises(ValidationError, field.validate, 10)



class FieldForValueTests(TestCase):
    """
    Tests for L{Field.forValue}.
    """
    def test_forValue(self):
        """
        L{Field.forValue} creates a L{Field} with the given key and description.
        """
        field = Field.forValue("key", None, "description")
        self.assertEqual(field.key, "key")
        self.assertEqual(field.description, "description")


    def test_forValueGoodValue(self):
        """
        The L{Field.forValue}-created L{Field} validates the value it was
        constructed with.
        """
        field = Field.forValue("key", 1234, "description")
        field.validate(1234)


    def test_valueFieldWrongValue(self):
        """
        The L{Field.forValue}-created L{Field} raises a L{ValidationError} for
        different values.
        """
        field = Field.forValue("key", 1234, "description")
        self.assertRaises(ValidationError, field.validate, 5678)


    def test_serialize(self):
        """
        The L{Field.forValue}-created L{Field} returns the given object when
        serializing, regardless of input.

        If the caller is buggy, no need to log garbage if we know what needs
        logging. These bugs will be caught by unit tests, anyway, if author of
        code is doing things correctly.
        """
        field = Field.forValue("key", 1234, "description")
        self.assertEqual(field.serialize(None), 1234)



class MessageSerializerTests(TestCase):
    """
    Tests for L{_MessageSerializer}.
    """
    def test_noMultipleFields(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} exception if
        constructed with more than object per field name.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("akey", identity, ""), Field("akey", identity, ""),
                           Field("message_type", identity, "")])


    def test_noBothTypeFields(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} exception if
        constructed with both a C{"message_type"} and C{"action_type"} field.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("message_type", identity, ""),
                           Field("action_type", identity, "")])


    def test_missingTypeField(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} if there is
        neither a C{"message_type"} nor a C{"action_type"} field.
        """
        self.assertRaises(ValueError, _MessageSerializer, [])


    def test_noTaskLevel(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} if there is
        a C{"task_level"} field included.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("message_type", identity, ""),
                           Field("task_level", identity, "")])


    def test_noTaskUuid(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} if there is
        a C{"task_uuid"} field included.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("message_type", identity, ""),
                           Field("task_uuid", identity, "")])


    def test_noTimestamp(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} if there is
        a C{"timestamp"} field included.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("message_type", identity, ""),
                           Field("timestamp", identity, "")])


    def test_noUnderscoreStart(self):
        """
        L{_MessageSerializer.__init__} will raise a L{ValueError} if there is
        a field included whose name starts with C{"_"}.
        """
        self.assertRaises(ValueError, _MessageSerializer,
                          [Field("message_type", identity, ""),
                           Field("_key", identity, "")])


    def test_serialize(self):
        """
        L{_MessageSerializer.serialize} will serialize all values in the given
        dictionary using the respective L{Field}.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", u"The type"),
             Field("length", len, "The length of a thing"),
             ])
        message = {"message_type": "mymessage",
                   "length": "thething"}
        serializer.serialize(message)
        self.assertEqual(message, {"message_type": "mymessage",
                                   "length": 8})


    def test_missingSerializer(self):
        """
        If a value in the dictionary passed to L{_MessageSerializer.serialize}
        has no respective field, it is unchanged.

        Logging attempts to capture everything, with minimal work; with any
        luck this value is JSON-encodable. Unit tests should catch such bugs, in any case.
        """
        serializer = _MessageSerializer(
            [Field.forValue("message_type", "mymessage", u"The type"),
             Field("length", len, "The length of a thing"),
             ])
        message = {"message_type": "mymessage",
                   "length": "thething",
                   "extra": 123}
        serializer.serialize(message)
        self.assertEqual(message, {"message_type": "mymessage",
                                   "length": 8,
                                   "extra": 123})



class MessageTypeTests(TestCase):
    """
    Tests for L{MessageType}.
    """
    def messageType(self):
        """
        Return a L{MessageType} suitable for unit tests.
        """
        return MessageType("myapp:mysystem",
                           [Field.forTypes("key", [int], u""),
                            Field.forTypes("value", [int], u"")],
                           u"A message type")


    def test_validateMissingType(self):
        """
        L{MessageType._serializer.validate} raises a L{ValidationError} exception if the
        given dictionary has no C{"message_type"} field.
        """
        messageType = self.messageType()
        self.assertRaises(ValidationError, messageType._serializer.validate,
                          {"key": 1, "value": 2})


    def test_validateWrongType(self):
        """
        L{MessageType._serializer.validate} raises a L{ValidationError}
        exception if the given dictionary has the wrong value for the
        C{"message_type"} field.
        """
        messageType = self.messageType()
        self.assertRaises(ValidationError, messageType._serializer.validate,
                          {"key": 1, "value": 2, "message_type": "wrong"})


    def test_validateExtraField(self):
        """
        L{MessageType._serializer.validate} raises a L{ValidationError}
        exception if the given dictionary has an extra unknown field.
        """
        messageType = self.messageType()
        self.assertRaises(ValidationError, messageType._serializer.validate,
                          {"key": 1, "value": 2,
                           "message_type": "myapp:mysystem",
                           "extra": "hello"})


    def test_validateMissingField(self):
        """
        L{MessageType._serializer.validate} raises a L{ValidationError}
        exception if the given dictionary has a missing field.
        """
        messageType = self.messageType()
        self.assertRaises(ValidationError, messageType._serializer.validate,
                          {"key": 1, "message_type": "myapp:mysystem"})


    def test_validateFieldValidation(self):
        """
        L{MessageType._serializer.validate} raises a L{ValidationError}
        exception if the one of the field values fails field-specific
        validation.
        """
        messageType = self.messageType()
        self.assertRaises(ValidationError, messageType._serializer.validate,
                          {"key": 1, "value": None,
                           "message_type": "myapp:mysystem"})


    def test_validateStandardFields(self):
        """
        L{MessageType._serializer.validate} does not raise an exception if the
        dictionary has the standard fields that are added to all messages.
        """
        messageType = self.messageType()
        messageType._serializer.validate(
            {"key": 1, "value": 2, "message_type": "myapp:mysystem",
             "task_level": "/", "task_uuid": "123", "timestamp": "xxx"})


    def test_call(self):
        """
        L{MessageType.__call__} creates a new L{Message} with correct
        C{message_type} field value added.
        """
        messageType = self.messageType()
        message = messageType()
        self.assertEqual(message._contents,
                         {"message_type": messageType.message_type})


    def test_callSerializer(self):
        """
        L{MessageType.__call__} creates a new L{Message} with the
        L{MessageType._serializer} as its serializer.
        """
        messageType = self.messageType()
        message = messageType()
        self.assertIs(message._serializer, messageType._serializer)


    def test_callWithFields(self):
        """
        L{MessageType.__call__} creates a new L{Message} with the additional
        given fields.
        """
        messageType = self.messageType()
        message = messageType(key=2, value=3)
        self.assertEqual(message._contents,
                         {"message_type": messageType.message_type,
                          "key": 2,
                          "value": 3})


    def test_description(self):
        """
        L{MessageType.description} stores the passed in description.
        """
        messageType = self.messageType()
        self.assertEqual(messageType.description, u"A message type")



class ActionTypeTestsMixin(object):
    """
    Mixin for tests for the three L{ActionType} message variants.
    """
    def getValidMessage(self):
        """
        Return a dictionary of a message that is of the action status being
        tested.
        """
        raise NotImplementedError("Override in subclasses")


    def getSerializer(self, actionType):
        """
        Given a L{ActionType}, return the L{_MessageSerializer} for this
        variant.
        """
        raise NotImplementedError("Override in subclasses")


    def actionType(self):
        """
        Return a L{ActionType} suitable for unit tests.
        """
        return ActionType("myapp:mysystem:myaction",
                          [Field.forTypes("key", [int], "")], # start fields
                          [Field.forTypes("value", [int], "")], # success fields
                          "A action type")


    def test_validateMissingType(self):
        """
        L{ActionType.validate} raises a L{ValidationError} exception if the
        given dictionary has no C{"action_type"} field.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        del message["action_type"]
        self.assertRaises(ValidationError,
                          self.getSerializer(actionType).validate, message)


    def test_validateWrongType(self):
        """
        L{ActionType.validate} raises a L{ValidationError} exception if the
        given dictionary has the wrong value for the C{"action_type"} field.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        message["action_type"] = "xxx"
        self.assertRaises(ValidationError,
                          self.getSerializer(actionType).validate, message)


    def test_validateExtraField(self):
        """
        L{ActionType.validate} raises a L{ValidationError} exception if the
        given dictionary has an extra unknown field.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        message["extra"] = "ono"
        self.assertRaises(ValidationError,
                          self.getSerializer(actionType).validate, message)


    def test_validateMissingField(self):
        """
        L{ActionType.validate} raises a L{ValidationError} exception if the
        given dictionary has a missing field.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        for key in message:
            if key != "action_type":
                del message[key]
                break
        self.assertRaises(ValidationError,
                          self.getSerializer(actionType).validate, message)


    def test_validateFieldValidation(self):
        """
        L{ActionType.validate} raises a L{ValidationError} exception if the
        one of the field values fails field-specific validation.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        for key in message:
            if key != "action_type":
                message[key] = object()
                break
        self.assertRaises(ValidationError,
                          self.getSerializer(actionType).validate, message)


    def test_validateStandardFields(self):
        """
        L{ActionType.validate} does not raise an exception if the dictionary
        has the standard fields that are added to all messages.
        """
        actionType = self.actionType()
        message = self.getValidMessage()
        message.update(
             {"task_level": "/", "task_uuid": "123", "timestamp": "xxx"})
        self.getSerializer(actionType).validate(message)



class ActionTypeStartMessage(TestCase, ActionTypeTestsMixin):
    """
    Tests for L{ActionType} validation of action start messages.
    """
    def getValidMessage(self):
        """
        Return a dictionary of a valid action start message.
        """
        return {"action_type": "myapp:mysystem:myaction",
                "action_status": "started",
                "key": 1}


    def getSerializer(self, actionType):
        return actionType._serializers.start



class ActionTypeSuccessMessage(TestCase, ActionTypeTestsMixin):
    """
    Tests for L{ActionType} validation of action success messages.
    """
    def getValidMessage(self):
        """
        Return a dictionary of a valid action success message.
        """
        return {"action_type": "myapp:mysystem:myaction",
                "action_status": "succeeded",
                "value": 2}


    def getSerializer(self, actionType):
        return actionType._serializers.success



class ActionTypeFailureMessage(TestCase, ActionTypeTestsMixin):
    """
    Tests for L{ActionType} validation of action failure messages.
    """
    def getValidMessage(self):
        """
        Return a dictionary of a valid action failure message.
        """
        return {"action_type": "myapp:mysystem:myaction",
                "action_status": "failed",
                "exception": "exceptions.RuntimeError",
                "reason": "because",
                }


    def getSerializer(self, actionType):
        return actionType._serializers.failure



class ChildActionTypeStartMessage(TestCase):
    """
    Tests for validation of child actions created with L{ActionType}.
    """
    def test_childActionUsesChildValidator(self):
        """
        Validation of child actions uses the child's validator.
        """
        A = ActionType(
            "myapp:foo", [Field.forTypes("a", [int], "")], [], "")
        B = ActionType(
            "myapp:bar", [Field.forTypes("b", [int], "")], [], "")

        logger = MemoryLogger()

        with A(logger, a=1):
            with B(logger, b=2):
                pass
        # If wrong serializers/validators were used, this will fail:
        logger.validate()



class ActionTypeTests(TestCase):
    """
    General tests for L{ActionType}.
    """
    def actionType(self):
        """
        Return a L{ActionType} suitable for unit tests.
        """
        return ActionType("myapp:mysystem:myaction", [], [],
                          "An action type")


    def test_call(self):
        """
        L{ActionType.__call__} returns the result of calling
        C{self._startAction}.
        """
        actionType = self.actionType()
        actionType._startAction = lambda *args, **kwargs: 1234
        result = actionType(object())
        self.assertEqual(result, 1234)


    def test_callArguments(self):
        """
        L{ActionType.__call__} calls C{self._startAction} with the logger,
        action type, serializers and passed in fields.
        """
        called = []
        actionType = self.actionType()
        actionType._startAction = lambda *args, **kwargs: called.append(
            (args, kwargs))
        logger = object()
        actionType(logger, key=5)
        self.assertEqual(called, [((logger, "myapp:mysystem:myaction",
                                    actionType._serializers),
                                   {"key": 5})])


    def test_defaultStartAction(self):
        """
        L{ActionType._startAction} is L{eliot.startAction} by default.
        """
        self.assertEqual(ActionType._startAction, startAction)


    def test_asTask(self):
        """
        L{ActionType.asTask} returns the result of calling C{self._startTask}.
        """
        actionType = self.actionType()
        actionType._startTask = lambda *args, **kwargs: 1234
        result = actionType.asTask(object())
        self.assertEqual(result, 1234)


    def test_asTaskArguments(self):
        """
        L{ActionType.asTask} calls C{self._startTask} with the logger,
        action type and passed in fields.
        """
        called = []
        actionType = self.actionType()
        actionType._startTask = lambda *args, **kwargs: called.append(
            (args, kwargs))
        logger = object()
        actionType.asTask(logger, key=5)
        self.assertEqual(called, [((logger, "myapp:mysystem:myaction",
                                    actionType._serializers),
                                   {"key": 5})])


    def test_defaultStartTask(self):
        """
        L{ActionType._startTask} is L{eliot.startTask} by default.
        """
        self.assertEqual(ActionType._startTask, startTask)


    def test_description(self):
        """
        L{ActionType.description} stores the passed in description.
        """
        actionType = self.actionType()
        self.assertEqual(actionType.description, "An action type")



class EndToEndValidationTests(TestCase):
    """
    Test validation of messages created using L{MessageType} and
    L{ActionType}.
    """
    MESSAGE = MessageType("myapp:mymessage",
                          [Field.forTypes("key", [int], "The key")],
                          "A message for testing.")
    ACTION = ActionType("myapp:myaction",
                        [Field.forTypes("key", [int], "The key")],
                        [Field.forTypes("result", [unicode], "The result")],
                        "An action for testing.")


    def test_correctFromMessageType(self):
        """
        A correct message created using L{MessageType} will be logged to a
        L{MemoryLogger}.
        """
        logger = MemoryLogger()
        msg = self.MESSAGE().bind(key=123)
        msg.write(logger)
        self.assertEqual(logger.messages[0]["key"], 123)


    def test_incorrectFromMessageType(self):
        """
        An incorrect message created using L{MessageType} will raise a
        L{ValidationError} in L{MemoryLogger.validate}.
        """
        logger = MemoryLogger()
        msg = self.MESSAGE().bind(key="123")
        msg.write(logger)
        self.assertRaises(ValidationError, logger.validate)


    def test_correctStartFromActionType(self):
        """
        A correct start message created using a L{ActionType} will be logged
        to a L{MemoryLogger}.
        """
        logger = MemoryLogger()
        with self.ACTION(logger, key=123) as action:
            action.addSuccessFields(result="foo")
        self.assertEqual(logger.messages[0]["key"], 123)


    def test_incorrectStartFromActionType(self):
        """
        An incorrect start message created using a L{ActionType} will raise a
        L{ValidationError}.
        """
        logger = MemoryLogger()
        with self.ACTION(logger, key="123") as action:
            action.addSuccessFields(result="foo")
        self.assertRaises(ValidationError, logger.validate)


    def test_correctSuccessFromActionType(self):
        """
        A correct success message created using a L{ActionType} will be logged
        to a L{MemoryLogger}.
        """
        logger = MemoryLogger()
        with self.ACTION(logger, key=123) as action:
            action.addSuccessFields(result="foo")
        self.assertEqual(logger.messages[1]["result"], "foo")


    def test_incorrectSuccessFromActionType(self):
        """
        An incorrect success message created using a L{ActionType} will raise a
        L{ValidationError}.
        """
        logger = MemoryLogger()
        with self.ACTION(logger, key=123) as action:
            action.addSuccessFields(result=-1)
        self.assertRaises(ValidationError, logger.validate)


    def test_correctFailureFromActionType(self):
        """
        A correct failure message created using a L{ActionType} will be logged
        to a L{MemoryLogger}.
        """
        logger = MemoryLogger()
        def run():
            with self.ACTION(logger, key=123):
                raise RuntimeError("hello")
        self.assertRaises(RuntimeError, run)
        self.assertEqual(logger.messages[1]["reason"], "hello")
