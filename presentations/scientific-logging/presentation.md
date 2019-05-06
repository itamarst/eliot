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

## **Logic:** Complex calculations

## **Structure:** Long-running batch processes

## **Goal:** A inference about reality

???

I’m just a humble software engineer
but recently spent 1.5 years doing scientific computing
learned what makes it different than other forms of software

complex math
read in inputs, eventually get output: batch job
an inference about reality: it’s going to rain on tuesday, or, this cell culture has these particular genes.

---

# Three problems in scientific computing

## **Logic:** Why is your calculation wrong?

## **Structure:** Why is your code slow?

## **Goal:** Can you trust the result?

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

## Often only happens with real data

## Can’t use debugger with a 12 hour process

## You need a record of what the batch process actually did

---

# You need logging!

## Which functions called which other functions

## What were the functions’ inputs and outputs

## Intermediate values as well

---
# The Eliot logging library

## Project started in 2014

## Structured, trace-based logging, with built-in support for scientific computing (NumPy, Dask)

## https://eliot.readthedocs.io

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

* Only support single process, not distributed systems
* Can’t tell you which inputs are slow:
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
    ├── double ⇒ started ⧖ 0.0s
    │   ├── a: 13
--
    ├── double ⇒ started ⧖ 10.0s
    │   ├── a: 0
--
    ├── double ⇒ started ⧖ 0.0s
    │   ├── a: 4
```

---

class: middle

# Problem #3
# Can you trust your code?

---

# Scientific code is an argument about reality

* This cell culture has these genes
* This behavior is correlated with this outcome
* This causes that

---

# Reproducability is necessary but insufficient

* If I run your code and get different results I won’t trust it
* But even with consistent results—
* —opaque black-box results are hard to trust

---

# Trust also requires a coherent explanation

1. We did A—
2. —here is a graph of intermediate results.
3. And then did B—
4. —here is a table showing why it makes sense.
5. Therefore, we can conclude C.

---

# Explanations with Jupyter

## **Pros:** Wonderful at interleaving execution and visual and textual explanations.

## **Cons:** Not great from software engineering perspective (tests, modularity, etc.).

---

# Explanations with Eliot

##  Logs show causal trace of calculation, with intermediate results.

## **Pros:** Integrates with standard software execution structure.

## **Cons:** No visualization capability, no ability to add text.

???

logs are a bit opaque, help you author as gain trust
but not something you can give someone else

---

# The future: Eliot + Jupyter?

## We could take Eliot’s output and load it into Jupyter.
## The best of both worlds: software engineering best practices, with Jupyter’s ability to easily visualize and explain.
## Interested? Talk to me!

---

# Logging will help you:

## 1. Debug your code.
## 2. Speed up your code
## 3. Understand and trust the results.

# Go add logging to your project!

---

# Further information

* Eliot documentation: https://eliot.readthedocs.io
* Consulting services: https://pythonspeed.com
* Email: itamar@pythonspeed.com
* Twitter: @itamarst

