Contributing to Eliot
^^^^^^^^^^^^^^^^^^^^^

To run the full test suite, the Daemontools package should be installed.

All modules should have the ``from __future__ import unicode_literals`` statement, to ensure Unicode is used by default.

Coding standard is PEP8, with the only exception being camel case methods for the Twisted-related modules.
Some camel case methods remain for backwards compatibility reasons with the old coding standard.

You should use ``black`` to format the code.
