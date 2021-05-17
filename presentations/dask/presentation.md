
layout: true

{{content}}

.footer[pythonspeed.com | @itamarst]

---

class: middle

# Logging for Scientific Computing

## Itamar Turner-Trauring
## https://pythonspeed.com

---

# Three lessons about scientific computing

## **Logic:** Complex calculations

## **Structure:** Long-running batch processes

## **Tools:** Dask is really useful

???

I’m just a humble software engineer
but recently spent 1.5 years doing scientific computing
learned what makes it different than other forms of software

complex math
read in inputs, eventually get output: batch job
reason we're here today: Dask

---

# Three problems in scientific computing

## **Logic:** Why is your calculation wrong?

## **Structure:** Why is your code slow?

## **Tools:** How do we use this with Dask?

???

each characteristic has corresponding problems

these three problems, and how logging can help address them, are what I’ll be talking about for the rest of the talk

---

class: middle

# Problem #1:
# Why is your calculation wrong?

---

# Scientific computing’s slow feedback loop

## Your batch process is finally done...

--
## (it only took 12 hours)

--

## ...and the result is obviously wrong 🤦‍ 

---

# How do you solve this?

* Often only happens with real data.
* Using a debugger with a 12-hour process won't work.
* You need a record of what the batch process actually did.

---

# You need logging!

* Which functions called which other functions.
* What were the functions’ inputs and outputs.
* Intermediate values as well.

---
# The Eliot logging library

* Project started in 2014.
* Structured, trace-based logging, with built-in support for scientific computing (NumPy, Dask).
* https://eliot.readthedocs.io


???

Very different than normal logging libraries

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

class: middle

# Problem #2:
# Why is your code slow?

---

# Profilers are insufficient

## Profilers can’t tell you which inputs are slow:
* `f()` may be fast on some inputs, but slow on others.
* Profiler just tells you "`f()` is slowish on average."

---

# Eliot to the rescue

* Records start, finish and elapsed time of actions.
* But, also logs inputs and results of computations.
* **You can find slow actions and their inputs!**

---

# Example: when is complex_calc() slow?

```python
from eliot import start_action

def main(inputs):
    with start_action(action_type="main"):
        A = []
        for i in inputs:
            A.append(complex_calc(i))
        return np.median(A, axis=0)
```

???

you can see here I'm using a different Eliot API, just for variety.

---

# Example: when is complex_calc() slow?

```
$ python slow.py
$ eliot-tree out.log | grep complex_calc
    ├── complex_calc ⇒ (arg: 13) ⧖ 0.1s
...
    ├── complex_calc ⇒ (arg: -12) ⧖ 10.0s
...
    ├── complex_calc ⇒ (arg: 4) ⧖ 0.2s
```

### It's slow when the input argument is -12!

---

class: middle

# Problem #3
# Logging inside Dask

---

# How do you match log messages to Dask tasks?

* Dask runs your code as a _graph_ of tasks.
* Would like to trace causality from Dask in logs: task A called task B.
* Eliot's tree-of-actions structure is a pretty good fit.

---

# Eliot's Dask support: Logic 1

```python
from eliot import log_call
from eliot.dask import compute_with_trace

@log_call
def multiply(x, y=7):
    return x * y

@log_call
def add(x, y):
    return x + y
```

---

# Eliot's Dask support: Logic 2

```python
@log_call
def main_computation():
    bag = from_sequence([1, 2, 3])
    return bag.map(multiply).fold(add)
```

---

# Eliot's Dask support: Setup

```python
from os import getpid
from eliot import to_file

def _start_logging():
    to_file(open(f"{getpid()}.log", "a"))

_start_logging()  # <-- main process

client = Client(n_workers=3)
client.run(_start_logging)  # <-- workers
```

---

# Eliot's Dask support: Compute

```python
from eliot.dask import compute_with_trace

bag = main_computation()

# Instead of dask.compute():
result = compute_with_trace(bag)
print(result)
```

---

# Resulting logs (simplified)

```
$ eliot-tree *.log
└── main_computation/1 ⇒ ()
    │   │   ├── multiply/2/2/3/1 ⇒ (x: 1 y: z)
    │   │   │   └── multiply/2/2/3/2 ⇒ (result: 7)
    ...
    │   ├── add/2/5/3/1 ⇒ (x: 7, y: 14)
    │   │   │   └── add/2/5/3/2 ⇒ (result: 21)
    │   │   ├── add/2/5/4/1 ⇒ (x: 21, y: 21)
    │   │   │   └── add/2/5/4/2 ⇒ (result: 42)
    └── main_computation/3 ⇒ (result: 42)
```

???

this is simplified output to fit on slide

---

# Caveats and missing features

* Dask is a graph, Eliot is a tree.
    * **Solution:** All parent tasks are automatically recorded in logs. Omitted from previous slide just so it fits on screen.
* No built-in way to centralize logs from multiple machines.
    * **Solution:** `scp`, or upload to S3, or tools like `logstash`.

---

# Additional Eliot features

* `eliot.dask.persist_with_trace()`.
* More sophisticated logging APIs than those shown here.
* Pluggable serialization to support logging custom object types.
* Use outside Dask, e.g. `asyncio`/Twisted/`trio` support.
* Support for unit testing log messages.

---

# Further information

## https://eliot.readthedocs.io
## https://pythonspeed.com
## Email: itamar@pythonspeed.com
## Twitter: @itamarst

???

Python performance 
Bridging the gap between scientific computing and software engineering
