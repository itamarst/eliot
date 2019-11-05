
class: middle

# Eliot: Logging that tells you _why_ it happened

## https://eliot.readthedocs.io

---

# Why do we want logs?

To know:

1. What happened.
2. Why it happened.

Traditional logging only tells us what happened.

Let's see why Eliot is better!

---

# Example: original code

```python
def add(a, b):
    # ... implementation ...

def multiply(a, b):
    # ... implementation ...

def multiplysum(a, b, c):
    return multiply(add(a, b), c)

print(multiplysum(1, 2, 4)) # (1 + 2)*4⇒12
```

---

# Example: we run it

```shell-session
$ python badmath.py
0
```

## Something is wrong!

---

# Example: add logging

```python
from eliot import log_call

@log_call
def add(a, b):
    # ... implementation ...

@log_call
def multiply(a, b):
    # ... implementation ...

# etc.
```

???

Just add decorator to each function.

There are more sophisticated APIs for usage inside functions.

---

# Example: also need to configure log output

```python
from eliot import to_file
to_file(open("out.log", "w"))
```

---

# Example: look at logs

```
$ python badmath.py
0
$ eliot-tree out.log
─── multiplysum (inputs a=1 b=2 c=4)
    ├── add (inputs a=1 b=2)
    │   └── result: 3
    ├── multiply (inputs a=3 b=4)
    │   └── result: 0
    └── result: 0
```

(Note: `eliot-tree` output was simplified to fit on slide)

---

# Features

* Structured logging, JSON by default
* NumPy and Dask support
* asyncio, Twisted, and Trio support
* Easy, gradual migration from stdlib `logging`
* Unit test your logging (if you want to)
* And more!

---

# Learn more

* https://eliot.readthedocs.io
* itamar@pythonspeed.com

 
