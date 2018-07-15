Integrating and Migrating Existing Logging
==========================================

If you have an existing code base, you likely have existing log messages.
This document will explain how to migrate and integrate existing logging into your new Eliot log setup.
In particular, this will focus on the Python standard library ``logging`` package, but the same principles apply to other logging libraries.


Step 1: Route existing logs to Eliot
------------------------------------

Eliot includes a ``logging.Handler`` that can take standard library log messages and route them into Eliot.
These log messages will *automatically* appear in the correct place in the action tree!
Once you add actions to your code these log messages will automatically benefit from Eliot's causal information.

To begin with, however, we'll just add routing of log messages to Eliot:

.. code-block:: python

   # Add Eliot Handler to root Logger. You may wish to only route specific
   # Loggers to Eliot.
   import logging
   from eliot.stdlib import EliotHandler
   logging.getLogger().addHandler(EliotHandler())


Step 2: Add actions at entry points and other key points
--------------------------------------------------------

Simply by adding a few key actions—the entry points to the code, as well as key sub-actions—you can start getting value from Eliot's functionality while still getting information from your existing logs.
You can leave existing log messages in place, replacing them with Eliot logging opportunistically; they will still be included in your output.

.. literalinclude:: ../../../examples/stdlib.py

The stdlib logging messages will be included in the correct part of the tree:

.. code-block:: shell-session

   $ python examples/stdlib.py  | eliot-tree 
   3f465ee3-7fa9-40e2-8b20-9c0595612a8b
   └── mypackage:main/1 ⇒ started
       ├── timestamp: 2018-07-15 16:50:39.230467
       ├── mypackage:do_a_thing/2/1 ⇒ started
       │   ├── timestamp: 2018-07-15 16:50:39.230709
       │   └── mypackage:do_a_thing/2/2 ⇒ succeeded
       │       └── timestamp: 2018-07-15 16:50:39.230836
       ├── mypackage:do_a_thing/3/1 ⇒ started
       │   ├── timestamp: 2018-07-15 16:50:39.230980
       │   ├── eliot:stdlib/3/2
       │   │   ├── log_level: ERROR
       │   │   ├── logger: mypackage
       │   │   ├── message: The number 3 is a bad number, don't use it.
       │   │   └── timestamp: 2018-07-15 16:50:39.231157
       │   └── mypackage:do_a_thing/3/3 ⇒ failed
       │       ├── exception: builtins.ValueError
       │       ├── reason: I hate the number 3
       │       └── timestamp: 2018-07-15 16:50:39.231364
       ├── eliot:stdlib/4
       │   ├── log_level: INFO
       │   ├── logger: mypackage
       │   ├── message: Number 3 was rejected.
       │   └── timestamp: 2018-07-15 16:50:39.231515
       └── mypackage:main/5 ⇒ succeeded
           └── timestamp: 2018-07-15 16:50:39.231641
