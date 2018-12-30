### Part 1: Motivation [7 minutes]

* Problem #1: Reproducibility
    * Different outputs for different inputs—but why?
    * Need to understand what happened inside the computation, where things diverged
* Problem #2: General bugs
    * A function raises an exception: why?
    * The process runs out of memory and crashes: why?
* Problem #3: Slowness
    * Which functions are causing the problem?
    * May need to run with real data to get real problem
    * Profiling may add too much cost, or vastly too much output
* The root problem
    * Batch processes that take hours or days to run, causing—
    * Slow feedback cycles
* The ideal solution
    * The ability to look back at the course of computation
    * See a trace of what happened, and why

### Part 2: Quick intro to Eliot [7 minutes]

* Eliot: a causal logging library
    * Standard logging is a series of disjoined facts
    * Eliot logging is a story of what happened—actions that can succeed or fail, and that can spawn other actions
    * NumPy and Dask support
* Example: Adding Eliot to a simple computation

### Part 3: Eliot in practice [14 minutes]

* Example #1: What went wrong in computation?
    * A real bug where intermediate results demonstrate the problem
    * Explain the problem (kept getting same result regardless of inputs)
    * Show the logs
    * Explain implication of logs
    * Show the actual bug in the code (forgot to indent last line of loop)
* Example #2: Why is my computation slow?
    * We'll see which part of code is causing slowness...
    * ...and which particular inputs trigger the problem!
    * Show tree of actions with timing info
    * Slow function leaps out
    * Use full view for that sub-tree to see inputs
* Where to learn more
    * https://eliot.readthedocs.io
