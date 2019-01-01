Scientific Computing with Eliot
===============================

When it takes hours or days to run your computation, it can take a long time before you notice something has gone wrong, so your feedback cycle for fixes can be very slow.
If you want to solve problems quickly—whether it's inconsistent results, crashes, or slowness—you need to understand what was going on in your process as it was running: you need logging.

Eliot is an ideal logging library for these cases:

* It provides structured logging, instead of prose, so you can see inputs, outputs, and intermediate results of your calculations.
* It gives you a trace of what happened, including causality: instead of just knowing that ``f()`` was called, you can distinguish between calls to ``f()`` from ``path1()`` and ``path2()``.
* It supports scientific libraries: NumPy and Dask.
  By default, Eliot will automatically serialize NumPy integers, floats, arrays, and bools to JSON (see :ref:`custom_json` for details).


Using Dask
----------

If you're using the Dask distributed computing framework, you can automatically use Eliot to trace computations across multiple processes or even machines.
To do this you will need to:

* Ensure all worker processes write logs to disk (if you're using the ``multiprocessing`` or ``distributed`` backends).
* Aggregate all log files into a single place, so you can more easily analyze them with e.g. `eliot-tree <https://github.com/jonathanj/eliottree>`_, if you're using multiple worker machines.
* Replace ``dask.compute()`` with ``eliot.dask.compute_with_trace()``.

The only caveat is that retries within Dask will result in confusing log messages; this will eventually be fixed.

In the following example, you can see how this works for a Dask run using the ``distributed`` backend, the recommended Dask backend.
We'll be using multiple worker processes, but only use a single machine:
