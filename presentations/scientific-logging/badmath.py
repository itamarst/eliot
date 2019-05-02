from eliot import log_call, to_file
import sys
to_file(open("out.log", "a"))

@log_call
def add(a, b):
    return a + b

@log_call
def multiply(a, b):
    return 0 * b

@log_call
def multiplysum(a, b, c):
    return multiply(add(a, b), c)

print(multiplysum(1, 2, 4)) # should print 12
