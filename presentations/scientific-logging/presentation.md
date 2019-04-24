layout: true

{{content}}

.footer[pythonspeed.com | @itamarst]

---

class: middle

# Logging for Scientific Computing

## Itamar Turner-Trauring
## Consulting services: https://pythonspeed.com

---

# The nature of scientific computing

* **Logic:** Complex calculations
* **Structure:** Long-running batch processes
* **Goal:** a claim about reality

???

I'm a software engineer
but recently spent 1.5 years doing scientific computing
learned what makes it different than other forms of software

---

# Problem #1: Calculations gone wrong

## Your batch process is finally done...

--
## (it only took 12 hours)

--

## ...and the result is obviously wrong 🤦‍ 

---

# How do you solve this?

## Often only happens with real data

## Can't use debugger with a 12 hour process

## You need—logging!

---

# Log intermediate steps of calculations

* Parameters
* Inputs
* Outputs

---

# Introducing Eliot

* Structured, causal logging
* Built-in support for scientific computing (NumPy, Dask)
* https://eliot.readthedocs.io

---

# Example: original code

```python
def add(a, b):
    # ... implementation ...
    
def multiply(a, b):
    # ... implementation ...

def multiplysum(a, b, c):
    return -multiply(add(a, b), c)

print(multiplysum(1, 2, 4)) # -(1 + 2)*4⇒-12
```

---

# Example: we run it

```shell-session
$ python mathishard.py
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

You also need to tell Eliot where to send logs, but omitted for brevity.

---

# Example: look at logs

```
$ python mathishard.py
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

# Problem #2: Your code is slow

* The calculation takes 12 hours—why?

---

# Profilers are insufficient

* Only support single process, not distributed systems
* Can't tell you which inputs are slow:
    * `f()` may be fast on some inputs, but very slow on others
    * Profiler just tells you "`f()` is slowish"

---

# Eliot to the rescue

* Supports multiple processes
* Supports Dask
* Tells you elapsed time _and_ inputs to function

---

# Example: when is double() slow?

```python
@log_call
def main():
    A = double(13)
    B = double(0)
    C = double(4)
    return A * B * C
```

---

# Example: when is double() slow?

```
$ python slow.py
$ eliot-tree out.log | grep -A1 double.*started
    ├── __main__.double/2/1 ⇒ started ⧖ 0.0s
    │   ├── a: 13
--
    ├── __main__.double/3/1 ⇒ started ⧖ 10.0s
    │   ├── a: 0
--
    ├── __main__.double/4/1 ⇒ started ⧖ 0.0s
    │   ├── a: 4
```
