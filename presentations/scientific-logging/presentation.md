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
* **Goal:** A claim about reality

???

I'm a software engineer
but recently spent 1.5 years doing scientific computing
learned what makes it different than other forms of software

---

# Three problems in scientific computing

* **Logic:** Why is your calculation wrong?
* **Structure:** Why is your code slow?
* **Goal:** Can you trust the result?

---

class: middle

# Problem #1:
# Why is your calculation wrong?

---

# Scientific computing's slow feedback loop

## Your batch process is finally done...

--
## (it only took 12 hours)

--

## ...and the result is obviously wrong 🤦‍ 

---

# How do you solve this?

## Often only happens with real data

## Can't use debugger with a 12 hour process

## You need logging!

---

# Introducing Eliot

* Structured, causal logging
* Built-in support for scientific computing (NumPy, Dask)
* https://eliot.readthedocs.io

---

# Logging can help you debug your code

* Which functions called which other functions
* What were the functions' inputs and outputs

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

class: middle

# Problem #2:
# Why is your code slow?

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

---

class: center

# Problem #3
# Can you trust your code?

---

# Scientific code is an argument about reality

* This cell culture has these genes
* This behavior is correlated with this outcome
* This causes that

---

# Reproducability is necessary but insufficient

* If I run your code and get different results I won't trust it
* But even with consistent results—
* —opaque black-box results are hard to trust

---

# Trust comes from a coherent explanation

1. We did A—
2. —here is a graph of intermediate results.
3. And then did B—
4. —here is a table showing why it makes sense.
5. Therefore, we can conclude C.

---

# Jupyter as tool for explanation

* Pros: Wonderful at interleaving execution and visual and prose explinations.
* Cons: Not great from software engineering perspective (tests, modularity, etc.).

---

# Eliot as tool for explanation

* Shows calculation's intermediate results.
* Pros: Integrates with standard software execution structure.
* Cons: No visualization capability, no ability to add prose.

---

# A vision for the future: Eliot + Jupyter?

* What if you could take Eliot's output and load it into something like Jupyter?
* The best of of both worlds: software engineering best practices, with Jupyter's ability to easily visualize and explain.
* If you're interested I'd love to talk to you.

---

# Logging will help you:

* Debug your code.
* Speed up your code
* Understand and trust the results.

# Go add it to your project!

---

# Further information

* Eliot documentation: https://eliot.readthedocs.io
* Contact: itamar@pythonspeed.com / @itamarst
* Consulting services: https://pythonspeed.com
