"""
Tests for L{eliot._parse}.
"""

'''
Basic idea for testing parsing:

Create a tree of Eliot actions and messages (using Hypothesis stateful
testing? Normal hypothesis tests?). Feed resulting messages into parser in
random order. At the end we should get expected result.

The key thought here is that if any random order is correct then the
intermediate states must be correct too.

Additional coverage is likely needed that is specific to missing actions.
'''
