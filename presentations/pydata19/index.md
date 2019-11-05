
class: middle

# Eliot: Logging that tells you _why_ it happened

## https://eliot.readthedocs.io

---

# Data processing has a slow feedback loop

## Your batch process is finally done...

--
## (it only took 4 hours)

--

## ...and the result is obviously wrong 🤦‍ 

---

# How do you solve this?

## Often only happens with real data

## Can’t use debugger with a 4 hour process

## You need a record of what the batch process actually did

---

# You need logging!

## Which functions called which other functions

## What were the functions’ inputs and outputs

## Intermediate values as well

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

# Example: add logging

```python
from eliot import log_call, to_file
to_file(open("out.log", "w"))

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

* **Logging of a structured tree of actions**
* NumPy and Dask support
* asyncio, Twisted, and Trio support
* Easy, gradual migration from stdlib `logging`
* Unit test your logging (if you want to)
* And more!

---

# Learn more

* https://eliot.readthedocs.io
* itamar@pythonspeed.com

 
