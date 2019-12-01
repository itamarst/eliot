.. _messages:

Messages
========

Sometimes you don't want to generate actions; sometimes you just want an individual isolated message, the way traditional logging systems work.
Here's how to do it.

When you have an action
-----------------------

If you already have an action object, you can log a message in that action's context:

.. code-block:: python

    from eliot import start_action

    class YourClass(object):
        def run(self):
            with start_action(action_type="myaction") as ctx:
                ctx.log(message_type="mymessage", key="abc", key2=4)

If you don't have an action
---------------------------

If you don't have a reference to an action, or you're worried the function will sometimes be called outside the context of any action at all, you can use ``log_message``:

.. code-block:: python

    from eliot import log_message

    def run(x):
        log_message(message_type="in_run", xfield=x)

The main downside to using this function is that it's a little slower, since it needs to handle the case where there is no action in context.
